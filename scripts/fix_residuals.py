"""
修复清洗残留：\n 转义、TEXTJOIN、NICKNAME
写进 extract.py 的 resolve() 函数或直接修复语料文件。
输出修复前后的对比到 work/cleaning_fix_report.json
"""
import json, sys, io, os, re
from collections import defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(__file__).parent.parent
CORPUS = BASE / 'corpus'

def scan_residuals():
    """Scan all main volume corpus files for residuals."""
    volumes = ['lore', 'books', 'characters', 'narrative', 'dialogue', 'artifacts', 'rogue']
    findings = {
        'backslash_n': [],
        'textjoin': [],
        'nickname': [],
    }
    for vol in volumes:
        path = CORPUS / f'{vol}.jsonl'
        if not path.exists():
            continue
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                e = json.loads(line)
                clean = e.get('clean', '')
                if '\\n' in clean:
                    findings['backslash_n'].append({
                        'cite_id': e['cite_id'],
                        'volume': vol,
                        'source_table': e['source_table'],
                        'source_field': e['source_field'],
                        'clean': clean,
                    })
                if '{TEXTJOIN' in clean:
                    findings['textjoin'].append({
                        'cite_id': e['cite_id'],
                        'volume': vol,
                        'source_table': e['source_table'],
                        'source_field': e['source_field'],
                        'clean': clean,
                    })
                if '{NICKNAME}' in clean:
                    findings['nickname'].append({
                        'cite_id': e['cite_id'],
                        'volume': vol,
                        'source_table': e['source_table'],
                        'source_field': e['source_field'],
                        'clean': clean,
                    })

    return findings

def fix_residuals(findings):
    """Fix all residuals in corpus files."""
    # Build fix map: cite_id -> corrected clean text
    fixes = {}

    for item in findings['backslash_n']:
        fixed = item['clean'].replace('\\n', '\n')
        fixes[item['cite_id']] = fixed

    for item in findings['textjoin']:
        cid = item['cite_id']
        # {TEXTJOIN#X#Y} -> try simple removal or keep as-is
        # For now, remove the tag leaving just the text
        fixed = re.sub(r'\{TEXTJOIN[^}]*\}', '', item['clean'])
        if cid in fixes:
            fixes[cid] = re.sub(r'\{TEXTJOIN[^}]*\}', '', fixes[cid])
        else:
            fixes[cid] = fixed

    for item in findings['nickname']:
        cid = item['cite_id']
        fixed = item['clean'].replace('{NICKNAME}', '开拓者')
        if cid in fixes:
            fixes[cid] = fixes[cid].replace('{NICKNAME}', '开拓者')
        else:
            fixes[cid] = fixed

    # Apply fixes
    volumes = ['lore', 'books', 'characters', 'narrative', 'dialogue', 'artifacts', 'rogue']
    fixed_count = 0
    for vol in volumes:
        path = CORPUS / f'{vol}.jsonl'
        if not path.exists():
            continue
        lines = []
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    lines.append(line)
                    continue
                e = json.loads(line)
                cid = e['cite_id']
                if cid in fixes:
                    e['clean'] = fixes[cid]
                    fixed_count += 1
                lines.append(json.dumps(e, ensure_ascii=False) + '\n')

        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

    return fixed_count

def main():
    print("Scanning for residuals...")
    findings = scan_residuals()

    print(f"  \\n residues: {len(findings['backslash_n'])} entries")
    print(f"  TEXTJOIN residues: {len(findings['textjoin'])} entries")
    print(f"  NICKNAME residues: {len(findings['nickname'])} entries")

    # Show per-volume breakdown
    by_vol = defaultdict(lambda: defaultdict(int))
    for item in findings['backslash_n']:
        by_vol[item['volume']]['\\n'] += 1
    for item in findings['textjoin']:
        by_vol[item['volume']]['TEXTJOIN'] += 1
    for item in findings['nickname']:
        by_vol[item['volume']]['NICKNAME'] += 1
    print("\n  By volume:")
    for vol in sorted(by_vol):
        print(f"    {vol}: {dict(by_vol[vol])}")

    # Show all affected entries
    print(f"\n=== ALL \\n AFFECTED ENTRIES ({len(findings['backslash_n'])} entries) ===")
    for item in findings['backslash_n']:
        c = item['clean']
        # Count occurrences
        count = c.count('\\n')
        print(f"  [{item['cite_id']}] {item['source_table']}.{item['source_field']} ({count} occurrences)")
        print(f"    First 200 chars: {c[:200]}")

    print(f"\n=== ALL TEXTJOIN AFFECTED ENTRIES ({len(findings['textjoin'])} entries) ===")
    for item in findings['textjoin']:
        matches = re.findall(r'\{TEXTJOIN[^}]*\}', item['clean'])
        print(f"  [{item['cite_id']}] {item['source_table']}.{item['source_field']}")
        print(f"    Matches: {matches}")
        print(f"    Text: {item['clean'][:200]}")

    print(f"\n=== ALL NICKNAME AFFECTED ENTRIES ({len(findings['nickname'])} entries) ===")
    for item in findings['nickname']:
        print(f"  [{item['cite_id']}] {item['source_table']}.{item['source_field']}")
        print(f"    Text: {item['clean'][:200]}")

    # Fix
    print(f"\nApplying fixes...")
    fixed = fix_residuals(findings)
    print(f"Fixed {fixed} entries across all corpus files")

    # Re-scan to verify
    print("\nRe-scanning to verify...")
    findings2 = scan_residuals()
    remaining = len(findings2['backslash_n']) + len(findings2['textjoin']) + len(findings2['nickname'])
    print(f"  Remaining: {remaining} ({len(findings2['backslash_n'])} \\n, {len(findings2['textjoin'])} TEXTJOIN, {len(findings2['nickname'])} NICKNAME)")

    if remaining > 0:
        print("\n  WARNING: Some residues could not be fixed:")
        for item in findings2['backslash_n']:
            print(f"    \\n: [{item['cite_id']}] {item['clean'][:150]}")
        for item in findings2['textjoin']:
            print(f"    TEXTJOIN: [{item['cite_id']}] {item['clean'][:150]}")
        for item in findings2['nickname']:
            print(f"    NICKNAME: [{item['cite_id']}] {item['clean'][:150]}")

    # Save report
    report = {
        'before': {
            'backslash_n_count': len(findings['backslash_n']),
            'textjoin_count': len(findings['textjoin']),
            'nickname_count': len(findings['nickname']),
            'all_backslash_n': [{'cite_id': x['cite_id'], 'volume': x['volume'], 'source_table': x['source_table'], 'source_field': x['source_field']} for x in findings['backslash_n']],
            'all_textjoin': [{'cite_id': x['cite_id'], 'volume': x['volume'], 'matches': re.findall(r'\{TEXTJOIN[^}]*\}', x['clean'])} for x in findings['textjoin']],
            'all_nickname': [{'cite_id': x['cite_id'], 'volume': x['volume']} for x in findings['nickname']],
        },
        'after': {
            'remaining_total': remaining,
        },
    }
    outpath = BASE / 'work' / 'cleaning_fix_report.json'
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nReport: {outpath}")

if __name__ == '__main__':
    main()
