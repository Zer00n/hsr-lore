"""
R2 v3-前置：TalkSentenceID 号段分布调查
统计 speakerless 65,450 条按 TalkSentenceID 前 3/4/5 位的分布，
取条数最多的 15 个号段，每个抽 10 条完整原文。
输出 work/talksentence_prefix_survey.json
"""
import json, sys, io, os, re
from collections import Counter

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

    print(f"Total entries: {len(entries)}")

    # Extract TalkSentenceID prefix at various lengths
    for prefix_len in [3, 4, 5]:
        prefix_counter = Counter()
        for e in entries:
            pk = str(e.get('source_pk', ''))
            prefix = pk[:prefix_len] if len(pk) >= prefix_len else pk
            prefix_counter[prefix] += 1

        top15 = prefix_counter.most_common(15)

        print(f"\n{'='*70}")
        print(f"Prefix length {prefix_len}: {len(prefix_counter)} unique prefixes")
        print(f"{'='*70}")
        print(f"{'Prefix':>8s} {'Count':>8s} {'Pct':>8s}")
        print('-' * 30)
        for prefix, count in top15:
            pct = count / len(entries) * 100
            print(f"{prefix:>8s} {count:>8d} {pct:>7.1f}%")

        # Sample 10 from each top 15
        prefix_samples = {}
        for prefix, _ in top15:
            prefix_entries = [e for e in entries if str(e['source_pk'])[:prefix_len] == prefix]
            samples = []
            for e in prefix_entries[:10]:
                samples.append({
                    'cite_id': e['cite_id'],
                    'source_pk': e['source_pk'],
                    'clean_text': e.get('clean', ''),
                })
            prefix_samples[prefix] = {
                'count': len(prefix_entries),
                'samples': samples,
            }

        # Print samples
        print(f"\n{'─'*70}")
        print("SAMPLES (10 per top prefix)")
        print(f"{'─'*70}")
        for prefix, _ in top15:
            info = prefix_samples[prefix]
            print(f"\n--- Prefix {prefix} ({info['count']} entries) ---")
            for s in info['samples']:
                print(f"  [{s['cite_id']}] {s['clean_text'][:150]}")

    # Save report
    report = {'total_entries': len(entries)}
    for prefix_len in [3, 4, 5]:
        prefix_counter = Counter()
        for e in entries:
            pk = str(e.get('source_pk', ''))
            prefix = pk[:prefix_len] if len(pk) >= prefix_len else pk
            prefix_counter[prefix] += 1
        top15 = prefix_counter.most_common(15)
        report[f'prefix_{prefix_len}'] = {
            'unique_prefixes': len(prefix_counter),
            'top_15': [{'prefix': p, 'count': c, 'pct': round(c/len(entries)*100, 1)} for p, c in top15],
        }
        # Add full samples to the 5-digit level (most granular)
        if prefix_len == 5:
            prefix_samples = {}
            for prefix, _ in top15:
                prefix_entries = [e for e in entries if str(e['source_pk'])[:5] == prefix]
                samples = []
                for e in prefix_entries[:10]:
                    samples.append({
                        'cite_id': e['cite_id'],
                        'source_pk': e['source_pk'],
                        'clean_text': e.get('clean', ''),
                    })
                prefix_samples[prefix] = {'count': len(prefix_entries), 'samples': samples}
            report['samples_prefix_5'] = prefix_samples

    outpath = os.path.join(WORK, 'talksentence_prefix_survey.json')
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nOutput: {outpath}")

if __name__ == '__main__':
    main()
