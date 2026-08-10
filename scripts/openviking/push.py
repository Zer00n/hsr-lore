"""
OpenViking 推送脚本 v3
按 plan 生成文件并上传，支持 --only 限定卷、--dry-run
v3 修正: 使用 --parent 而非 --to 避免 URI 包裹问题 (xxx.md/xxx.md)
"""
import json, os, sys, io, time, hashlib, subprocess
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(__file__).parent.parent.parent
WORK = BASE / 'work'
LOGS = BASE / 'logs' / 'ov'
ENDPOINT = "https://api.vikingdb.cn-beijing.volces.com/openviking"
LIBRARY_ID = "ov-290dce6904ec3189"
NAMESPACE = "viking://resources/hsr"

def ov_cli(*args):
    """Run ov CLI command."""
    cmd = ['ov'] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"ov CLI error: {result.stderr}")
    return result.stdout

def push_files(plan, only_volume=None):
    """
    Push files to OpenViking using ov add-resource --parent.
    --parent avoids the URI wrapping issue (xxx.md/xxx.md).
    """
    manifest = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'files_pushed': 0,
        'files_failed': 0,
        'files_skipped': 0,
        'total_bytes': 0,
        'start_time': datetime.now(timezone.utc).isoformat(),
        'errors': [],
        'volumes': {},
    }

    total_files = 0
    for dir_path, info in sorted(plan['directories'].items()):
        vol = dir_path.split('/')[0]
        if only_volume and vol != only_volume:
            continue

        vol_stats = manifest['volumes'].setdefault(vol, {'pushed': 0, 'failed': 0, 'skipped': 0})
        # Ensure parent directory exists
        parent_uri = f"{NAMESPACE}/{dir_path}"
        print(f"\n[{vol}] {dir_path} ({info['file_count']} files)")

        for f_entry in info['files']:
            fpath = f_entry['path']
            total_files += 1
            try:
                # Generate actual file content from plan
                content = _build_file_content(plan, dir_path, f_entry)
                if not content:
                    manifest['files_skipped'] += 1
                    vol_stats['skipped'] += 1
                    continue

                # Write to temp file, then upload via ov add-resource --parent
                tmp_path = BASE / 'work' / '.ov_tmp' / fpath
                os.makedirs(tmp_path.parent, exist_ok=True)
                with open(tmp_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                # Use --parent to avoid URI wrapping
                ov_cli('add-resource', '--parent', parent_uri, str(tmp_path))

                manifest['files_pushed'] += 1
                manifest['total_bytes'] += f_entry['size_bytes']
                vol_stats['pushed'] += 1

                if total_files % 50 == 0:
                    print(f"  [{total_files}] files processed...")

                # Clean up temp file
                os.remove(tmp_path)
            except Exception as e:
                manifest['files_failed'] += 1
                vol_stats['failed'] += 1
                manifest['errors'].append({
                    'path': fpath,
                    'error': str(e),
                })
                print(f"  ERROR [{fpath}]: {e}")

    manifest['end_time'] = datetime.now(timezone.utc).isoformat()
    duration = (datetime.fromisoformat(manifest['end_time']) -
                datetime.fromisoformat(manifest['start_time'])).total_seconds()
    manifest['duration_sec'] = duration

    # Save manifest
    os.makedirs(LOGS, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    manifest_path = LOGS / f'{ts}_manifest.json'
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # Clean up temp dir
    tmp_root = BASE / 'work' / '.ov_tmp'
    if tmp_root.exists():
        import shutil
        shutil.rmtree(tmp_root, ignore_errors=True)

    return manifest


def _build_file_content(plan, dir_path, f_entry):
    """
    Build file content from plan entry.
    The plan stores file metadata but not content — we need to regenerate
    content from the corpus. For now, extract content from plan metadata.
    """
    # Content is embedded in plan v3 — stored as base64 or inline
    # For the initial push, we rely on ov CLI to read files from disk
    # Content generation is done at write time in plan.py
    return None  # Placeholder — actual content is in temp files from plan

def load_plan():
    with open(WORK / 'ov_plan.json', 'r', encoding='utf-8') as f:
        return json.load(f)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--only', help='Only push this volume')
    parser.add_argument('--dry-run', action='store_true', help='Dry run')
    parser.add_argument('--live', action='store_true', help='Actually push')
    args = parser.parse_args()

    plan = load_plan()

    if not args.live:
        print("DRY RUN — use --live to actually push")
        if args.only:
            vol = args.only
            count = sum(1 for d in plan['directories'] if d.startswith(vol))
            print(f"Would push {count} dirs from volume '{vol}'")
        else:
            print(f"Would push {plan['total_files']} files")
            print(f"Total bytes: {plan['total_bytes']:,}")
            print(f"Max file: {plan['max_file_bytes']:,} bytes")
            print(f"Avg file: {plan['avg_file_bytes']:,} bytes")
        sys.exit(0)

    print("LIVE PUSH to OpenViking")
    print(f"Endpoint: {ENDPOINT}")
    print(f"Library: {LIBRARY_ID}")
    print(f"Namespace: {NAMESPACE}")
    print(f"Total files: {plan['total_files']}")
    confirm = input("Type 'yes' to confirm: ")
    if confirm != 'yes':
        print("Aborted.")
        sys.exit(0)

    manifest = push_files(plan, only_volume=args.only)
    print(f"\nPUSH COMPLETE")
    print(f"Files: {manifest['files_pushed']} pushed, "
          f"{manifest['files_failed']} failed, "
          f"{manifest['files_skipped']} skipped")
    print(f"Duration: {manifest.get('duration_sec', 0):.1f}s")
    print(f"Manifest: logs/ov/")
