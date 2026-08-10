"""Gate trigger test — generate artificially high rejection rate for lore chunk"""
import json, sys, os, random, subprocess
from pathlib import Path

BASE = Path(__file__).parent.parent
WORK = BASE / 'work'
LOGS = BASE / 'logs'

# Load cite_index
cite_index = {}
with open(WORK / 'cite_index.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            rec = json.loads(line)
            cite_index[rec['cite_id']] = rec

# Load lore chunk cite_ids
with open(BASE / 'config' / 'task_chunks.json', 'r', encoding='utf-8') as f:
    chunk_plan = json.load(f)

lore_chunk = next(c for c in chunk_plan['chunks'] if c['volume'] == 'lore')
cite_ids = lore_chunk['cite_ids']

# Create bad data: 5 good + 2 bad = 2/7 = 28.6% rejection
real_cites = []
for cid in cite_ids[:3]:
    rec = cite_index.get(cid)
    if rec and rec.get('clean') and len(rec['clean']) > 10:
        txt = rec['clean']
        real_cites.append({'cite_id': cid, 'quote': txt[:40]})

good_objects = [
    {'type': 'CHAR', 'canonical_name': '纳努克', 'aliases': [],
     'summary': {'text': '毁灭星神','claim_type': 'fact','confidence': 'attested',
        'citations': [real_cites[0]]},
     'attributes': [], 'source_volume': 'lore'},
    {'type': 'PATH', 'canonical_name': '毁灭', 'aliases': [],
     'summary': {'text': '纳努克执掌的命途','claim_type': 'fact','confidence': 'attested',
        'citations': [real_cites[0]]},
     'attributes': [], 'source_volume': 'lore'},
    {'type': 'ORGN', 'canonical_name': '反物质军团', 'aliases': [],
     'summary': {'text': '纳努克麾下','claim_type': 'fact','confidence': 'attested',
        'citations': [real_cites[0]]},
     'attributes': [], 'source_volume': 'lore'},
    {'type': 'CONC', 'canonical_name': '绝灭大君', 'aliases': [],
     'summary': {'text': '纳努克的令使','claim_type': 'fact','confidence': 'attested',
        'citations': [real_cites[0]]},
     'attributes': [], 'source_volume': 'lore'},
    {'type': 'WRLD', 'canonical_name': '雅利洛-VI', 'aliases': [],
     'summary': {'text': '永恒冰冻的星球','claim_type': 'fact','confidence': 'attested',
        'citations': [real_cites[0]]},
     'attributes': [], 'source_volume': 'lore'},
]

# BAD: fake cite_id — will be rejected
bad1 = {'type': 'CHAR', 'canonical_name': '虚构角色',
 'summary': {'text': 'bad data','claim_type': 'fact','confidence': 'attested',
    'citations': [{'cite_id': 'FAKE-NOT-EXIST', 'quote': 'not real'}]},
 'attributes': [], 'source_volume': 'lore'}

# BAD: fact with no citations — will be rejected
bad2 = {'type': 'AEON', 'canonical_name': '另一个星神',
 'summary': {'text': 'bad','claim_type': 'fact','confidence': 'attested', 'citations': []},
 'attributes': [], 'source_volume': 'lore'}

all_objects = good_objects + [bad1, bad2]
output_text = '\n'.join(json.dumps(o, ensure_ascii=False) for o in all_objects)
expected_rejections = [
    {'violation': 'fake_cite_id', 'detail': 'cite_id=FAKE-NOT-EXIST'},
    {'violation': 'fact_no_citation', 'detail': 'fact with empty citations'},
]

# Create mock task run
run_id = 'mock_gate_test'
run_logs = LOGS / 'runs' / run_id
run_logs.mkdir(parents=True, exist_ok=True)

out_path = run_logs / 'T1_entity_relation_C001.jsonl'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(output_text)

# Backfill
backfilled = run_logs / 'T1_entity_relation_C001_backfilled.jsonl'
subprocess.run([str(BASE / '.venv' / 'Scripts' / 'python.exe'),
    str(BASE / 'scripts' / 'backfill_offsets.py'),
    str(out_path), '--output', str(backfilled)],
    cwd=str(BASE), check=True)

# Validate
result = subprocess.run([str(BASE / '.venv' / 'Scripts' / 'python.exe'),
    str(BASE / 'scripts' / 'validate.py'), str(backfilled)],
    capture_output=True, text=True, cwd=str(BASE),
    encoding='utf-8', errors='replace')

print("=" * 60)
print("GATE TRIGGER TEST")
print("=" * 60)
print(f"Input: 5 good + 2 bad = 7 objects, expected rejection: 2/7 = 28.6%")
print(f"\nValidation stdout:")
print(result.stdout)

# Parse results
for line in result.stdout.split('\n'):
    if 'Accepted:' in line: print(f"\n>>> {line.strip()}")
    if 'Rejected:' in line: print(f">>> {line.strip()}")
    if 'rejection' in line.lower() and 'reason' in line.lower():
        print(f">>> {line.strip()}")

rejection_rate = 2/7
print(f"\nRejection rate: {rejection_rate:.1%}")
print(f"Gate threshold: 20%")
print(f"Would trigger gate: {rejection_rate > 0.2}")

# Check expected rejections
act_rejected = 0
for line in result.stdout.split('\n'):
    if 'Rejected:' in line:
        try:
            act_rejected = int(line.strip().split()[1])
        except: pass

print(f"\nExpected rejections: {len(expected_rejections)}")
print(f"Actual rejected: {act_rejected}")
if act_rejected == len(expected_rejections):
    print("MATCH")
else:
    print(f"MISMATCH: expected {len(expected_rejections)}, got {act_rejected}")

# Save expected rejections
with open(run_logs / 'expected_rejections_C001.json', 'w', encoding='utf-8') as f:
    json.dump(expected_rejections, f, ensure_ascii=False, indent=2)

# Save manifest
manifest = {
    'run_id': run_id,
    'gate_test': True,
    'chunk': 'C001 (lore)',
    'total_objects': 7,
    'expected_rejections': len(expected_rejections),
    'actual_rejected': act_rejected,
    'rejection_rate': rejection_rate,
    'gate_triggered': rejection_rate > 0.2,
}
with open(run_logs / 'manifest.json', 'w', encoding='utf-8') as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

print(f"\nManifest: {run_logs / 'manifest.json'}")
print(f"Expected rejections: {run_logs / 'expected_rejections_C001.json'}")
print(f"\nOutput saved to: {run_logs}")

# Show rejected items
print(f"\nRejected items:")
for line in result.stdout.split('\n'):
    if 'Rejected items' in line:
        in_section = True
        continue
    if in_section and line.strip():
        print(f"  {line.strip()}")
