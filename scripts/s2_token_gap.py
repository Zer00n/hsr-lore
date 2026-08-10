"""
S2: Token gap investigation
Compare build_prompts.py output (work/prompts/{cid}.txt chars) vs
calls.jsonl input_token from real mock runs.
"""
import json, sys, io, os
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(__file__).parent.parent
PROMPTS = BASE / 'work' / 'prompts'

sys.path.insert(0, str(BASE / 'scripts'))
from token_utils import TOKEN_COEFFICIENT

# Load calls.jsonl
calls = {}
calls_path = BASE / 'logs' / 'runs' / 'mock_conc4' / 'calls.jsonl'
if not calls_path.exists():
    # Try other locations
    for d in (BASE / 'logs' / 'runs').iterdir():
        cp = d / 'calls.jsonl'
        if cp.exists():
            calls_path = cp
            break

if calls_path.exists():
    with open(calls_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                c = json.loads(line)
                cid = c.get('task_name', '').split('/')[-1] if '/' in c.get('task_name', '') else ''
                if cid and cid.startswith('C'):
                    if cid not in calls or 'T1' in c.get('task_name', ''):
                        calls[cid] = c
    print(f"Loaded {len(calls)} records from {calls_path.name}")

# Load chunk plan for entry counts
with open(BASE / 'config' / 'task_chunks.json', 'r', encoding='utf-8') as f:
    chunks = {c['chunk_id']: c for c in json.load(f)['chunks']}
print(f"Chunk plan: {len(chunks)} chunks")

print()
print(f"{'Chunk':>6s} {'Volume':>15s} {'Plan Entries':>12s} {'Prompt Chars':>12s} "
      f"{'Calls Input':>12s} {'Est@.{:.2f}'.format(TOKEN_COEFFICIENT):>12s} {'Dev%':>7s}")
print("-" * 85)

total_plan_entries = 0
total_actual_entries = 0
total_prompt_chars = 0
total_calls_tokens = 0
issues = []

for cid in sorted(calls.keys(), key=lambda x: (x[0], int(x[1:]))):
    call = calls.get(cid)
    chunk = chunks.get(cid)
    if not chunk:
        continue

    plan_entries = chunk['entry_count']
    prompt_path = PROMPTS / f'{cid}.txt'
    prompt_chars = 0
    if prompt_path.exists():
        prompt_chars = prompt_path.stat().st_size

    # Count actual cite_id lines in prompt to estimate entry count
    actual_entries = 0
    if prompt_path.exists():
        with open(prompt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # Count [CITE_ID] patterns
        import re
        actual_entries = len(set(re.findall(r'\[([A-Z0-9-]+)\]', content)))

    calls_input = call.get('input_token', 0)
    estimated = int(prompt_chars * TOKEN_COEFFICIENT)
    dev_pct = (calls_input - estimated) / estimated * 100 if estimated else 0

    total_plan_entries += plan_entries
    total_actual_entries += actual_entries
    total_prompt_chars += prompt_chars
    total_calls_tokens += calls_input

    flag = ''
    if abs(dev_pct) > 20:
        flag = ' ⚠'
        issues.append((cid, prompt_chars, calls_input, estimated, dev_pct))

    print(f"{cid:>6s} {chunk['volume']:>15s} {plan_entries:>12,d} {prompt_chars:>12,d} "
          f"{calls_input:>12,d} {estimated:>12,d} {dev_pct:>+6.1f}%{flag}")

print("-" * 85)
print(f"{'TOTAL':>6s} {'':>15s} {total_plan_entries:>12,d} {total_prompt_chars:>12,d} "
      f"{total_calls_tokens:>12,d} {int(total_prompt_chars * TOKEN_COEFFICIENT):>12,d} "
      f"{(total_calls_tokens - int(total_prompt_chars * TOKEN_COEFFICIENT)) / max(int(total_prompt_chars * TOKEN_COEFFICIENT), 1) * 100:>+6.1f}%")

# Check for truncation
print(f"\n{'='*60}")
print("TRUNCATION CHECK")
print(f"{'='*60}")
for cid, prompt_chars, calls_input, estimated, dev_pct in issues:
    print(f"  {cid}: prompt={prompt_chars:,} chars, calls={calls_input:,} tokens, "
          f"est={estimated:,}, dev={dev_pct:+.1f}%")
    chunk = chunks.get(cid)
    if chunk:
        print(f"    volume={chunk['volume']}, plan entries={chunk['entry_count']:,}")

if not issues:
    print("  No blocks with deviation > 20%")

# Also check build_prompts.py total vs calls total
print(f"\n{'='*60}")
print("BUILD_PROMPTS VS CALLS TOTALS")
print(f"{'='*60}")

with open(BASE / 'work' / 'prompt_assembly_report.json', 'r', encoding='utf-8') as f:
    report = json.load(f)

bp_total_tokens = report['summary']['total_tokens']
print(f"  build_prompts report: {bp_total_tokens:,} estimated tokens ({report['summary']['total_chars']:,} chars)")
print(f"  calls.jsonl total:   {total_calls_tokens:,} tokens")
diff = bp_total_tokens - total_calls_tokens
print(f"  Difference:          {diff:,} ({diff/bp_total_tokens*100:+.1f}%)")
print(f"  Note: build_prompts uses full prompt (sys+user), calls has mock_response mode")
print(f"  where input_token = len(messages_as_json) // 3 (raw estimate)")
