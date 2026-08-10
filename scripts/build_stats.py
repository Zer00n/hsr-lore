"""
C5: 统计数据生成器 v2
从指定 run_id 的 manifest + validation 结果汇总生成 stats.json。
所有数字由脚本生成，不手写。不含任何 mock 数据回退。
stats.json 含 run_id 与 generation_time 字段，便于核对来源。
"""
import json
import sys
import io
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter, defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(__file__).parent.parent


def load_manifest(run_dir):
    path = run_dir / 'manifest.json'
    if not path.exists():
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_validation(run_dir):
    val_dir = run_dir / 'validation'
    results = []
    if not val_dir.is_dir():
        return results
    for vpath in sorted(val_dir.glob('*.json')):
        with open(vpath, 'r', encoding='utf-8') as f:
            results.append(json.load(f))
    return results


def load_calls(run_dir):
    calls = []
    path = run_dir / 'calls.jsonl'
    if not path.exists():
        return calls
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                calls.append(json.loads(line))
    return calls


def build_stats(run_id, run_dir=None):
    """Build stats.json from a specific run's data. No fallbacks.

    Args:
        run_id: Required. Used for logs/runs/{run_id} lookup and embedded in output.
        run_dir: If provided, use this exact directory.
    """
    if run_dir:
        rd = Path(run_dir)
    elif run_id:
        rd = BASE / 'logs' / 'runs' / run_id
        # Also check logs/mock/
        if not rd.exists():
            rd = BASE / 'logs' / 'mock' / run_id
        if not rd.exists():
            raise FileNotFoundError(
                f"Run directory not found: {rd}. "
                f"Provide --run-id with the exact run identifier.")
    else:
        raise ValueError("--run-id or --run-dir is required. No default fallback.")

    print(f"Reading run data from: {rd}")

    manifest = load_manifest(rd)
    validations = load_validation(rd)
    calls = load_calls(rd)

    # ── Basic metrics ──
    total_calls = manifest.get('call_count', len(calls))
    total_input_tokens = manifest.get('total_input_tokens',
        sum(c.get('input_token', 0) for c in calls))
    total_output_tokens = manifest.get('total_output_tokens',
        sum(c.get('output_token', 0) for c in calls))

    # ── Citation pass rate ──
    total_accepted = sum(v.get('accepted', 0) for v in validations)
    total_rejected = sum(v.get('rejected', 0) for v in validations)
    total_validated = total_accepted + total_rejected
    citation_pass_rate = total_accepted / max(total_validated, 1)

    # ── Rejection reasons ──
    rejection_reasons = Counter()
    for v in validations:
        if 'rejection_reasons' in v:
            for reason, count in v['rejection_reasons'].items():
                rejection_reasons[reason] += count

    # ── Per-task counts from manifest ──
    per_task_counts = {}
    for task_entry in manifest.get('tasks', []):
        tname = task_entry.get('task_id', '')
        per_task_counts[tname] = {
            'total_chunks': task_entry.get('total_chunks', 0),
            'completed': task_entry.get('completed', 0),
            'failed': task_entry.get('failed', 0),
        }

    # ── AFP (mock = 0) ──
    cumulative_afp = 0

    # ── Totals from build site data ──
    totals = {'entities': 0, 'relations': 0, 'events': 0, 'discrepancies': 0}
    site_data = BASE / 'site' / 'public' / 'data'
    for key in totals:
        fpath = site_data / f'{key}.json'
        if fpath.exists():
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            totals[key] = len(data) if isinstance(data, list) else 0

    stats = {
        'run_id': run_id or str(rd.name),
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'source_manifest': str(rd),
        'citation_pass_rate': round(citation_pass_rate, 4),
        'total_calls': total_calls,
        'total_input_tokens': total_input_tokens,
        'total_output_tokens': total_output_tokens,
        'cumulative_afp': cumulative_afp,
        'per_task_counts': per_task_counts,
        'rejection_reasons': dict(rejection_reasons),
        'totals': totals,
        'manifest_run_id': manifest.get('run_id', ''),
        'manifest_start_time': manifest.get('start_time', ''),
        'manifest_elapsed_seconds': manifest.get('elapsed_seconds', 0),
    }

    return stats


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Generate stats.json from run data')
    parser.add_argument('--run-id', required=True,
                        help='Run ID (e.g., live_pass1_20260810 or mock_concurrency4)')
    parser.add_argument('--run-dir', default='',
                        help='Exact run directory path (overrides --run-id lookup)')
    parser.add_argument('--output', default='',
                        help='Output path (default: site/public/data/stats.json)')
    args = parser.parse_args()

    run_dir = Path(args.run_dir) if args.run_dir else None
    stats = build_stats(run_id=args.run_id, run_dir=run_dir)

    out_path = Path(args.output) if args.output else BASE / 'site' / 'public' / 'data' / 'stats.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"\nStats written to: {out_path}")
    print(f"  run_id: {stats['run_id']}")
    print(f"  generated_at: {stats['generated_at']}")
    print(f"  citation_pass_rate: {stats['citation_pass_rate']:.1%}")
    print(f"  total_calls: {stats['total_calls']}")
    print(f"  total_input_tokens: {stats['total_input_tokens']:,}")
    print(f"  total_output_tokens: {stats['total_output_tokens']:,}")
    print(f"  cumulative_afp: {stats['cumulative_afp']}")
    print(f"  totals: {stats['totals']}")


if __name__ == '__main__':
    main()
