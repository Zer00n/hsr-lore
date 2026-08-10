"""
Block-level metrics recorder.
Reads run directory outputs and computes per-chunk quality metrics.
Run independently from run_tasks.py — safe to call during a live run.
"""
import json, sys, io, os, re, subprocess
from pathlib import Path
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(__file__).parent.parent
RUN_DIR = BASE / 'logs' / 'runs' / 'live_pass1_20260810'
VALID_TYPES = {'AEON', 'PATH', 'CHAR', 'ORGN', 'PLAC', 'WRLD', 'CONC', 'ARTF', 'RACE'}
VALID_PREDS = {'EMBODIES', 'EMISSARY_OF', 'FOLLOWER_OF', 'OPPOSES',
               'MEMBER_OF', 'LEADS', 'MENTOR_OF', 'KIN_OF', 'ALLY_OF',
               'ENEMY_OF', 'SUCCEEDS', 'CREATED', 'KILLED', 'TRANSFORMED_INTO',
               'LOCATED_IN', 'ORIGINATES_FROM', 'RULES',
               'PARTICIPATED_IN', 'CAUSED', 'RESULTED_IN', 'RELATED_TO'}
SCHEMA_FIELDS_ENTITY = {'type', 'canonical_name', 'summary'}
SCHEMA_FIELDS_RELATION = {'subject_name', 'predicate', 'object_name'}
SCHEMA_FIELDS_EVENT = {'name', 'summary'}
SCHEMA_FIELDS_DISCREPANCY = {'kind', 'topic', 'statements', 'analysis'}


def compute_metrics(chunk_id, volume, entry_count):
    """Compute metrics for a completed chunk from its output files."""
    # Find output file (any task prefix)
    output_files = list(RUN_DIR.glob(f'*_{chunk_id}.jsonl'))
    if not output_files:
        print(f'  {chunk_id}: no output file found')
        return None

    output_path = output_files[0]

    # Read objects
    objects = []
    with open(output_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                objects.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    if not objects:
        print(f'  {chunk_id}: empty output')
        return None

    # Read calls.jsonl for this chunk
    calls = []
    if (RUN_DIR / 'calls.jsonl').exists():
        with open(RUN_DIR / 'calls.jsonl', 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    c = json.loads(line)
                    if chunk_id in c.get('task_name', ''):
                        calls.append(c)

    # Read validation
    val_path = RUN_DIR / 'validation' / f'{chunk_id}.json'
    validation = {}
    if val_path.exists():
        with open(val_path, 'r', encoding='utf-8') as f:
            validation = json.load(f)

    # Compute metrics
    total = len(objects)
    cited = 0
    schema_ok = 0
    type_ok = 0
    pred_ok = 0
    total_relations = 0
    total_entities = 0

    for obj in objects:
        # Citation check
        has_cit = False
        def check_cit(o, depth=0):
            nonlocal has_cit
            if depth > 10:
                return
            if isinstance(o, dict):
                if 'citations' in o and isinstance(o['citations'], list) and len(o['citations']) > 0:
                    has_cit = True
                for v in o.values():
                    check_cit(v, depth + 1)
            elif isinstance(o, list):
                for item in o:
                    check_cit(item, depth + 1)
        check_cit(obj)
        if has_cit:
            cited += 1

        # Entity checks
        t = obj.get('type', '')
        if t in VALID_TYPES:
            type_ok += 1
            total_entities += 1
            if SCHEMA_FIELDS_ENTITY.issubset(obj.keys()):
                schema_ok += 1
        elif t == 'entity' and 'entity_type' in obj:
            total_entities += 1
        elif 'predicate' in obj or 'relation_type' in obj:
            total_relations += 1
            pred = obj.get('predicate', obj.get('relation_type', ''))
            if pred in VALID_PREDS:
                pred_ok += 1
            if SCHEMA_FIELDS_RELATION.issubset(obj.keys()) or (
                'subject' in obj and 'object' in obj):
                schema_ok += 1
        elif 'kind' in obj:
            if SCHEMA_FIELDS_DISCREPANCY.issubset(obj.keys()):
                schema_ok += 1
        elif 'name' in obj and ('participants' in obj or 'stated_time' in obj):
            if SCHEMA_FIELDS_EVENT.issubset(obj.keys()):
                schema_ok += 1

    # Token info
    input_tokens = 0
    elapsed = 0
    finish_reason = ''
    if calls:
        last_call = calls[-1]
        input_tokens = last_call.get('input_token', 0)
        elapsed = last_call.get('latency_ms', 0) / 1000
        finish_reason = last_call.get('finish_reason', '')

    metrics = {
        'chunk_id': chunk_id,
        'volume': volume,
        'input_tokens': input_tokens,
        'entry_count': entry_count,
        'avg_entry_tokens': round(input_tokens / max(entry_count, 1), 1),
        'output_objects': total,
        'citation_rate': round(cited / max(total, 1), 3),
        'schema_compliance': round(schema_ok / max(total, 1), 3),
        'type_compliance': round(type_ok / max(total_entities, 1), 3) if total_entities else 0,
        'predicate_compliance': round(pred_ok / max(total_relations, 1), 3) if total_relations else 0,
        'rejection_rate': validation.get('rejection_rate', 0),
        'rejection_reasons': {},  # filled below
        'elapsed_sec': round(elapsed, 1),
        'finish_reason': finish_reason,
    }

    # Extract rejection reasons by running validate.py as subprocess
    backfilled = list(RUN_DIR.glob(f'*_{chunk_id}_backfilled.jsonl'))
    if backfilled:
        try:
            result = subprocess.run(
                [sys.executable, str(BASE / 'scripts' / 'validate.py'), str(backfilled[0])],
                capture_output=True, text=True, timeout=30,
                encoding='utf-8', errors='replace'
            )
            # Parse rejection reasons from validate output
            reason_counts = Counter()
            in_reasons = False
            for line in result.stdout.split('\n'):
                if 'Rejection reasons:' in line:
                    in_reasons = True
                    continue
                if in_reasons and line.strip():
                    m = re.match(r'\s*\[ *(\d+)\] (\w+)', line)
                    if m:
                        reason_counts[m.group(2)] += int(m.group(1))
                    else:
                        break
            metrics['rejection_reasons'] = dict(reason_counts.most_common())
        except Exception as e:
            metrics['rejection_reasons'] = {'error': str(e)[:100]}

    return metrics


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--summary', action='store_true', help='Print summary table')
    args = parser.parse_args()

    # Load chunk plan
    with open(BASE / 'config' / 'task_chunks.json', 'r', encoding='utf-8') as f:
        plan = json.load(f)

    # Scan completed chunks
    output_files = list(RUN_DIR.glob('*_*.jsonl'))
    completed_ids = set()
    for f in output_files:
        if '_backfilled' in f.name:
            continue
        cid = f.stem.split('_')[-1]
        completed_ids.add(cid)

    # Build chunk lookup
    chunk_lookup = {}
    for ch in plan.get('chunks', []):
        chunk_lookup[ch['chunk_id']] = ch

    # Compute metrics
    all_metrics = []
    metrics_path = BASE / 'work' / 'block_metrics.jsonl'

    # Load existing metrics
    existing_ids = set()
    if metrics_path.exists():
        with open(metrics_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    m = json.loads(line)
                    existing_ids.add(m['chunk_id'])
                    all_metrics.append(m)

    # Compute new metrics
    for cid in sorted(completed_ids):
        if cid in existing_ids:
            continue
        ch = chunk_lookup.get(cid, {})
        vol = ch.get('volume', '?')
        ec = ch.get('entry_count', 0)
        m = compute_metrics(cid, vol, ec)
        if m:
            all_metrics.append(m)
            print(f'  {cid} ({vol}): {m["output_objects"]} objs, '
                  f'cit={m["citation_rate"]:.0%}, schema={m["schema_compliance"]:.0%}, '
                  f'type={m["type_compliance"]:.0%}, pred={m["predicate_compliance"]:.0%}, '
                  f'rej={m["rejection_rate"]:.0%}, {m["elapsed_sec"]:.0f}s')

    # Write all metrics
    all_metrics.sort(key=lambda m: m['chunk_id'])
    with open(metrics_path, 'w', encoding='utf-8') as f:
        for m in all_metrics:
            f.write(json.dumps(m, ensure_ascii=False) + '\n')

    # Summary table
    if args.summary and all_metrics:
        print('\n' + '=' * 90)
        print('PER-BLOCK METRICS')
        print('=' * 90)
        print(f'{"Chunk":7s} {"Vol":12s} {"InTok":>8s} {"Obj":>5s} {"Cite":>6s} {"Schema":>7s} {"Type":>6s} {"Pred":>6s} {"Rej":>5s} {"Time":>7s}')
        print('-' * 90)

        by_vol = {}
        for m in all_metrics:
            vol = m['volume']
            if vol not in by_vol:
                by_vol[vol] = []
            by_vol[vol].append(m)

            print(f'{m["chunk_id"]:7s} {m["volume"]:12s} {m["input_tokens"]:>8,} {m["output_objects"]:>5d} '
                  f'{m["citation_rate"]:>5.0%} {m["schema_compliance"]:>6.0%} '
                  f'{m["type_compliance"]:>5.0%} {m["predicate_compliance"]:>5.0%} '
                  f'{m["rejection_rate"]:>4.0%} {m["elapsed_sec"]:>6.0f}s')

        print('-' * 90)
        print('\nBY VOLUME (sorted by citation_rate):')
        for vol in sorted(by_vol.keys()):
            ms = by_vol[vol]
            avg_cit = sum(m['citation_rate'] for m in ms) / len(ms)
            avg_schema = sum(m['schema_compliance'] for m in ms) / len(ms)
            avg_type = sum(m['type_compliance'] for m in ms) / len(ms)
            avg_pred = sum(m['predicate_compliance'] for m in ms) / len(ms)
            avg_rej = sum(m['rejection_rate'] for m in ms) / len(ms)
            total_obj = sum(m['output_objects'] for m in ms)
            total_time = sum(m['elapsed_sec'] for m in ms)
            print(f'  {vol:14s} {len(ms):>3d} blocks  '
                  f'avg_cit={avg_cit:.0%}  avg_schema={avg_schema:.0%}  '
                  f'avg_type={avg_type:.0%}  avg_pred={avg_pred:.0%}  '
                  f'avg_rej={avg_rej:.0%}  '
                  f'objects={total_obj}  time={total_time/60:.0f}min')

        # Write to stats
        stats_path = BASE / 'work' / 'stats.json'
        stats = {}
        if stats_path.exists():
            with open(stats_path, 'r', encoding='utf-8') as f:
                stats = json.load(f)
        stats['block_metrics'] = {
            'total_blocks': len(all_metrics),
            'by_volume': {
                vol: {
                    'count': len(ms),
                    'avg_citation_rate': round(sum(m['citation_rate'] for m in ms) / len(ms), 3),
                    'avg_schema_compliance': round(sum(m['schema_compliance'] for m in ms) / len(ms), 3),
                    'avg_type_compliance': round(sum(m['type_compliance'] for m in ms) / len(ms), 3),
                    'avg_predicate_compliance': round(sum(m['predicate_compliance'] for m in ms) / len(ms), 3),
                    'avg_rejection_rate': round(sum(m['rejection_rate'] for m in ms) / len(ms), 3),
                    'total_objects': sum(m['output_objects'] for m in ms),
                    'total_time_sec': sum(m['elapsed_sec'] for m in ms),
                }
                for vol, ms in by_vol.items()
            },
            'chunks': all_metrics,
        }
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        print(f'\nStats written to {stats_path}')

    print(f'\nMetrics file: {metrics_path} ({len(all_metrics)} blocks)')


if __name__ == '__main__':
    main()
