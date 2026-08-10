"""
Offset 回填器
输入模型产出的 {cite_id, quote} 格式，回填 offset_start/offset_end。
使用方式：validate.py 调用前先通过此回填器。
"""
import json, sys, io, os
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(__file__).parent.parent
WORK = BASE / 'work'

def load_cite_index():
    idx = {}
    path = WORK / 'cite_index.jsonl'
    if not path.exists():
        return idx
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                idx[rec['cite_id']] = rec
    return idx

def backfill_offsets(obj, cite_index, ambiguous_log=None):
    """
    Recursively backfill offset_start/offset_end for all citations in obj.
    Returns (modified_obj, errors) where errors is a list of failed citations.
    """
    errors = []
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k == 'citations' and isinstance(v, list):
                fixed_citations = []
                for cit in v:
                    if isinstance(cit, dict):
                        fixed_cit = dict(cit)
                        cid = fixed_cit.get('cite_id', '')
                        quote = fixed_cit.get('quote', '')
                        if cid and quote:
                            rec = cite_index.get(cid)
                            if rec and rec.get('clean'):
                                clean = rec['clean']
                                # Find all occurrences
                                start = 0
                                found_positions = []
                                while True:
                                    pos = clean.find(quote, start)
                                    if pos == -1:
                                        break
                                    found_positions.append(pos)
                                    start = pos + 1

                                if len(found_positions) == 0:
                                    errors.append({'cite_id': cid, 'quote': quote[:80],
                                                   'reason': 'quote_not_found'})
                                elif len(found_positions) == 1:
                                    fixed_cit['offset_start'] = found_positions[0]
                                    fixed_cit['offset_end'] = found_positions[0] + len(quote)
                                else:
                                    # Multiple matches: use first occurrence, log for review
                                    fixed_cit['offset_start'] = found_positions[0]
                                    fixed_cit['offset_end'] = found_positions[0] + len(quote)
                                    if ambiguous_log is not None:
                                        ambiguous_log.append({
                                            'cite_id': cid, 'quote': quote,
                                            'positions': found_positions,
                                            'used': found_positions[0],
                                        })
                            else:
                                errors.append({'cite_id': cid, 'quote': quote[:80],
                                               'reason': 'cite_id_not_in_index'})
                        elif cid:
                            errors.append({'cite_id': cid, 'quote': quote[:80] if quote else '',
                                           'reason': 'quote_empty'})
                        if 'offset_start' in fixed_cit or 'offset_end' in fixed_cit:
                            fixed_citations.append(fixed_cit)
                        elif cid:
                            # Preserve citation without offset so validator can catch it
                            fixed_citations.append(fixed_cit)
                    else:
                        fixed_citations.append(cit)
                result[k] = fixed_citations
            elif isinstance(v, dict):
                result[k], sub_errors = backfill_offsets(v, cite_index, ambiguous_log)
                errors.extend(sub_errors)
            elif isinstance(v, list):
                result[k] = v  # no nested citations in list items by design
            else:
                result[k] = v
        return result, errors
    return obj, errors

def process_output(input_path, output_path, ambiguous_path=None):
    """
    Process a model output file: read JSON Lines, backfill offsets, write enriched JSON Lines.
    Returns stats dict.
    """
    cite_index = load_cite_index()
    ambiguous_log = []

    total = 0
    backfilled = 0
    errors = []
    enriched_lines = []

    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                enriched_lines.append(line)
                continue
            try:
                obj = json.loads(line)
                total += 1
                enriched_obj, obj_errors = backfill_offsets(obj, cite_index, ambiguous_log)
                errors.extend(obj_errors)
                if not obj_errors:
                    backfilled += 1
                enriched_lines.append(json.dumps(enriched_obj, ensure_ascii=False) + '\n')
            except json.JSONDecodeError:
                errors.append({'reason': 'json_parse_failure', 'line': line[:100]})
                enriched_lines.append(line)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(enriched_lines)

    if ambiguous_path and ambiguous_log:
        with open(ambiguous_path, 'w', encoding='utf-8') as f:
            for entry in ambiguous_log:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    return {
        'total_objects': total,
        'backfilled_ok': backfilled,
        'errors': len(errors),
        'ambiguous_quotes': len(ambiguous_log),
        'error_details': errors[:10],
    }

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='Input JSONL file (model output)')
    parser.add_argument('--output', required=True, help='Output JSONL file (with offsets)')
    parser.add_argument('--ambiguous', default='', help='Path to log ambiguous quotes')
    args = parser.parse_args()

    stats = process_output(args.input, args.output, args.ambiguous)
    print(json.dumps(stats, ensure_ascii=False, indent=2))
