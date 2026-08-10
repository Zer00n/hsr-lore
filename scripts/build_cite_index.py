"""
引证索引构建器
从 corpus/*.jsonl 构建 cite_id → {clean, volume} 的快速查找索引
"""
import json, os, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

CORPUS = r'D:\Office\claudecode\star\hsr-lore\corpus'
WORK = r'D:\Office\claudecode\star\hsr-lore\work'

def build_index():
    cite_index = {}
    total = 0

    for vol in ['lore', 'books', 'characters', 'narrative', 'dialogue', 'artifacts', 'rogue']:
        path = os.path.join(CORPUS, f'{vol}.jsonl')
        if not os.path.exists(path):
            print(f'WARNING: {vol}.jsonl not found')
            continue
        vol_count = 0
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                e = json.loads(line)
                cid = e['cite_id']
                clean = e.get('clean', '')
                cite_index[cid] = {
                    'clean': clean,
                    'volume': vol,
                }
                vol_count += 1
                total += 1
        print(f'  {vol}: {vol_count} entries')

    # Write sorted JSONL
    jsonl_path = os.path.join(WORK, 'cite_index.jsonl')
    with open(jsonl_path, 'w', encoding='utf-8') as f:
        for cid in sorted(cite_index.keys()):
            rec = {'cite_id': cid, 'clean': cite_index[cid]['clean'], 'volume': cite_index[cid]['volume']}
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')

    # Write whitelist
    txt_path = os.path.join(WORK, 'cite_whitelist.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        for cid in sorted(cite_index.keys()):
            f.write(cid + '\n')

    print(f'\nTotal: {total} unique cite_ids')
    print(f'Index: {jsonl_path}')
    print(f'Whitelist: {txt_path}')
    return cite_index

if __name__ == '__main__':
    build_index()