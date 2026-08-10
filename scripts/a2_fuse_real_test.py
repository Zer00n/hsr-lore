"""
A2 v2: Fuse test with real prompt data at low budget.
Sets max_total_input_tokens = 2000000 (2M), runs real prompts through.
Expects fuse to trip around chunk 4 given ~128K avg per call.
"""
import json, sys, io, yaml, time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(__file__).parent.parent
WORK = BASE / 'work'
CONFIG = BASE / 'config'

sys.path.insert(0, str(BASE / 'scripts' / 'llm'))
from client import LLMClient, TokenBudgetExceededError

# Load chunk plan and task card
with open(CONFIG / 'task_chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)['chunks']
with open(BASE / 'tasks' / 'T1_entity_relation.yaml', 'r', encoding='utf-8') as f:
    task_card = yaml.safe_load(f)

# Load cite_index
cite_index = {}
with open(WORK / 'cite_index.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        if not line.strip():
            continue
        rec = json.loads(line)
        cite_index[rec['cite_id']] = rec

def build_chunk_input(chunk):
    lines = []
    for cid in chunk.get('cite_ids', []):
        rec = cite_index.get(cid)
        if rec:
            lines.append(f"[{rec['cite_id']}]\n{rec['clean']}\n")
    return '\n'.join(lines)

def build_messages(chunk):
    system_prompt = task_card.get('system_prompt', '')
    user_template = task_card.get('user_prompt_template', '')
    corpus_text = build_chunk_input(chunk)
    user_prompt = user_template.replace('{volume_name}', chunk.get('volume', ''))
    user_prompt = user_prompt.replace('{entry_count}', str(len(chunk.get('cite_ids', []))))
    user_prompt = user_prompt.replace('{scope_description}', chunk.get('description', ''))
    user_prompt = user_prompt.replace('{corpus_entries}', corpus_text)
    return [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_prompt},
    ]

# Create client with low input budget (2M tokens)
client = LLMClient(profile='mock', run_id='a2_fuse_real')
client.logger.max_input_tokens = 2_000_000  # 2M

print(f"Fuse limit: 2,000,000 input tokens")
print(f"Running chunks with real prompt data...")
print()

start = time.time()
ran = 0
fuse_tripped = False

for chunk in chunks[:20]:  # Only first 20 chunks
    cid = chunk['chunk_id']
    messages = build_messages(chunk)
    est_tokens = len(json.dumps(messages, ensure_ascii=False, sort_keys=True)) // 3

    try:
        print(f"  [{cid}] {chunk['volume']} ~{est_tokens:,} est tokens...", end=' ', flush=True)
        resp = client.chat(messages=messages, task_name=f"fuse_test/{cid}",
                          input_volume=chunk['volume'],
                          mock_response='[mock fuse test response]')
        client.logger.mark_chunk_completed(cid)  # track for fuse message
        input_tok = resp.get('usage', {}).get('prompt_tokens', 0)
        print(f"OK (actual input={input_tok:,}, cumulative={client.logger.total_input_tokens:,})")
        ran += 1
    except TokenBudgetExceededError as e:
        print(f"\n  FUSE TRIPPED at [{cid}]!")
        print(f"  Direction: {e.direction}")
        print(f"  Current: {e.current_total:,} / Limit: {e.limit:,}")
        print(f"  Message: {str(e)[:200]}...")
        fuse_tripped = True
        break
    except Exception as ex:
        print(f"ERROR: {type(ex).__name__}: {ex}")

elapsed = time.time() - start
print()
print("=" * 60)
print(f"RESULTS: {ran} chunks in {elapsed:.1f}s")
print(f"  Fuse tripped: {fuse_tripped}")
print(f"  Cumulative input: {client.logger.total_input_tokens:,}")
print(f"  Cumulative output: {client.logger.total_output_tokens:,}")
print(f"  Completed chunks: {client.logger.completed_chunks}")
