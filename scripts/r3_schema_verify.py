"""
R3: Schema 反向测试逐条验证 v4
用 subprocess 调用 validate.py，逐条检查 invalid fixtures。
输出 work/r3_schema_invalid_report.json
"""
import json, sys, io, os, subprocess, tempfile
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(__file__).parent.parent
WORK = BASE / 'work'
VENV_PYTHON = BASE / '.venv' / 'Scripts' / 'python.exe'
VALIDATE_SCRIPT = BASE / 'scripts' / 'validate.py'
FIXTURES_PATH = BASE / 'tests' / 'fixtures' / 'invalid' / 'all.json'

# Design intent: entry_id → expected rejection reason keyword
DESIGN_INTENT = {
    'CHAR:TooLong': 'quote exceeds 200 chars',
    'CHAR:FakeID': 'cite_id not in whitelist',
    'CHAR:FakeQuote': 'quote not exact substring',
    'CHAR:BadOffset': 'offset mismatch',
    'CHAR:NoCite': 'citations must be non-empty',
    'REL:eeeeeeeeeeee': 'invalid predicate',  # IS_BEST_FRIEND not in vocab
    'CHAR:BadConf': 'invalid confidence',
    'WRONG_FORMAT': 'invalid entity_id',
    'DSC:ffffffffffff': 'contradiction needs at least 2',
    'DSC:gggggggggggg': 'invalid discrepancy_id',
    'REL:hhhhhhhhhhhh': 'invalid relation_id',
    'WRONG_REL_ID': 'invalid relation_id',
    'CHAR:BadClaim': 'invalid claim_type',
    'MRG:iiiiiiiiiiii': 'invalid merge_id',
    'CHAR:BadVol': 'invalid source_volume',
    'CHAR:NoCiteInterp': 'citations must be non-empty',
}

def get_entry_id(entry):
    for key in ['entity_id', 'relation_id', 'discrepancy_id', 'event_id', 'merge_id']:
        if key in entry:
            return entry[key]
    # Try to identify from other fields
    if isinstance(entry, dict):
        if 'summary' in entry and isinstance(entry['summary'], dict):
            txt = entry['summary'].get('text', '')[:60]
            if 'Fake' in txt or 'FAKE' in txt:
                for k in ['entity_id', 'relation_id']:
                    if k in entry:
                        return entry[k]
    return f'ENTRY_{hash(json.dumps(entry, sort_keys=True, default=str))}'

def validate_single(entry):
    """Run validate.py on a single entry via subprocess, parse output carefully."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', encoding='utf-8', delete=False) as f:
        json.dump([entry], f)
        tmp_path = f.name

    try:
        proc = subprocess.run(
            [str(VENV_PYTHON), str(VALIDATE_SCRIPT), tmp_path],
            capture_output=True, timeout=30,
            cwd=str(BASE),
            encoding='utf-8',
            errors='replace'
        )
        stdout = proc.stdout or ''

        accepted = False
        rejection_detail = ''
        rejection_reason = ''

        for line in stdout.split('\n'):
            # Look for "Accepted: N (X%)"
            if 'Accepted:' in line and not 'Accepted: 0' in line:
                m = line.strip()
                if 'Accepted: 1' in m or 'Accepted: 0' not in m:
                    # Parse "Accepted: 1 (100.0%)"
                    parts = m.split()
                    if len(parts) >= 2:
                        try:
                            if int(parts[1]) > 0:
                                accepted = True
                        except:
                            pass

            # Look for rejection detail lines: "[N] TYPE: reason — detail"
            if '—' in line and 'Rejected' not in line and 'Accepted' not in line and 'By type' not in line:
                # Format: "  [0] entity: citation_error — summary.citations[0]: quote exceeds 200 chars (len=250)"
                stripped = line.strip()
                if stripped.startswith('[') and ':' in stripped:
                    parts = stripped.split('—', 1)
                    if len(parts) >= 1:
                        # Extract reason from "  [N] entity: citation_error"
                        before_dash = parts[0].strip()
                        colon_parts = before_dash.split(':', 1)
                        if len(colon_parts) >= 2:
                            rejection_reason = colon_parts[1].strip()
                        elif len(colon_parts) >= 1:
                            rejection_reason = colon_parts[0].split(']', 1)[-1].strip()
                    if len(parts) >= 2:
                        rejection_detail = parts[1].strip()

        # Also check "Rejection reasons:" section
        if not rejection_reason:
            in_rejection_section = False
            for line in stdout.split('\n'):
                if 'Rejection reasons:' in line:
                    in_rejection_section = True
                    continue
                if in_rejection_section and line.strip().startswith('['):
                    # "  [  1] citation_error"
                    bracket_end = line.find(']', line.find(']') + 1)
                    if bracket_end > 0:
                        rejection_reason = line[bracket_end + 1:].strip()
                    break
                if in_rejection_section and not line.strip():
                    break

        return {
            'accepted': accepted,
            'rejection_reason': rejection_reason,
            'rejection_detail': rejection_detail,
            'stdout_full': stdout,
        }
    finally:
        os.unlink(tmp_path)

def main():
    with open(FIXTURES_PATH, 'r', encoding='utf-8') as f:
        invalid = json.load(f)

    results = []
    for i, entry in enumerate(invalid):
        entry_id = get_entry_id(entry)
        intended = DESIGN_INTENT.get(entry_id, 'unknown_intent')

        val = validate_single(entry)
        reason = val['rejection_reason']
        detail = val['rejection_detail']

        # Check if intended keyword appears in reason or detail
        intent_match = 'mismatch'
        combined = (reason + ' ' + detail).lower()
        intended_lower = intended.lower()
        # Check for substring match of intended keyword
        if intended != 'unknown_intent':
            keywords = intended_lower.replace('_', ' ').split()
            match_count = sum(1 for kw in keywords if kw in combined)
            if match_count >= len(keywords) * 0.5:  # at least half the keywords match
                intent_match = 'match'

        results.append({
            'index': i,
            'entry_id': entry_id,
            'intended_check': intended,
            'accepted': val['accepted'],
            'actual_rejection_reason': reason,
            'actual_rejection_detail': detail,
            'intent_vs_actual': intent_match,
        })

    report = {
        'total_invalid_entries': len(invalid),
        'results': results,
        'summary': {
            'accepted_in_error': sum(1 for r in results if r['accepted']),
            'correctly_rejected': sum(1 for r in results if not r['accepted']),
            'intent_matches': sum(1 for r in results if r['intent_vs_actual'] == 'match'),
            'intent_mismatches': sum(1 for r in results if r['intent_vs_actual'] == 'mismatch'),
        },
    }

    outpath = WORK / 'r3_schema_invalid_report.json'
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"R3 done: {len(results)} entries checked")
    print(f"  Accepted (error): {report['summary']['accepted_in_error']}")
    print(f"  Correctly rejected: {report['summary']['correctly_rejected']}")
    print(f"  Intent matches: {report['summary']['intent_matches']}")
    print(f"  Intent mismatches: {report['summary']['intent_mismatches']}")
    print(f"Output: {outpath}")
    print()

    for r in results:
        match_flag = 'OK' if r['intent_vs_actual'] == 'match' else 'MISMATCH'
        status = 'ACCEPTED' if r['accepted'] else 'REJECTED'
        print(f"{match_flag:8s} [{r['index']:2d}] {r['entry_id']:30s} | {status}: {r['actual_rejection_reason']}")
        if r['actual_rejection_detail']:
            print(f"         Detail: {r['actual_rejection_detail']}")

if __name__ == '__main__':
    main()
