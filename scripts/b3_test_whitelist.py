"""
B3 验证：cite_id_out_of_scope 拒收测试
构造一条引用块外 cite_id 的对象，确认校验器以 cite_id_out_of_scope 拒收。
"""
import json, sys, io, subprocess
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(__file__).parent.parent
WORK = BASE / 'work'

# Load real cite_ids from cite_index
cite_ids = []
with open(WORK / 'cite_index.jsonl', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if i >= 100:
            break
        if line.strip():
            rec = json.loads(line)
            cite_ids.append(rec['cite_id'])

# Pick in-scope and out-of-scope cite_ids
in_scope = cite_ids[:5]
out_of_scope = cite_ids[-5:] if len(cite_ids) > 10 else ['FAKE-OUT-OF-SCOPE-99999']

print(f"In-scope cite_ids: {in_scope}")
print(f"Out-of-scope cite_ids: {out_of_scope}")

# Create a test object with an out-of-scope citation
test_obj = {
    'entity_id': 'CHAR:test-entity',
    'type': 'CHAR',
    'canonical_name': '测试实体',
    'aliases': [],
    'summary': {
        'text': '测试实体的摘要。',
        'claim_type': 'fact',
        'confidence': 'attested',
        'citations': [{'cite_id': out_of_scope[0], 'quote': '测试引文'}],
    },
    'attributes': [],
    'source_volume': 'lore',
}

# Write block-level whitelist (only in-scope cite_ids)
wl_path = BASE / 'tests' / 'fixtures' / 'b3_block_whitelist.json'
with open(wl_path, 'w', encoding='utf-8') as f:
    json.dump(in_scope, f, ensure_ascii=False)

print(f"\nBlock whitelist: {in_scope}")
print(f"Test object cite_id: {out_of_scope[0]} (NOT in whitelist)")

# Write test object
obj_path = BASE / 'tests' / 'fixtures' / 'b3_test_obj.jsonl'
with open(obj_path, 'w', encoding='utf-8') as f:
    f.write(json.dumps(test_obj, ensure_ascii=False) + '\n')

# Run validator with block whitelist
print(f"\nRunning validator...")
result = subprocess.run(
    [str(BASE / '.venv' / 'Scripts' / 'python.exe'),
     str(BASE / 'scripts' / 'validate.py'),
     str(obj_path),
     '--cite-whitelist', str(wl_path)],
    capture_output=True, text=True, timeout=30,
    cwd=str(BASE), encoding='utf-8', errors='replace'
)

print("\n" + "=" * 60)
print("VALIDATOR OUTPUT")
print("=" * 60)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[:500])

print("\n" + "=" * 60)
print("VERIFICATION")
print("=" * 60)
if 'cite_id_out_of_scope' in result.stdout:
    print("✓ cite_id_out_of_scope rejection confirmed!")
    for line in result.stdout.split('\n'):
        if 'cite_id_out_of_scope' in line:
            print(f"  → {line.strip()}")
else:
    print("✗ cite_id_out_of_scope NOT found in output!")
    print("  Searching for any rejection reasons...")
    for line in result.stdout.split('\n'):
        if 'REJECTED' in line or 'reject' in line.lower():
            print(f"  → {line.strip()}")
