"""
OpenViking 覆盖率验证脚本
读 ov_plan.json，对每个 URI 做可检索性验证。
--dry-run: 输出预期清单
--check: 对已灌库的文件做检索验证（需库中有文件）
输出 work/ov_coverage.json
"""
import json, sys, io, os, subprocess, time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(__file__).parent.parent.parent
WORK = BASE / 'work'
NAMESPACE = 'viking://resources/hsr'

def load_plan():
    with open(WORK / 'ov_plan.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def get_expected_uris(plan):
    """Extract all expected file URIs from the plan."""
    uris = []
    for dir_path, info in sorted(plan['directories'].items()):
        for f_entry in info['files']:
            uri = f"{NAMESPACE}/{f_entry['path']}"
            uris.append({
                'uri': uri,
                'dir': dir_path,
                'size_bytes': f_entry['size_bytes'],
                'entry_count': f_entry.get('entry_count', 1),
            })
    return uris

def check_file_exists(uri):
    """Check if an OpenViking file exists and is readable via ov read."""
    try:
        result = subprocess.run(
            ['ov', 'read', uri],
            capture_output=True, text=True, timeout=15,
            encoding='utf-8', errors='replace'
        )
        return result.returncode == 0
    except:
        return False

def check_file_findable(uri):
    """Check if a file can be found via ov find using a snippet from its content."""
    try:
        # Read the file first to get text for search
        result = subprocess.run(
            ['ov', 'read', uri],
            capture_output=True, text=True, timeout=15,
            encoding='utf-8', errors='replace'
        )
        if result.returncode != 0:
            return False

        # Extract a distinctive search term (first 30 chars of body after frontmatter)
        content = result.stdout
        # Skip YAML frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                content = parts[2]
        search_term = content.strip()[:40]
        if not search_term:
            return False

        # Search for it
        find_result = subprocess.run(
            ['ov', 'find', search_term, '-u', NAMESPACE, '-n', '10', '-o', 'json'],
            capture_output=True, text=True, timeout=15,
            encoding='utf-8', errors='replace'
        )
        if find_result.returncode != 0:
            return False

        data = json.loads(find_result.stdout)
        resources = data.get('result', {}).get('resources', [])
        return any(uri in r.get('uri', '') for r in resources)
    except:
        return False

def main():
    import argparse
    parser = argparse.ArgumentParser(description='OpenViking Coverage Check')
    parser.add_argument('--dry-run', action='store_true', help='Output expected URI list')
    parser.add_argument('--check', action='store_true', help='Actually check against live OpenViking')
    parser.add_argument('--repush', action='store_true', help='Re-push missing files')
    parser.add_argument('--sample', type=int, default=0, help='Check only N sample URIs')
    args = parser.parse_args()

    plan = load_plan()
    expected = get_expected_uris(plan)

    print(f"Expected URIs: {len(expected)}")
    print(f"Expected bytes: {plan['total_bytes']:,}")

    if args.dry_run:
        print(f"\nURI list (first 20):")
        for u in expected[:20]:
            print(f"  {u['uri']}")

    coverage_report = {
        'total_expected': len(expected),
        'total_bytes_expected': plan['total_bytes'],
        'missing': [],
        'found': 0,
        'checked': 0,
    }

    if args.check:
        to_check = expected
        if args.sample > 0:
            import random
            random.seed(20260807)
            to_check = random.sample(expected, min(args.sample, len(expected)))

        print(f"\nChecking {len(to_check)} URIs...")
        for i, u in enumerate(to_check):
            if i % 10 == 0:
                print(f"  [{i}/{len(to_check)}] checking...")
            exists = check_file_exists(u['uri'])
            findable = check_file_findable(u['uri']) if exists else False
            coverage_report['checked'] += 1
            if exists and findable:
                coverage_report['found'] += 1
            else:
                issue = {
                    'uri': u['uri'],
                    'exists': exists,
                    'findable': findable,
                    'dir': u['dir'],
                    'size_bytes': u['size_bytes'],
                }
                coverage_report['missing'].append(issue)
                print(f"  MISSING: {u['uri']} (exists={exists}, findable={findable})")

        coverage_report['coverage_rate'] = coverage_report['found'] / coverage_report['checked'] if coverage_report['checked'] else 0
        print(f"\nCoverage: {coverage_report['found']}/{coverage_report['checked']} ({coverage_report['coverage_rate']*100:.1f}%)")
        print(f"Missing: {len(coverage_report['missing'])}")

    outpath = WORK / 'ov_coverage.json'
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(coverage_report, f, ensure_ascii=False, indent=2)
    print(f"\nOutput: {outpath}")

if __name__ == '__main__':
    main()
