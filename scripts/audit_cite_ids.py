"""
cite_id 重复审计
扫描全库 296,849 条 cite_id，逐条列出重复出现在哪些卷、内容是否一致。
输出 work/cite_id_duplicates.json
"""
import json, sys, io, os
from collections import defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(__file__).parent.parent
CORPUS = BASE / 'corpus'
WORK_DIR = BASE / 'work'

MAIN_VOLS = ['lore', 'books', 'characters', 'narrative', 'dialogue', 'artifacts', 'rogue', 'unattributed']
ISO_VOLS = ['speakerless', 'excluded_ip']
ALL_VOLS = MAIN_VOLS + ISO_VOLS

def main():
    # Load all cite_id → (volume, clean) mappings
    cid_map = defaultdict(list)
    for vol in ALL_VOLS:
        path = CORPUS / f'{vol}.jsonl'
        if not path.exists():
            continue
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    e = json.loads(line)
                    cid_map[e['cite_id']].append({
                        'volume': vol,
                        'cite_id': e['cite_id'],
                        'clean': e.get('clean', ''),
                        'title': e.get('title', ''),
                    })

    # Find duplicates
    total_entries = sum(len(items) for items in cid_map.values())
    unique_cids = len(cid_map)
    duplicate_cids = {cid: items for cid, items in cid_map.items() if len(items) > 1}
    dup_entries = sum(len(items) for items in duplicate_cids.values())
    excess = dup_entries - len(duplicate_cids)

    print(f"Total entries: {total_entries}")
    print(f"Unique cite_ids: {unique_cids}")
    print(f"Duplicate cite_ids: {len(duplicate_cids)}")
    print(f"Duplicate entries (excess): {excess}")
    print(f"Expected excess: {total_entries - unique_cids}")

    # Categorize duplicates
    by_vol_pair = defaultdict(int)
    content_mismatch = []
    categories = defaultdict(int)

    for cid, items in duplicate_cids.items():
        vols = tuple(sorted(set(i['volume'] for i in items)))
        by_vol_pair[vols] += 1

        # Check content consistency
        cleans = [i['clean'] for i in items]
        all_same = all(c == cleans[0] for c in cleans)
        if not all_same:
            content_mismatch.append({
                'cite_id': cid,
                'volumes': vols,
                'entries': [{'volume': i['volume'], 'clean_preview': i['clean'][:100]} for i in items],
            })

        # Categorize
        if 'narrative' in vols and ('unattributed' in vols or 'speakerless' in vols):
            categories['narrative_vs_speakerless'] += 1
        elif 'dialogue' in vols and ('unattributed' in vols or 'speakerless' in vols):
            categories['dialogue_vs_speakerless'] += 1
        elif 'excluded_ip' in vols:
            categories['involving_excluded_ip'] += 1
        elif set(vols).issubset(set(ISO_VOLS)):
            categories['isolation_only'] += 1
        elif set(vols).issubset(set(MAIN_VOLS)):
            categories['main_volume_overlap'] += 1
        else:
            categories['other'] += 1

    report = {
        'total_entries': total_entries,
        'unique_cite_ids': unique_cids,
        'duplicate_cite_ids': len(duplicate_cids),
        'excess_entries': excess,
        'by_volume_pair': {str(k): v for k, v in sorted(by_vol_pair.items(), key=lambda x: -x[1])},
        'categories': dict(categories),
        'content_mismatches': content_mismatch,
        'reconciliation': {},
    }

    # Build exact reconciliation
    print(f"\n=== Volume pair breakdown ===")
    for pair, count in sorted(by_vol_pair.items(), key=lambda x: -x[1]):
        print(f"  {' & '.join(pair)}: {count} duplicate cite_ids ({count} excess entries)")

    print(f"\n=== Category breakdown ===")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    # Reconcile: 13,344 narrative overlap
    narr_dup = categories.get('narrative_vs_speakerless', 0)
    dial_dup = categories.get('dialogue_vs_speakerless', 0)
    excl_dup = categories.get('involving_excluded_ip', 0)
    iso_dup = categories.get('isolation_only', 0)
    main_dup = categories.get('main_volume_overlap', 0)
    other_dup = categories.get('other', 0)

    # Verify
    sum_cats = narr_dup + dial_dup + excl_dup + iso_dup + main_dup + other_dup
    print(f"\n=== Reconciliation ===")
    print(f"  narrative vs speakerless/unattributed: {narr_dup}")
    print(f"  dialogue vs speakerless/unattributed:  {dial_dup}")
    print(f"  involving excluded_ip:                {excl_dup}")
    print(f"  isolation only (speakerless vs excl):  {iso_dup}")
    print(f"  main volume internal:                 {main_dup}")
    print(f"  other:                                {other_dup}")
    print(f"  Total: {sum_cats} (expected {len(duplicate_cids)})")

    if sum_cats != len(duplicate_cids):
        print(f"  WARNING: {len(duplicate_cids) - sum_cats} unaccounted!")

    # Content mismatch report
    if content_mismatch:
        print(f"\n=== CONTENT MISMATCHES ({len(content_mismatch)}) ===")
        for cm in content_mismatch[:20]:
            print(f"  {cm['cite_id']}: {' & '.join(cm['volumes'])}")
            for entry in cm['entries']:
                print(f"    [{entry['volume']}] {entry['clean_preview']}")

    report['reconciliation'] = {
        'narrative_vs_speakerless': narr_dup,
        'dialogue_vs_speakerless': dial_dup,
        'involving_excluded_ip': excl_dup,
        'isolation_only': iso_dup,
        'main_volume_internal': main_dup,
        'other': other_dup,
        'total': sum_cats,
        'expected': len(duplicate_cids),
        'balanced': sum_cats == len(duplicate_cids),
    }

    outpath = WORK_DIR / 'cite_id_duplicates.json'
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nOutput: {outpath}")

if __name__ == '__main__':
    main()
