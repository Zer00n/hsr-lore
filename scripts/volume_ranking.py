"""
全字段文本体量排序脚本
遍历 ExcelOutput 下全部含 Hash 字段的文件，对每个 (文件, 字段) 二元组：
- 解析所有 Hash 为中文
- 统计非空条数、总字符数、平均/中位字符数、最长样例
- 按总字符数降序排列
"""
import json, os, glob, sys, io, statistics

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = r'D:\Office\claudecode\star\hsr-lore\vendor\StarRailData'
EXCEL = os.path.join(BASE, 'ExcelOutput')
TEXTMAP_PATH = os.path.join(BASE, 'TextMap', 'TextMapCHS.json')

print("Loading TextMapCHS...")
with open(TEXTMAP_PATH, 'r', encoding='utf-8') as f:
    textmap = json.load(f)
print(f"  {len(textmap)} entries loaded\n")

def is_hash_ref(val):
    return isinstance(val, dict) and 'Hash' in val and len(val) == 1

def resolve_hash(val):
    """Resolve a Hash reference to Chinese text"""
    h = str(val['Hash'])
    text = textmap.get(h, '')
    if text and text != 'N/A':
        return text
    return None

def collect_field_texts(data, field_path):
    """Collect all resolved texts for a field path (e.g. 'field' or 'parent.child')"""
    parts = field_path.split('.')
    texts = []
    for record in data:
        if record is None or not isinstance(record, dict):
            continue
        # Navigate to the field
        val = record
        for part in parts:
            if isinstance(val, dict) and part in val:
                val = val[part]
            else:
                val = None
                break
        if val is not None and is_hash_ref(val):
            text = resolve_hash(val)
            if text:
                texts.append(text)
    return texts

def compute_stats(texts):
    """Compute statistics for a list of text strings"""
    if not texts:
        return {'count': 0, 'total_chars': 0, 'avg': 0, 'median': 0, 'longest': ''}
    lengths = [len(t) for t in texts]
    return {
        'count': len(texts),
        'total_chars': sum(lengths),
        'avg': round(sum(lengths) / len(lengths), 1),
        'median': statistics.median(lengths),
        'longest': max(texts, key=len)[:80] if texts else '',
    }

print("Scanning ExcelOutput files...")
results = []
file_count = 0

for fpath in sorted(glob.glob(os.path.join(EXCEL, '*.json'))):
    fname = os.path.basename(fpath)
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        continue

    if not isinstance(data, list) or len(data) == 0:
        continue
    data = [d for d in data if d is not None and isinstance(d, dict)]
    if len(data) == 0:
        continue

    first = data[0]

    # Check top-level hash fields
    for key, val in first.items():
        if is_hash_ref(val):
            texts = collect_field_texts(data, key)
            if texts:
                stats = compute_stats(texts)
                results.append({
                    'file': fname,
                    'field': key,
                    **stats,
                })

        elif isinstance(val, dict) and 'Hash' not in val:
            # Check nested hash fields
            for nk, nv in val.items():
                if is_hash_ref(nv):
                    field_path = f'{key}.{nk}'
                    texts = collect_field_texts(data, field_path)
                    if texts:
                        stats = compute_stats(texts)
                        results.append({
                            'file': fname,
                            'field': field_path,
                            **stats,
                        })

    file_count += 1
    if file_count % 50 == 0:
        print(f"  [{file_count}] files scanned, {len(results)} field pairs found...")

# Sort by total_chars descending
results.sort(key=lambda x: -x['total_chars'])

print(f"\n=== RESULTS ===")
print(f"Total (file, field) pairs: {len(results)}")
print(f"Total characters across all fields: {sum(r['total_chars'] for r in results):,}")

# Print top 80
print(f"\n{'='*120}")
print(f"{'Rank':<6} {'File':<45} {'Field':<30} {'Count':>8} {'TotalChars':>12} {'Avg':>7} {'Med':>6} {'Longest (first 80 chars)'}")
print(f"{'='*120}")

for i, r in enumerate(results[:80]):
    print(f"{i+1:<6} {r['file']:<45} {r['field']:<30} {r['count']:>8} {r['total_chars']:>12,} {r['avg']:>7.1f} {r['median']:>6.0f} {r['longest'][:80]}")

# Save full results
output_path = r'D:\Office\claudecode\star\hsr-lore\work\text_volume_full.json'
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\nFull results saved to: {output_path}")

# Also save just the top 80 as a readable text file
top80_path = r'D:\Office\claudecode\star\hsr-lore\work\text_volume_top80.txt'
with open(top80_path, 'w', encoding='utf-8') as f:
    f.write(f"{'Rank':<6} {'File':<45} {'Field':<30} {'Count':>8} {'TotalChars':>12} {'Avg':>7} {'Med':>6} {'Longest (first 80 chars)'}\n")
    f.write(f"{'='*120}\n")
    for i, r in enumerate(results[:80]):
        f.write(f"{i+1:<6} {r['file']:<45} {r['field']:<30} {r['count']:>8} {r['total_chars']:>12,} {r['avg']:>7.1f} {r['median']:>6.0f} {r['longest'][:80]}\n")
print(f"Top 80 saved to: {top80_path}")