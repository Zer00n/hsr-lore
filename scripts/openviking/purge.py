"""
OpenViking 清空脚本 v2
清空 viking://resources/hsr/ 下全部内容，需 --yes 二次确认。
v2: 通过 ov rm --recursive CLI 执行真实删除。
"""
import os, sys, io, subprocess

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

NAMESPACE = 'viking://resources/hsr'

def purge(confirm=False):
    if not confirm:
        print(f"WARNING: This will DELETE ALL content under {NAMESPACE}")
        print(f"Run with --yes to confirm.")
        sys.exit(0)

    print(f"Purging {NAMESPACE}...")

    # Step 1: List all top-level entries
    try:
        result = subprocess.run(
            ['ov', 'ls', NAMESPACE, '-o', 'json', '-c', 'true', '-l', '256', '-n', '256'],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            print(f"ERROR listing: {result.stderr}")
            sys.exit(1)

        listing = result.stdout.strip()
        if not listing or listing == '(empty)':
            print("Already empty. Nothing to purge.")
            return

        # Parse JSON listing
        import json
        items = json.loads(listing)
        if not isinstance(items, list):
            items = [items]

        for item in items:
            uri = item.get('uri', '') if isinstance(item, dict) else str(item)
            if not uri:
                continue
            print(f"  Removing: {uri}")
            subprocess.run(
                ['ov', 'rm', uri, '--recursive'],
                capture_output=True, text=True, timeout=60
            )

    except subprocess.TimeoutExpired:
        print("ERROR: Timeout — try again or use web console")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Step 2: Verify
    result = subprocess.run(
        ['ov', 'ls', NAMESPACE, '-l', '256', '-n', '256'],
        capture_output=True, text=True, timeout=30
    )
    remaining = result.stdout.strip()

    if remaining == '(empty)':
        print(f"\nPURGE CONFIRMED: {NAMESPACE} is empty.")
    else:
        print(f"\nWARNING: Items remain after purge:\n{remaining}")
        print("You may need to purge from the web console.")
        sys.exit(1)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='OpenViking Purge')
    parser.add_argument('--yes', action='store_true', help='Confirm deletion')
    args = parser.parse_args()
    purge(confirm=args.yes)
