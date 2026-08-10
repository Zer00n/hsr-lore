"""
R2: 无说话人对话重新抽样
输出 work/r2_speakerless_sample_v2.jsonl
随机抽 200 条，每条完整原文。不做预先分类。
"""
import json, sys, io, os, random

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(BASE, 'work')
CORPUS = os.path.join(BASE, 'corpus')

def main():
    entries = []
    with open(os.path.join(CORPUS, 'speakerless.jsonl'), 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))

    random.seed(20260807)
    sample = random.sample(entries, min(200, len(entries)))

    outpath = os.path.join(WORK, 'r2_speakerless_sample_v2.jsonl')
    with open(outpath, 'w', encoding='utf-8') as f:
        for i, e in enumerate(sample):
            record = {
                'sample_index': i + 1,
                'cite_id': e['cite_id'],
                'title': e.get('title', ''),
                'clean_text': e.get('clean', ''),
                'raw_text': e.get('raw', ''),
            }
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

    # Also output a TSV for easy reading
    tsv_path = os.path.join(WORK, 'r2_speakerless_sample_v2.tsv')
    with open(tsv_path, 'w', encoding='utf-8') as f:
        f.write('index\tcite_id\ttitle\tclean_text\n')
        for i, e in enumerate(sample):
            clean = e.get('clean', '').replace('\t', ' ').replace('\n', '\\n')
            f.write(f'{i+1}\t{e["cite_id"]}\t{e.get("title","")}\t{clean}\n')

    print(f"R2 done: {len(sample)} entries sampled from {len(entries)} total")
    print(f"JSONL: {outpath}")
    print(f"TSV:   {tsv_path}")

if __name__ == '__main__':
    main()
