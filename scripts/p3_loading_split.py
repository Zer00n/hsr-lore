"""
P3: lore/loading 按内容主题二次分组
每个文件控制在 30 条以内。
输出 work/p3_loading_groups.json
"""
import json, sys, io, os, re
from collections import defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(__file__).parent.parent
WORK = BASE / 'work'
CORPUS = BASE / 'corpus'

MAX_PER_FILE = 30

def main():
    entries = []
    with open(CORPUS / 'lore.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            e = json.loads(line)
            if e.get('source_table') == 'LoadingDesc':
                entries.append(e)

    print(f"Total LoadingDesc entries: {len(entries)}")

    # Strategy: group by first meaningful words in text as topic hints
    # Fall back to ID-range grouping if topic extraction fails
    groups = defaultdict(list)

    for e in entries:
        clean = e.get('clean', '')
        # Try to extract a topic keyword from the text
        # LoadingDesc texts often start with a location, character, or concept name
        first_sentence = clean.split('\n')[0].strip()[:60]
        # Extract proper nouns: consecutive Chinese chars or capitalized words
        topic = 'other'
        if first_sentence:
            # Try to match patterns like "XX的XX" or named entities
            match = re.match(r'^[^，。！？；：、\s]{2,8}', first_sentence)
            if match:
                topic = match.group()
            else:
                # Use first 4 chars as topic
                topic = first_sentence[:4]

        # Use topic as group key if it has enough entries, otherwise fall back
        groups[topic].append(e)

    # Merge small groups (< 3 entries) into "other"
    merged_groups = defaultdict(list)
    for topic, items in groups.items():
        if len(items) < 3:
            merged_groups['其他'].extend(items)
        else:
            merged_groups[topic].extend(items)

    # Split each group into files of MAX_PER_FILE entries
    file_plan = []
    for topic, items in sorted(merged_groups.items()):
        topic_slug = re.sub(r'[^\w一-鿿-]', '', topic)[:20] or 'topic'
        for chunk_idx in range(0, len(items), MAX_PER_FILE):
            chunk = items[chunk_idx:chunk_idx + MAX_PER_FILE]
            suffix = f'-{chunk_idx // MAX_PER_FILE:02d}' if len(items) > MAX_PER_FILE else ''
            filename = f'{topic_slug}{suffix}.md'
            file_plan.append({
                'path': f'lore/loading/{filename}',
                'entry_count': len(chunk),
                'total_chars': sum(len(e.get('clean', '')) for e in chunk),
                'sample_titles': [e.get('title', '')[:50] for e in chunk[:3]],
            })

    report = {
        'total_entries': len(entries),
        'max_per_file': MAX_PER_FILE,
        'total_files': len(file_plan),
        'files': file_plan,
        'group_sizes': {topic: len(items) for topic, items in sorted(merged_groups.items())},
    }

    outpath = WORK / 'p3_loading_groups.json'
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"P3 done: {len(entries)} entries → {len(file_plan)} files (max {MAX_PER_FILE}/file)")
    print(f"Groups: {report['group_sizes']}")
    for fp in file_plan:
        print(f"  {fp['path']}: {fp['entry_count']} entries, {fp['total_chars']} chars")
    print(f"Output: {outpath}")

if __name__ == '__main__':
    main()
