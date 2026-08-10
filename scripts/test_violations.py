"""Precision test: verify each of 8 violation types triggers exactly 1 rejection"""
import json, subprocess, os, tempfile
from pathlib import Path

BASE = Path(__file__).parent.parent
WORK = BASE / 'work'

cite_index = {}
with open(WORK / 'cite_index.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            rec = json.loads(line)
            cite_index[rec['cite_id']] = rec

# Find a real cite for valid references
real_cite = None
for cid, rec in cite_index.items():
    if rec.get('clean') and len(rec['clean']) > 20:
        real_cite = {'cite_id': cid, 'quote': rec['clean'][:40]}
        break

def test_violation(name, obj):
    """Run single object through backfill+validate, return success."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', encoding='utf-8', delete=False) as f:
        f.write(json.dumps(obj, ensure_ascii=False) + '\n')
        tmp_dir = os.path.dirname(f.name)
        tmp_name = f.name

    backfilled = tmp_name.replace('.jsonl', '_bf.jsonl')
    subprocess.run([str(BASE / '.venv' / 'Scripts' / 'python.exe'),
        str(BASE / 'scripts' / 'backfill_offsets.py'), tmp_name, '--output', backfilled],
        cwd=str(BASE), capture_output=True)

    result = subprocess.run([str(BASE / '.venv' / 'Scripts' / 'python.exe'),
        str(BASE / 'scripts' / 'validate.py'), backfilled],
        capture_output=True, text=True, cwd=str(BASE), encoding='utf-8', errors='replace')

    accepted = 'Accepted: 1' in result.stdout
    rejected = 'Rejected: 1' in result.stdout
    os.unlink(tmp_name)
    if os.path.exists(backfilled):
        os.unlink(backfilled)
    return accepted, rejected, result.stdout

# Test each violation type
tests = {
    'fake_cite_id': {
        'type': 'CHAR', 'canonical_name': 'Test', 'aliases': [],
        'summary': {'text': 'x','claim_type': 'fact','confidence': 'attested',
            'citations': [{'cite_id': 'FAKE-NOT-REAL', 'quote': 'xyz'}]},
        'attributes': [], 'source_volume': 'lore',
    },
    'doctored_quote': {
        'type': 'CHAR', 'canonical_name': 'Test', 'aliases': [],
        'summary': {'text': 'x','claim_type': 'fact','confidence': 'attested',
            'citations': [{'cite_id': real_cite['cite_id'], 'quote': 'THIS_DOCTORED_QUOTE_NOT_IN_SOURCE_XYZ'}]},
        'attributes': [], 'source_volume': 'lore',
    },
    'wrong_predicate': {
        'subject_name': '纳努克', 'predicate': 'IS_BEST_FRIEND', 'object_name': '毁灭',
        'qualifiers': {}, 'claim_type': 'fact', 'confidence': 'attested',
        'citations': [real_cite], 'source_volume': 'lore',
    },
    'fact_no_citation': {
        'type': 'CHAR', 'canonical_name': 'Test', 'aliases': [],
        'summary': {'text': 'x','claim_type': 'fact','confidence': 'attested', 'citations': []},
        'attributes': [], 'source_volume': 'lore',
    },
    'interp_no_citation': {
        'type': 'CHAR', 'canonical_name': 'Test', 'aliases': [],
        'summary': {'text': 'x','claim_type': 'interpretation','confidence': 'inferred', 'citations': []},
        'attributes': [], 'source_volume': 'lore',
    },
    'bad_attr_key': {
        'type': 'CHAR', 'canonical_name': 'Test', 'aliases': [],
        'summary': {'text': 'x','claim_type': 'fact','confidence': 'attested', 'citations': [real_cite]},
        'attributes': [{'key': 'bad_key_xyz', 'value': 'v', 'claim_type': 'fact', 'confidence': 'attested', 'citations': [real_cite]}],
        'source_volume': 'lore',
    },
    'missing_confidence': {
        'type': 'CHAR', 'canonical_name': 'Test', 'aliases': [],
        'summary': {'text': 'x','claim_type': 'fact','confidence': 'attested', 'citations': [real_cite]},
        'attributes': [], 'source_volume': 'lore',
    },
    'single_statement_contradiction': {
        'kind': 'contradiction', 'topic': 'Test',
        'statements': [{'text': 'only one', 'citation': real_cite}],
        'analysis': {'text': 'x','claim_type': 'interpretation','confidence': 'inferred', 'citations': [real_cite]},
        'impact': 'low', 'source_volume': 'lore',
    },
}

print(f"{'Violation':>30s} {'Accepted':>8s} {'Rejected':>8s} {'Status':>8s}")
print("-" * 60)
for name, obj in tests.items():
    accepted, rejected, stdout = test_violation(name, obj)

    # For missing_confidence: object doesn't have confidence field at top level
    # Schema validation should reject
    status = 'OK' if (not accepted and rejected) else 'FAIL'
    if accepted and rejected: status = 'BOTH?'
    if not accepted and not rejected: status = 'NEITHER?'

    print(f"{name:>30s} {str(accepted):>8s} {str(rejected):>8s} {status:>8s}")
    if status != 'OK':
        # Show rejection reason from stdout
        for line in stdout.split('\n'):
            if 'Rejected items' in line or 'rejection' in line.lower():
                print(f"  {line.strip()}")
