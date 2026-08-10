"""Re-run fuse test with fixed token estimation."""
import json, sys, yaml, time
from pathlib import Path
BASE = Path('D:/Office/claudecode/star/hsr-lore')
sys.path.insert(0, str(BASE / 'scripts' / 'llm'))
from client import LLMClient, TokenBudgetExceededError

with open(BASE/'config'/'task_chunks.json','r', encoding='utf-8') as f:
    chunks = json.load(f)['chunks']
with open(BASE/'tasks'/'T1_entity_relation.yaml','r', encoding='utf-8') as f:
    task_card = yaml.safe_load(f)
cite_idx = {}
with open(BASE/'work'/'cite_index.jsonl','r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            rec = json.loads(line)
            cite_idx[rec['cite_id']] = rec

def build_msgs(chunk):
    sp = task_card.get('system_prompt','')
    ut = task_card.get('user_prompt_template','')
    parts = []
    for c in chunk['cite_ids']:
        rec = cite_idx.get(c)
        if rec:
            parts.append(f"[{rec['cite_id']}]\n{rec['clean']}\n")
    corpus = ''.join(parts)
    up = ut.replace('{volume_name}',chunk.get('volume',''))
    up = up.replace('{entry_count}',str(len(chunk.get('cite_ids',[]))))
    up = up.replace('{scope_description}',chunk.get('description',''))
    up = up.replace('{corpus_entries}',corpus)
    return [{'role':'system','content':sp},{'role':'user','content':up}]

client = LLMClient(profile='mock', run_id='a2_fuse_fixed')
client.logger.max_input_tokens = 5_000_000
ran = 0
tripped = False
for chunk in chunks[:25]:
    cid = chunk['chunk_id']
    msgs = build_msgs(chunk)
    prompt_chars = sum(len(m.get('content','')) for m in msgs)
    try:
        resp = client.chat(messages=msgs, task_name=f'fuse/{cid}',
                          input_volume=chunk['volume'], mock_response='[ok]')
        client.logger.mark_chunk_completed(cid)
        ran += 1
        print(f'  [{cid}] {chunk["volume"]} prompt={prompt_chars:,}chars '
              f'input={resp["usage"]["prompt_tokens"]:,} cum_total={client.logger.total_input_tokens:,}')
    except TokenBudgetExceededError as e:
        tripped = True
        print(f'\n  FUSE TRIPPED at [{cid}]!')
        print(f'  Direction: {e.direction}')
        print(f'  Current: {e.current_total:,} / Limit: {e.limit:,}')
        chunks_list = client.logger.completed_chunks
        print(f'  Completed chunks: {chunks_list} ({len(chunks_list)} total)')
        break

print(f'\nRESULTS: {ran} chunks completed, fuse tripped={tripped}')
print(f'  Completed chunks: {client.logger.completed_chunks}')
print(f'  Total input: {client.logger.total_input_tokens:,}')

# Verify completed_chunks.txt
import os
txt_path = BASE / 'logs' / 'runs' / 'a2_fuse_fixed' / 'completed_chunks.txt'
if not txt_path.exists():
    # Try alternate location
    for d in (BASE / 'logs' / 'runs').iterdir():
        if d.name.startswith('a2_fuse'):
            txt_path = d / 'completed_chunks.txt'
            if txt_path.exists():
                break
print(f'  completed_chunks.txt: {txt_path}')
if txt_path.exists():
    with open(txt_path) as f:
        lines = [l.strip() for l in f if l.strip()]
    print(f'  File contents ({len(lines)} entries):')
    for l in lines[:5]:
        print(f'    {l}')
    if len(lines) > 5:
        print(f'    ... ({len(lines)-5} more)')
