"""
任务执行器 v3
- 并发执行：--concurrency N，块级并发，任务间顺序
- Mock 模式使用真实 prompt（build_prompts.py 拼装结果）
- --skip-gate 在 --live 下被拒绝
- 线程安全：completed_chunks.txt 用文件锁，熔断加锁
- Pass2 使用 work/pass2_chunks.json 的分块方案
- offset 回填 → validate 校验链
"""
import json, sys, io, os, yaml, time, hashlib, subprocess, threading
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(__file__).parent.parent
WORK = BASE / 'work'
CORPUS = BASE / 'corpus'
CONFIG = BASE / 'config'
TASKS_DIR = BASE / 'tasks'
LOGS = BASE / 'logs'
SCHEMA_DIR = BASE / 'schema'

sys.path.insert(0, str(BASE / 'scripts' / 'llm'))
from client import LLMClient, EvidenceLogger, TokenBudgetExceededError
from mock_falsifiable import generate_mock
sys.path.insert(0, str(BASE / 'scripts'))
from pass2_builder import build_pass2_prompt, save_prompt_and_whitelist

# ── Load configs ──────────────────────────────────────────────────

def load_chunk_plan():
    with open(CONFIG / 'task_chunks.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def load_pass2_chunk_plan():
    """Load pass2 chunk plan from work/pass2_chunks.json."""
    path = WORK / 'pass2_chunks.json'
    if not path.exists():
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_task_card(task_id):
    path = TASKS_DIR / f'{task_id}.yaml'
    if not path.exists():
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def load_cite_index():
    idx = {}
    with open(WORK / 'cite_index.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                idx[rec['cite_id']] = rec
    return idx

# ── Input builder (same as build_prompts.py) ─────────────────────

def build_chunk_input(chunk, cite_index):
    """Build the corpus entries string for a chunk."""
    lines = []
    for cid in chunk['cite_ids']:
        rec = cite_index.get(cid)
        if rec:
            lines.append(f"[{rec['cite_id']}]\n{rec['clean']}\n")
    return '\n'.join(lines)

def build_real_prompt(task_card, chunk, cite_index):
    """Build the real system_prompt + user_prompt from task card and chunk data."""
    system_prompt = task_card.get('system_prompt', '')
    user_template = task_card.get('user_prompt_template', '')
    corpus_text = build_chunk_input(chunk, cite_index)

    user_prompt = user_template.replace('{volume_name}', chunk.get('volume', ''))
    user_prompt = user_prompt.replace('{entry_count}', str(len(chunk.get('cite_ids', []))))
    user_prompt = user_prompt.replace('{scope_description}', chunk.get('description', ''))
    user_prompt = user_prompt.replace('{corpus_entries}', corpus_text)

    return [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_prompt},
    ]

# ── Validator runner ──────────────────────────────────────────────

def run_validation(output_path, run_id):
    """Backfill offsets, then validate."""
    backfilled_path = str(output_path).replace('.jsonl', '_backfilled.jsonl')
    subprocess.run(
        [str(BASE / '.venv' / 'Scripts' / 'python.exe'),
         str(BASE / 'scripts' / 'backfill_offsets.py'),
         str(output_path), '--output', backfilled_path],
        capture_output=True, text=True, timeout=30, cwd=str(BASE),
        encoding='utf-8', errors='replace'
    )
    result = subprocess.run(
        [str(BASE / '.venv' / 'Scripts' / 'python.exe'),
         str(BASE / 'scripts' / 'validate.py'),
         str(backfilled_path)],
        capture_output=True, text=True, timeout=30, cwd=str(BASE),
        encoding='utf-8', errors='replace'
    )
    lines = result.stdout.split('\n')
    accepted = 0
    rejected = 0
    for line in lines:
        if 'Accepted:' in line:
            try:
                parts = line.strip().split()
                accepted = int(parts[1])
            except: pass
        if 'Rejected:' in line:
            try:
                parts = line.strip().split()
                rejected = int(parts[1])
            except: pass
    return {'accepted': accepted, 'rejected': rejected, 'stdout': result.stdout}

# ── Value priority ordering ─────────────────────────────────────────

VOLUME_PRIORITY = [
    'lore', 'books', 'characters', 'narrative',
    'artifacts', 'rogue', 'unattributed', 'dialogue'
]
VOLUME_PRIORITY_MAP = {v: i for i, v in enumerate(VOLUME_PRIORITY)}

def sort_chunks_by_priority(chunks):
    return sorted(chunks, key=lambda c: VOLUME_PRIORITY_MAP.get(c['volume'], 99))

# ── Pass2 guard ──────────────────────────────────────────────────

def check_ov_library():
    try:
        result = subprocess.run(['ov', 'ls', 'viking://resources/hsr/', '-l', '256', '-n', '256'],
                              capture_output=True, text=True, timeout=15,
                              encoding='utf-8', errors='replace')
        return result.returncode == 0 and result.stdout.strip() != '(empty)' and len(result.stdout.strip()) > 0
    except:
        return False

# ── Thread-safe completed_chunks ──────────────────────────────────

class CompletedTracker:
    """Thread-safe completed chunks tracker with file persistence."""

    def __init__(self, filepath):
        self.filepath = filepath
        self._lock = threading.Lock()
        self._completed = set()
        if filepath.exists():
            with open(filepath, 'r') as f:
                for line in f:
                    if line.strip():
                        self._completed.add(line.strip())

    def is_completed(self, chunk_id):
        with self._lock:
            return chunk_id in self._completed

    def mark_completed(self, chunk_id):
        with self._lock:
            if chunk_id not in self._completed:
                self._completed.add(chunk_id)
                with open(self.filepath, 'a', encoding='utf-8') as f:
                    f.write(chunk_id + '\n')

    def get_all(self):
        with self._lock:
            return set(self._completed)

    def __len__(self):
        with self._lock:
            return len(self._completed)

# ── Single chunk executor ────────────────────────────────────────

def execute_chunk(task_name, task_card, chunk, cite_index, client, run_logs,
                  val_logs, completed_tracker, is_live, stop_event, fuse_error,
                  pass1_dir=None, force=False):
    """Execute a single chunk. Returns (cid, success, summary) or raises."""
    cid = chunk['chunk_id']
    volume = chunk.get('volume', '')
    task_cid = f"{task_name}:{cid}"  # per-task tracking key
    pass_num = task_card.get('pass', 1)
    live_max_tokens = 16384  # configurable per-chunk output budget

    if not force and completed_tracker.is_completed(task_cid):
        return (cid, 'skipped', {'chunk_id': cid, 'volume': volume,
                'accepted': 0, 'rejected': 0, 'rejection_rate': 0.0})

    # Check fuse stop signal
    if stop_event.is_set():
        return (cid, 'stopped', {'chunk_id': cid, 'volume': volume,
                'accepted': 0, 'rejected': 0, 'rejection_rate': 0.0})

    expected_rejections = []
    whitelist_ids = []
    try:
        if is_live:
            messages = build_real_prompt(task_card, chunk, cite_index)
            response = client.chat(messages=messages, task_name=f"{task_name}/{cid}",
                                   input_volume=chunk.get('volume', ''),
                                   max_tokens=live_max_tokens)
            output_text = response.get('content', '')

            # ── Finish reason check ──
            finish_reason = response.get('finish_reason', 'unknown')
            completion_tokens = response.get('usage', {}).get('completion_tokens', 0)
            if finish_reason != 'stop' and finish_reason != 'unknown':
                # Truncation or other abnormal termination — mark as failed, don't mark completed
                token_ratio = completion_tokens / live_max_tokens if live_max_tokens > 0 else 0
                print(f"\n  [{cid}] ⚠ FINISH REASON: {finish_reason} "
                      f"(completion_tokens={completion_tokens}, max_tokens={live_max_tokens}, "
                      f"ratio={token_ratio:.1%})")
                print(f"  [{cid}] OUTPUT TRUNCATED — not marking as completed.")
                print(f"  [{cid}] Manual intervention required: increase max_tokens and re-run with --force")
                return (cid, 'truncated', {
                    'chunk_id': cid, 'volume': volume,
                    'accepted': 0, 'rejected': 0, 'rejection_rate': 0.0,
                    'error': f'finish_reason={finish_reason}, completion_tokens={completion_tokens}, max_tokens={live_max_tokens}'
                })
        elif pass_num == 2:
            # Pass2: build prompt from pass1 output data
            messages, whitelist_ids, full_prompt = build_pass2_prompt(
                task_name, task_card, pass1_dir, cite_index)
            # Save prompt and whitelist
            save_prompt_and_whitelist(task_name, messages, whitelist_ids, full_prompt, run_logs)
            output_text, expected_rejections = generate_mock(task_name, volume, chunk, cite_index)

            # Save expected rejections
            exp_path = run_logs / f"expected_rejections_{cid}.json"
            with open(exp_path, 'w', encoding='utf-8') as f:
                json.dump(expected_rejections, f, ensure_ascii=False, indent=2)

            # Pass real prompt + mock response through client
            client.chat(messages=messages, task_name=f"{task_name}/{cid}",
                       input_volume='_pass2', mock_response=output_text)
        else:
            # Pass1 mock: build real prompt, generate mock response
            messages = build_real_prompt(task_card, chunk, cite_index)
            output_text, expected_rejections = generate_mock(task_name, volume, chunk, cite_index)

            # Save expected rejections
            exp_path = run_logs / f"expected_rejections_{cid}.json"
            with open(exp_path, 'w', encoding='utf-8') as f:
                json.dump(expected_rejections, f, ensure_ascii=False, indent=2)

            # Pass real prompt through client with mock response
            client.chat(messages=messages, task_name=f"{task_name}/{cid}",
                       input_volume=volume, mock_response=output_text)

        # Save output
        out_path = run_logs / f"{task_name}_{cid}.jsonl"
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(output_text)

        # Validate
        val_result = run_validation(out_path, str(run_logs.name))
        rejection_rate = val_result['rejected'] / max(val_result['accepted'] + val_result['rejected'], 1)

        val_summary = {
            'chunk_id': cid,
            'volume': volume,
            'accepted': val_result['accepted'],
            'rejected': val_result['rejected'],
            'rejection_rate': round(rejection_rate, 3),
        }
        with open(val_logs / f'{cid}.json', 'w', encoding='utf-8') as f:
            json.dump(val_summary, f, ensure_ascii=False, indent=2)

        # Compare expected vs actual rejections
        if expected_rejections:
            exp_count = len(expected_rejections)
            act_count = val_summary['rejected']
            match = exp_count == act_count
            val_summary['expected_rejections'] = exp_count
            val_summary['rejection_match'] = match
            if not match:
                val_summary['rejection_mismatch'] = f'expected {exp_count}, got {act_count}'

        # Check failure criteria
        if rejection_rate > 0.2:
            if is_live:
                stop_event.set()  # Signal all threads to stop
                fuse_error['message'] = f'Rejection rate {rejection_rate:.1%} exceeds 20% threshold at {cid}'
            status = 'failed'
        else:
            status = 'ok'

        # Mark completed (thread-safe)
        completed_tracker.mark_completed(task_cid)
        client.logger.mark_chunk_completed(task_cid)

        return (cid, status, val_summary)

    except TokenBudgetExceededError as e:
        stop_event.set()
        fuse_error['message'] = str(e)
        print(f"\n  [{cid}] FUSE: {e}")
        return (cid, 'fuse', {'chunk_id': cid, 'volume': volume,
                'accepted': 0, 'rejected': 0, 'rejection_rate': 0.0,
                'error': str(e)})

    except Exception as ex:
        print(f"\n  [{cid}] ERROR: {ex}")
        return (cid, 'error', {'chunk_id': cid, 'volume': volume,
                'accepted': 0, 'rejected': 0, 'rejection_rate': 0.0,
                'error': str(ex)})

# ── Main runner ───────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description='HSR Task Runner v3')
    parser.add_argument('--task', help='Only run this task (e.g., T1_entity_relation)')
    parser.add_argument('--volume', help='Only run this volume')
    parser.add_argument('--chunk', help='Only run this chunk ID')
    parser.add_argument('--provider', default='mock', help='LLM provider profile')
    parser.add_argument('--live', action='store_true', help='Use real model (DANGER: costs tokens)')
    parser.add_argument('--skip-gate', action='store_true', help='Skip lore gate (mock only — rejected with --live)')
    parser.add_argument('--stop-after-volume', help='Stop cleanly after completing this volume')
    parser.add_argument('--concurrency', type=int, default=1, help='Concurrent chunks (default 1, recommend 3-4)')
    parser.add_argument('--run-id', default='', help='Override run_id')
    parser.add_argument('--resume', action='store_true', help='Resume from completed_chunks.txt')
    parser.add_argument('--force', action='store_true', help='Force re-run even if already completed')
    parser.add_argument('--pause-after', help='Pause after completing this chunk ID for manual review')
    args = parser.parse_args()

    # ── R2: Reject --skip-gate with --live ──
    if args.skip_gate and args.live:
        print("ERROR: --skip-gate is not allowed with --live.")
        print("  The lore gate is the only safety check before full pass1 execution.")
        print("  Correct command for live run:")
        print("    python scripts/run_tasks.py --live --run-id live_pass1_20260810 --concurrency 4")
        print("  The gate will run T1 + lore only, then stop for manual review.")
        print("  After review, resume with:")
        print("    python scripts/run_tasks.py --live --run-id live_pass1_20260810 --concurrency 4 --resume")
        sys.exit(2)

    # ── Run ID ──
    if args.run_id:
        run_id = args.run_id
    elif args.provider == 'mock' and not args.live:
        run_id = f"mock_concurrency{args.concurrency}"
    else:
        run_id = f"live_pass1_{datetime.now(timezone.utc).strftime('%Y%m%d')}"

    print(f"Run ID: {run_id}")
    print(f"Provider: {args.provider}")
    print(f"Concurrency: {args.concurrency}")
    print(f"Live: {args.live}")
    print()

    # S3: Concurrency safety warning
    MAX_RECOMMENDED_CONCURRENCY = 3
    if args.concurrency > MAX_RECOMMENDED_CONCURRENCY and (args.live or args.provider != 'mock'):
        print(f"⚠ WARNING: --concurrency {args.concurrency} > {MAX_RECOMMENDED_CONCURRENCY} (recommended max)")
        print(f"  doubao-pro-32k typical limits: ~300K TPM, ~60 RPM.")
        print(f"  At concurrency 4 with 2 min calls, peak ~2 RPM per worker → 8 RPM total (safe).")
        print(f"  At concurrency 8, peak ~4 RPM total (still safe for RPM, watch TPM).")
        print(f"  If you see 429 errors, reduce concurrency or increase rate_limit_backoff_ms.")
        print(f"  Continuing anyway...")
        print()

    # ── Live protection ──
    run_logs = LOGS / 'runs' / run_id
    if args.live or args.provider != 'mock':
        if run_logs.exists() and any(run_logs.iterdir()) and not args.resume and not args.force:
            print(f"ERROR: Live run directory '{run_logs}' already exists and is non-empty.")
            print(f"  To avoid overwriting, use a different --run-id or --resume.")
            sys.exit(1)

    val_logs = run_logs / 'validation'
    run_logs.mkdir(parents=True, exist_ok=True)
    val_logs.mkdir(parents=True, exist_ok=True)

    # ── Load configs ──
    chunk_plan = load_chunk_plan()
    cite_index = load_cite_index()
    pass2_plan = load_pass2_chunk_plan()

    print(f"Pass1 chunks: {len(chunk_plan['chunks'])}")
    if pass2_plan:
        print(f"Pass2 chunks: {pass2_plan.get('total_pass2_chunks', 'N/A')}")
    print(f"Cite index: {len(cite_index)} entries")
    print()

    # ── Completed tracker ──
    resume_path = run_logs / 'completed_chunks.txt'
    completed_tracker = CompletedTracker(resume_path)
    if args.resume:
        print(f"Resume: {len(completed_tracker)} chunks already completed")

    # ── Determine tasks ──
    tasks_to_run = []
    if args.task:
        card = load_task_card(args.task)
        if card:
            tasks_to_run = [(args.task, card)]
    else:
        for tname in ['T123_combined','T1_entity_relation','T2_event','T3_discrepancy_intra',
                      'T4_entity_merge','T5_relation_crossvol','T6_discrepancy_cross','T7_event_timeline']:
            card = load_task_card(tname)
            if card:
                tasks_to_run.append((tname, card))

    # ── Lore gate (--live only, without --skip-gate, not --force, not --resume) ──
    if args.live and not args.skip_gate and not args.resume and not args.force:
        print("=" * 60)
        print("LORE GATE — running T1 + lore only for manual review")
        print("=" * 60)
        tasks_to_run = [(t, c) for t, c in tasks_to_run if t in ('T123_combined', 'T1_entity_relation')]

    # ── Setup client ──
    client = LLMClient(profile=args.provider if args.live else 'mock', run_id=run_id)

    # ── pass1 directory for pass2 prompt building ──
    pass1_dir = BASE / 'tests' / 'fixtures' / 'mock_pass1'  # dev mode
    if args.live:
        pass1_dir = BASE / 'output' / 'pass1'  # production

    # ── Concurrency execution ──
    start_time = time.time()
    stop_event = threading.Event()
    fuse_error = {}

    total_ran = 0
    manifest = {
        'run_id': run_id,
        'provider': args.provider,
        'concurrency': args.concurrency,
        'live': args.live,
        'start_time': datetime.now(timezone.utc).isoformat(),
        'tasks': [],
    }

    for task_name, task_card in tasks_to_run:
        pass_num = task_card.get('pass', 1)
        applies_to = task_card.get('applies_to', [])

        # ── Select chunk plan: pass1 vs pass2 ──
        if pass_num == 2 and pass2_plan:
            # Use pass2 chunk plan for this task
            task_pass2 = pass2_plan.get('tasks', {}).get(task_name, {})
            pass2_chunks_list = task_pass2.get('chunks', [])
            print(f"\n  Using pass2 chunk plan: {len(pass2_chunks_list)} chunks for {task_name}")
            # For pass2, chunks are structured differently
            # We use them as pseudo-chunks for execution
            task_chunks = [{'chunk_id': c.get('chunk_id', f'P2-{i:03d}'),
                           'volume': '_pass2',
                           'entry_count': c.get('entry_count', c.get('entity_count', 0)),
                           'cite_ids': [],  # pass2 has its own input builder
                           'token_est': 0,
                           'description': c.get('description', '')}
                          for i, c in enumerate(pass2_chunks_list)]
        else:
            task_chunks = [ch for ch in chunk_plan['chunks']
                          if ch['volume'] in applies_to or '*' in str(applies_to)]

        if args.volume:
            task_chunks = [ch for ch in task_chunks if ch['volume'] == args.volume]
        if args.chunk:
            task_chunks = [ch for ch in task_chunks if ch['chunk_id'] == args.chunk]

        # Sort by value priority for pass1
        if pass_num == 1:
            task_chunks = sort_chunks_by_priority(task_chunks)
            priority_order = [c['volume'] for c in task_chunks]
            seen = set()
            unique_order = [v for v in priority_order if not (v in seen or seen.add(v))]
            print(f"  Order: {' → '.join(unique_order)}")

        # Pass2 guard
        if pass_num == 2 and args.live:
            if not check_ov_library():
                print(f"  ERROR: OpenViking library empty. Run push.py first.")
                break

        print(f"\n{'='*60}")
        print(f"{task_name} — {len(task_chunks)} chunks (concurrency={args.concurrency})")
        print(f"{'='*60}")

        task_manifest = {'task_id': task_name, 'total_chunks': len(task_chunks),
                        'completed': 0, 'failed': 0, 'stopped': 0, 'skipped': 0}

        # Lore gate: first chunk must run alone in serial
        if args.live and not args.skip_gate and not args.force and task_name in ('T123_combined', 'T1_entity_relation') and not args.resume:
            gate_chunk = task_chunks[0] if task_chunks else None
            gate_concurrency = 1
            if gate_chunk:
                print(f"  [GATE] Running lore gate chunk {gate_chunk['chunk_id']} in serial...")
                cid, status, summary = execute_chunk(
                    task_name, task_card, gate_chunk, cite_index, client,
                    run_logs, val_logs, completed_tracker, False, stop_event, fuse_error,
                    pass1_dir=pass1_dir)
                gate_status = '✓' if status == 'ok' else '✗'
                print(f"  [GATE {gate_status}] {cid}: {status} "
                      f"({summary.get('accepted', 0)} accepted, {summary.get('rejected', 0)} rejected)")
                if status == 'ok':
                    task_manifest['completed'] += 1
                    total_ran += 1
                elif status == 'failed':
                    task_manifest['failed'] += 1
                    total_ran += 1

                print(f"\n  LORE GATE COMPLETE. Review the output above.")
                print(f"  If satisfactory, resume with:")
                print(f"    python scripts/run_tasks.py --live --run-id {run_id} --concurrency {args.concurrency} --resume")
                print(f"  Exiting. Do NOT use --skip-gate with --live.")
                # Save manifest and exit
                task_manifest['total_chunks'] = 1
                manifest['tasks'].append(task_manifest)
                manifest['lore_gate_complete'] = True
                manifest['end_time'] = datetime.now(timezone.utc).isoformat()
                manifest['total_chunks_ran'] = total_ran
                with open(run_logs / 'manifest.json', 'w', encoding='utf-8') as f:
                    json.dump(manifest, f, ensure_ascii=False, indent=2)
                return

            # Remove gate chunk from concurrent list (already done)
            task_chunks = task_chunks[1:]

        # Concurrent execution for remaining chunks
        remaining = [ch for ch in task_chunks
                     if args.force or not completed_tracker.is_completed(f"{task_name}:{ch['chunk_id']}")]
        skipped = len(task_chunks) - len(remaining)
        task_manifest['skipped'] = skipped

        if args.concurrency == 1 or len(remaining) <= 1:
            # Serial mode
            for chunk in task_chunks:
                if stop_event.is_set():
                    task_manifest['stopped'] += 1
                    continue
                cid = chunk['chunk_id']
                task_cid = f"{task_name}:{cid}"
                if not args.force and completed_tracker.is_completed(task_cid):
                    print(f"  [{cid}] SKIP (completed)")
                    task_manifest['skipped'] += 1
                    continue

                print(f"  [{cid}] {chunk.get('volume','?')} "
                      f"({chunk.get('entry_count',0)} entries, ~{chunk.get('token_est',0):,} tokens)...", end=' ', flush=True)
                cid, status, summary = execute_chunk(
                    task_name, task_card, chunk, cite_index, client,
                    run_logs, val_logs, completed_tracker,
                    args.live, stop_event, fuse_error, pass1_dir=pass1_dir,
                    force=args.force)

                if status == 'ok':
                    print(f"OK ({summary.get('accepted',0)}a/{summary.get('rejected',0)}r)")
                    task_manifest['completed'] += 1
                elif status == 'skipped':
                    task_manifest['skipped'] += 1
                elif status == 'stopped':
                    task_manifest['stopped'] += 1
                else:
                    print(f"{status}")
                    task_manifest['failed'] += 1
                total_ran += 1

                # Pause-after
                if args.pause_after and cid == args.pause_after:
                    print(f"\n  ⏸ PAUSE: --pause-after {args.pause_after} reached")
                    print(f"  Chunk {cid}: {status} ({summary.get('accepted',0)}a/{summary.get('rejected',0)}r)")
                    manifest['stop_reason'] = f'pause_after_{args.pause_after}'
                    manifest['end_time'] = datetime.now(timezone.utc).isoformat()
                    manifest['total_chunks_ran'] = total_ran
                    with open(run_logs / 'manifest.json', 'w', encoding='utf-8') as f:
                        json.dump(manifest, f, ensure_ascii=False, indent=2)
                    return

                # Stop-after-volume
                if args.stop_after_volume and chunk['volume'] == args.stop_after_volume:
                    if all(completed_tracker.is_completed(f"{task_name}:{c['chunk_id']}")
                           for c in chunk_plan['chunks'] if c['volume'] == args.stop_after_volume):
                        print(f"\n  STOP: --stop-after-volume {args.stop_after_volume}")
                        manifest['stop_reason'] = f'volume_{args.stop_after_volume}_complete'
                        manifest['end_time'] = datetime.now(timezone.utc).isoformat()
                        manifest['total_chunks_ran'] = total_ran
                        with open(run_logs / 'manifest.json', 'w', encoding='utf-8') as f:
                            json.dump(manifest, f, ensure_ascii=False, indent=2)
                        return
        else:
            # Concurrent mode
            with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
                futures = {}
                for chunk in task_chunks:
                    cid = chunk['chunk_id']
                    task_cid = f"{task_name}:{cid}"
                    if not args.force and completed_tracker.is_completed(task_cid):
                        print(f"  [{cid}] SKIP (completed)")
                        task_manifest['skipped'] += 1
                        continue
                    if stop_event.is_set():
                        task_manifest['stopped'] += 1
                        continue
                    future = executor.submit(
                        execute_chunk, task_name, task_card, chunk, cite_index, client,
                        run_logs, val_logs, completed_tracker,
                        args.live, stop_event, fuse_error, pass1_dir=pass1_dir,
                        force=args.force)
                    futures[future] = chunk

                for future in as_completed(futures):
                    chunk = futures[future]
                    cid = chunk['chunk_id']
                    try:
                        cid_r, status, summary = future.result()
                        if status == 'ok':
                            print(f"  [{cid}] OK ({summary.get('accepted',0)}a/{summary.get('rejected',0)}r)")
                            task_manifest['completed'] += 1
                        elif status == 'skipped':
                            task_manifest['skipped'] += 1
                        elif status in ('stopped', 'fuse'):
                            print(f"  [{cid}] {status.upper()}: {summary.get('error', '')[:120]}")
                            task_manifest['stopped'] += 1
                        else:
                            print(f"  [{cid}] {status}: {summary.get('error', str(summary))[:120]}")
                            task_manifest['failed'] += 1
                        total_ran += 1
                    except Exception as ex:
                        print(f"  [{cid}] FUTURE ERROR: {ex}")
                        task_manifest['failed'] += 1

        manifest['tasks'].append(task_manifest)

        # Check fuse after task
        if stop_event.is_set():
            print(f"\n  FUSE TRIGGERED: {fuse_error.get('message', 'unknown')}")
            print(f"  Stopping further task dispatch.")
            break

    # ── Finalize ──
    elapsed = time.time() - start_time
    manifest['end_time'] = datetime.now(timezone.utc).isoformat()
    manifest['total_chunks_ran'] = total_ran
    manifest['elapsed_seconds'] = round(elapsed, 1)
    if stop_event.is_set():
        manifest['fuse_error'] = fuse_error.get('message', '')
    with open(run_logs / 'manifest.json', 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"RUN COMPLETE: {total_ran} chunks in {elapsed:.1f}s "
          f"(concurrency={args.concurrency})")
    print(f"Manifest: {run_logs / 'manifest.json'}")
    print(f"Completed chunks: {(run_logs / 'completed_chunks.txt').read_text(encoding='utf-8').strip().count(chr(10)) + 1}")

if __name__ == '__main__':
    main()
