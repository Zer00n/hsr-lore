"""
R4: 残留标记重新扫描
扫描全部 clean 字段，检测残余标记模式。
主卷（7卷）与隔离卷（speakerless + excluded_ip）分开统计。
输出 work/r4_residual_patterns_v2.json
"""
import json, sys, io, os, re
from collections import defaultdict, Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(BASE, 'work')
CORPUS = os.path.join(BASE, 'corpus')

MAIN_VOLUMES = ['lore', 'books', 'characters', 'narrative', 'dialogue', 'artifacts', 'rogue']
ISOLATION_VOLUMES = ['speakerless', 'excluded_ip']

# Patterns to scan for
PATTERNS = {
    'angle_brackets': re.compile(r'<[^>]*>'),           # <anything>
    'curly_braces': re.compile(r'\{[^}]*\}'),            # {anything}
    'hash_placeholders': re.compile(r'#\d+\[[^\]]*\]'),  # #1[i], #2[f1]
    'backslash_n': re.compile(r'\\n'),                    # \n
    'backslash_other': re.compile(r'\\[^n]'),             # \r, \t, etc.
    'ruby_B': re.compile(r'\{RUBY_B[^}]*\}'),            # {RUBY_B#...}
    'ruby_E': re.compile(r'\{RUBY_E[^}]*\}'),            # {RUBY_E#...}
    'nickname': re.compile(r'\{NICKNAME\}'),              # {NICKNAME}
    'gender_F': re.compile(r'\{F#[^}]*\}'),              # {F#...}
    'gender_M': re.compile(r'\{M#[^}]*\}'),              # {M#...}
    'textjoin': re.compile(r'\{TEXTJOIN[^}]*\}'),        # {TEXTJOIN#...}
    'textid': re.compile(r'\{TextID[^}]*\}'),            # {TextID#...}
}

def scan_entries(entries, label):
    results = {name: {'count': 0, 'entries_with': 0, 'samples': []} for name in PATTERNS}

    for e in entries:
        clean = e.get('clean', '')
        for pname, pattern in PATTERNS.items():
            matches = pattern.findall(clean)
            if matches:
                results[pname]['count'] += len(matches)
                results[pname]['entries_with'] += 1
                if len(results[pname]['samples']) < 5:
                    results[pname]['samples'].append({
                        'cite_id': e.get('cite_id', '?'),
                        'volume': e.get('volume', label),
                        'file': e.get('source_table', '?'),
                        'matches': matches[:5],
                        'context': clean[:200],
                    })

    return results

def main():
    report = {'main_volumes': {}, 'isolation_volumes': {}, 'combined': {}}

    # Scan main volumes
    for vol in MAIN_VOLUMES:
        path = os.path.join(CORPUS, f'{vol}.jsonl')
        if not os.path.exists(path):
            continue
        entries = []
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        entries.append(json.loads(line))
                    except:
                        pass
        report['main_volumes'][vol] = scan_entries(entries, vol)
        print(f"  {vol}: {len(entries)} entries scanned")

    # Scan isolation volumes
    for vol in ISOLATION_VOLUMES:
        path = os.path.join(CORPUS, f'{vol}.jsonl')
        if not os.path.exists(path):
            continue
        entries = []
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        entries.append(json.loads(line))
                    except:
                        pass
        report['isolation_volumes'][vol] = scan_entries(entries, vol)
        print(f"  {vol}: {len(entries)} entries scanned")

    # Combine pattern stats
    for scope_name, scope_data in [('main', report['main_volumes']), ('isolation', report['isolation_volumes'])]:
        combined = {}
        for pname in PATTERNS:
            total_count = sum(vol_data[pname]['count'] for vol_data in scope_data.values())
            total_entries = sum(vol_data[pname]['entries_with'] for vol_data in scope_data.values())
            all_samples = []
            for vol_data in scope_data.values():
                all_samples.extend(vol_data[pname]['samples'])
            combined[pname] = {
                'total_matches': total_count,
                'total_entries_affected': total_entries,
                'samples': all_samples[:3],
            }
        report['combined'][scope_name] = combined

    # Build summary table
    summary = []
    for pname in PATTERNS:
        mc = report['combined']['main'].get(pname, {})
        ic = report['combined']['isolation'].get(pname, {})
        summary.append({
            'pattern': pname,
            'regex': PATTERNS[pname].pattern,
            'main_matches': mc.get('total_matches', 0),
            'main_entries': mc.get('total_entries_affected', 0),
            'isolation_matches': ic.get('total_matches', 0),
            'isolation_entries': ic.get('total_entries_affected', 0),
        })
    report['summary_table'] = summary

    outpath = os.path.join(WORK, 'r4_residual_patterns_v2.json')
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\nR4 done. Output: {outpath}")
    print(f"\n{'Pattern':<25s} {'Main':>8s} {'(entries)':>10s} {'Isolation':>10s} {'(entries)':>10s}")
    print('-' * 70)
    for s in summary:
        print(f"{s['pattern']:<25s} {s['main_matches']:>8d} {s['main_entries']:>10d} {s['isolation_matches']:>10d} {s['isolation_entries']:>10d}")

if __name__ == '__main__':
    main()
