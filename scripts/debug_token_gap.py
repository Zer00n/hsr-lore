"""Quick debug: compare build_real_prompt token estimate vs build_prompts output."""
import json, yaml, sys
from pathlib import Path

BASE = Path('D:/Office/claudecode/star/hsr-lore')

with open(BASE / 'config' / 'task_chunks.json', 'r', encoding='utf-8') as f:
    chunk_plan = json.load(f)
with open(BASE / 'tasks' / 'T1_entity_relation.yaml', 'r', encoding='utf-8') as f:
    task_card = yaml.safe_load(f)

cite_index = {}
with open(BASE / 'work' / 'cite_index.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            rec = json.loads(line)
            cite_index[rec['cite_id']] = rec
print(f'Loaded {len(cite_index):,} cite_index entries')

for chunk_idx in [0, 1, 13, 24]:  # C001, C002, C014, C025
    chunk = chunk_plan['chunks'][chunk_idx]
    cid = chunk['chunk_id']

    corpus_parts = []
    found = 0
    for c in chunk['cite_ids']:
        rec = cite_index.get(c)
        if rec:
            corpus_parts.append(f"[{rec['cite_id']}]\n{rec['clean']}\n")
            found += 1
    corpus_text = '\n'.join(corpus_parts)

    system_prompt = task_card.get('system_prompt', '')
    user_template = task_card.get('user_prompt_template', '')
    user_prompt = user_template.replace('{volume_name}', chunk.get('volume', ''))
    user_prompt = user_prompt.replace('{entry_count}', str(len(chunk.get('cite_ids', []))))
    user_prompt = user_prompt.replace('{scope_description}', chunk.get('description', ''))
    user_prompt = user_prompt.replace('{corpus_entries}', corpus_text)

    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_prompt},
    ]

    input_str = json.dumps(messages, ensure_ascii=False, sort_keys=True)
    mock_token = len(input_str) // 3
    full_chars = len(system_prompt) + len(user_prompt)

    # Compare with build_prompts file
    prompt_path = BASE / 'work' / 'prompts' / f'{cid}.txt'
    prompt_size = prompt_path.stat().st_size if prompt_path.exists() else 0

    print(f'{cid}: found={found}/{chunk["entry_count"]} cite_ids, '
          f'full_chars={full_chars:,}, json_size={len(input_str):,}, '
          f'mock_token={mock_token:,}, prompt_file={prompt_size:,}')

    if prompt_size > 0:
        # Check if file content matches our messages
        with open(prompt_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        file_chars = len(file_content)
        our_concat = system_prompt + '\n\n' + user_prompt
        print(f'  File chars={file_chars:,}, our_concat={len(our_concat):,}, '
              f'diff={file_chars - len(our_concat)}')
