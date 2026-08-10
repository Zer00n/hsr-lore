"""
ExcelOutput 字段普查脚本
遍历所有 JSON 文件，提取字段名、Hash 引用、中文样例，输出结构化报告
"""
import json
import os
import glob
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = r'D:\Office\claudecode\star\hsr-lore\vendor\StarRailData'
EXCEL = os.path.join(BASE, 'ExcelOutput')
TEXTMAP_PATH = os.path.join(BASE, 'TextMap', 'TextMapCHS.json')

# Load TextMap
print("Loading TextMapCHS...")
with open(TEXTMAP_PATH, 'r', encoding='utf-8') as f:
    textmap = json.load(f)
print(f"  {len(textmap)} entries loaded")

# Get all JSON files
files = sorted(glob.glob(os.path.join(EXCEL, '*.json')))
print(f"  {len(files)} JSON files found\n")

# Classify keywords for A/B/C categorization
A_KEYWORDS = [
    'book', 'story', 'dialog', 'sentence', 'talk', 'mission', 'quest',
    'avatar', 'voice', 'npc', 'monster', 'item', 'relic', 'plane',
    'achievement', 'tutorial', 'loading', 'message', 'mail', 'phone',
    'rogue', 'dice', 'chronicle', 'archive', 'readable', 'note',
    'introduction', 'description', 'strategy', 'biography',
]

B_KEYWORDS = [
    'skill', 'buff', 'maze', 'battle', 'stage', 'level', 'dungeon',
    'music', 'bgm', 'cutscene', 'cinematic', 'emotion', 'expression',
    'gacha', 'shop', 'banner', 'activity', 'event', 'camp', 'faction',
    'raid', 'challenge', 'task', 'reward', 'formula', 'raid',
]

# Files to skip (too large for value type, already known)
SKIP_ANALYSIS = set()

results = []
total_hash_fields = 0
total_records = 0

for i, fpath in enumerate(files):
    fname = os.path.basename(fpath)
    fsize = os.path.getsize(fpath)

    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[{i+1}/{len(files)}] {fname}: ERROR {e}")
        continue

    if not isinstance(data, list) or len(data) == 0:
        print(f"[{i+1}/{len(files)}] {fname}: SKIP (not list or empty)")
        continue

    # Filter out None entries
    data = [d for d in data if d is not None and isinstance(d, dict)]
    if len(data) == 0:
        print(f"[{i+1}/{len(files)}] {fname}: SKIP (all null)")
        continue

    n_records = len(data)
    total_records += n_records

    # Extract top-level fields
    first = data[0]
    fields = []
    hash_fields = []

    for key, val in first.items():
        val_type = type(val).__name__
        is_hash = False
        hash_samples = []

        if isinstance(val, dict) and 'Hash' in val:
            is_hash = True
            # Resolve 3 samples from the data
            seen = set()
            for record in data:
                if key in record:
                    rv = record[key]
                    if isinstance(rv, dict) and 'Hash' in rv:
                        h = str(rv['Hash'])
                        if h in textmap and h not in seen:
                            text = textmap[h]
                            if len(text) > 0 and text != 'N/A':
                                hash_samples.append(text)
                                seen.add(h)
                            if len(hash_samples) >= 3:
                                break

        if is_hash:
            hash_fields.append({
                'field': key,
                'samples': hash_samples,
                'sample_count': len(hash_samples),
            })
            total_hash_fields += 1

        fields.append({
            'name': key,
            'type': val_type,
            'is_hash': is_hash,
            'nested_keys': list(val.keys()) if isinstance(val, dict) and 'Hash' not in val else None,
            'is_list': isinstance(val, list),
        })

    # Classify
    fname_lower = fname.lower()
    a_score = sum(1 for kw in A_KEYWORDS if kw in fname_lower)
    b_score = sum(1 for kw in B_KEYWORDS if kw in fname_lower)

    if a_score > 0:
        category = 'A'
    elif b_score > 0:
        category = 'B'
    else:
        category = 'C'

    # Check if any hash fields have "story" or "description" in name
    story_hash_fields = [h for h in hash_fields if any(
        kw in h['field'].lower()
        for kw in ['desc', 'story', 'text', 'name', 'title', 'intro', 'strategy', 'content']
    )]
    if story_hash_fields and category == 'C':
        category = 'B'

    results.append({
        'file': fname,
        'size_mb': fsize / (1024 * 1024),
        'records': n_records,
        'fields': fields,
        'hash_fields': hash_fields,
        'category': category,
        'a_score': a_score,
        'b_score': b_score,
    })

    if (i + 1) % 200 == 0:
        print(f"  [{i+1}/{len(files)}] processed...")

print(f"\n=== SURVEY COMPLETE ===")
print(f"Total files: {len(results)}")
print(f"Total records: {total_records}")
print(f"Total hash fields: {total_hash_fields}")

# Output summary by category
a_count = sum(1 for r in results if r['category'] == 'A')
b_count = sum(1 for r in results if r['category'] == 'B')
c_count = sum(1 for r in results if r['category'] == 'C')
print(f"\nCategory distribution:")
print(f"  A (worldview): {a_count}")
print(f"  B (suspicious): {b_count}")
print(f"  C (irrelevant): {c_count}")

# Save detailed results
output_path = r'D:\Office\claudecode\star\hsr-lore\work\excel_survey.json'
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\nDetailed results saved to: {output_path}")

# Print A and B class files with hash fields
print(f"\n=== A/B CLASS FILES WITH HASH FIELDS ===")
for r in results:
    if r['category'] in ('A', 'B') and r['hash_fields']:
        print(f"\n--- {r['file']} [{r['category']}] ({r['records']} records, {r['size_mb']:.1f} MB) ---")
        for hf in r['hash_fields']:
            print(f"  Field: {hf['field']}")
            for j, sample in enumerate(hf['samples']):
                print(f"    Sample {j+1}: {sample}")