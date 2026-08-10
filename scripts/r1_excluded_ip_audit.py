"""
R1: Fate/IP 联动排除重查
输出 work/r1_excluded_ip_audit.json
列出 excluded_ip.jsonl 中每条记录的判据字段原始值，不含先验知识标签。
"""
import json, sys, io, os
from collections import defaultdict, Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(BASE, 'work')
CORPUS = os.path.join(BASE, 'corpus')

def main():
    entries = []
    with open(os.path.join(CORPUS, 'excluded_ip.jsonl'), 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))

    report = {
        'total_entries': len(entries),
        'source_tables': Counter(),
        'by_cite_id_type': Counter(),
        'by_source_pk': defaultdict(list),
        'exclusion_meta_values': Counter(),
        'sample_entries': [],
    }

    for e in entries:
        st = e.get('source_table', 'unknown')
        report['source_tables'][st] += 1

        cite_type = e['cite_id'].split('-')[0] if '-' in e['cite_id'] else 'unknown'
        report['by_cite_id_type'][cite_type] += 1

        pk = e.get('source_pk', 'unknown')
        report['by_source_pk'][str(pk)].append({
            'cite_id': e['cite_id'],
            'title': e.get('title', ''),
            'raw_preview': e.get('raw', '')[:80],
        })

        em = e.get('meta', {})
        for k, v in em.items():
            report['exclusion_meta_values'][f"{k}={v}"] += 1

    # Compute per-source_pk entry counts
    pk_counts = {}
    for pk, items in report['by_source_pk'].items():
        pk_counts[pk] = len(items)
    report['unique_source_pks'] = len(pk_counts)
    report['pk_distribution'] = {
        '1_entry': sum(1 for c in pk_counts.values() if c == 1),
        '2_10_entries': sum(1 for c in pk_counts.values() if 2 <= c <= 10),
        '11_50_entries': sum(1 for c in pk_counts.values() if 11 <= c <= 50),
        '51_plus_entries': sum(1 for c in pk_counts.values() if c >= 51),
    }
    report['top_pks_by_count'] = sorted(pk_counts.items(), key=lambda x: -x[1])[:15]

    # Detailed listing of every unique source_pk with its first entry
    report['all_source_pks_detail'] = []
    for pk in sorted(pk_counts.keys(), key=lambda x: int(x) if x.isdigit() else 0):
        items = report['by_source_pk'][pk]
        report['all_source_pks_detail'].append({
            'source_pk': pk,
            'entry_count': len(items),
            'sample_cite_id': items[0]['cite_id'],
            'sample_title': items[0]['title'],
            'sample_raw': items[0]['raw_preview'],
        })

    # Sample: first 5 across different pks
    seen_pks = set()
    for e in entries:
        pk = str(e.get('source_pk', ''))
        if pk not in seen_pks and len(report['sample_entries']) < 10:
            seen_pks.add(pk)
            report['sample_entries'].append({
                'cite_id': e['cite_id'],
                'source_table': e['source_table'],
                'source_field': e['source_field'],
                'source_pk': e['source_pk'],
                'title': e.get('title', ''),
                'meta': e.get('meta', {}),
                'raw_first_120_chars': e.get('raw', '')[:120],
            })

    # Convert Counter to dict for JSON
    report['source_tables'] = dict(report['source_tables'])
    report['by_cite_id_type'] = dict(report['by_cite_id_type'])
    report['exclusion_meta_values'] = dict(report['exclusion_meta_values'])

    outpath = os.path.join(WORK, 'r1_excluded_ip_audit.json')
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"R1 done: {len(entries)} entries, {len(pk_counts)} unique source_pks")
    print(f"Output: {outpath}")

    # Print summary for inline verification
    print(f"\nSource tables: {report['source_tables']}")
    print(f"Cite ID types: {report['by_cite_id_type']}")
    print(f"Exclusion meta values: {report['exclusion_meta_values']}")
    print(f"PK distribution: {report['pk_distribution']}")
    print(f"Top PKs by count: {report['top_pks_by_count']}")

if __name__ == '__main__':
    main()
