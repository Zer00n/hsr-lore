"""
Falsifiable mock generator v2
Injects ~15% bad data covering all violation types.
Tracks expected rejections for automated verification.
"""
import json, random

VIOLATION_TYPES = [
    'fake_cite_id',           # cite_id not in whitelist
    'doctored_quote',         # quote modified from original
    'wrong_predicate',        # predicate not in 21-word vocab
    'fact_no_citation',       # claim_type=fact but no citations
    'interpretation_no_citation',  # claim_type=interpretation but no citations
    'bad_attribute_key',      # attribute key not in vocab, no x: prefix
    'missing_confidence',     # confidence field missing or empty
    'single_statement_contradiction',  # contradiction with only 1 statement
]

def inject_bad_mutation(obj, violation_type, cite_ids):
    """Mutate a good object to produce a specific violation."""
    obj = json.loads(json.dumps(obj))  # Deep copy
    expected = {'violation': violation_type, 'cite_id': obj.get('cite_id', '')}

    if violation_type == 'fake_cite_id':
        if obj.get('summary', {}).get('citations'):
            obj['summary']['citations'][0]['cite_id'] = 'FAKE-BAD-99999'
            expected['detail'] = 'cite_id=FAKE-BAD-99999'

    elif violation_type == 'doctored_quote':
        if obj.get('summary', {}).get('citations'):
            orig = obj['summary']['citations'][0].get('quote', '')
            obj['summary']['citations'][0]['quote'] = 'THIS IS A DOCTORED QUOTE NOT IN SOURCE'
            obj['summary']['citations'][0].pop('offset_start', None)
            obj['summary']['citations'][0].pop('offset_end', None)
            expected['detail'] = f'quote doctored from "{orig[:30]}..."'

    elif violation_type == 'wrong_predicate':
        if 'predicate' in obj:
            obj['predicate'] = 'IS_BEST_FRIEND'
            expected['detail'] = 'predicate=IS_BEST_FRIEND'

    elif violation_type == 'fact_no_citation':
        if obj.get('summary'):
            obj['summary']['claim_type'] = 'fact'
            obj['summary']['citations'] = []
            expected['detail'] = 'fact with empty citations'

    elif violation_type == 'interpretation_no_citation':
        if obj.get('summary'):
            obj['summary']['claim_type'] = 'interpretation'
            obj['summary']['citations'] = []
            expected['detail'] = 'interpretation with empty citations'

    elif violation_type == 'bad_attribute_key':
        if 'attributes' not in obj:
            obj['attributes'] = []
        obj['attributes'].append({'key': 'bad_key_not_in_vocab', 'value': 'test',
            'claim_type': 'fact', 'confidence': 'attested',
            'citations': obj.get('summary', {}).get('citations', [])})
        expected['detail'] = 'key=bad_key_not_in_vocab'

    elif violation_type == 'missing_confidence':
        if 'confidence' in obj:
            del obj['confidence']
            expected['detail'] = 'confidence missing'

    elif violation_type == 'single_statement_contradiction':
        obj = {'kind': 'contradiction', 'topic': 'Test contradiction',
               'statements': [{'text': 'Only one statement',
                               'citation': obj.get('summary', {}).get('citations', [{}])[0] if obj.get('summary', {}).get('citations') else {}}],
               'analysis': {'text': 'analysis', 'claim_type': 'interpretation', 'confidence': 'inferred',
                           'citations': obj.get('summary', {}).get('citations', []) if obj.get('summary', {}).get('citations') else []},
               'impact': 'low', 'source_volume': obj.get('source_volume', 'lore')}
        expected['detail'] = 'only 1 statement'

    return obj, expected

def generate_mock(task_id, volume, chunk, cite_index):
    """Generate mock output with ~15% bad data injection."""
    chunk_id = chunk['chunk_id']
    cite_ids = chunk.get('cite_ids', [])
    random.seed(hash(f"{task_id}{volume}{chunk_id}") % (2**32))

    # Pick real cite_ids for valid citations
    real_cites = []
    for cid in cite_ids[:5]:
        rec = cite_index.get(cid)
        if rec and rec.get('clean') and len(rec['clean']) >= 10:
            txt = rec['clean']
            end = random.randint(5, min(50, len(txt)))
            real_cites.append({'cite_id': cid, 'quote': txt[:end]})
    if not real_cites:
        return '', []

    expected_rejections = []
    good_objects = []
    bad_objects = []

    # Generate good objects first
    if 'entity' in task_id.lower() or task_id == 'T1':
        types = ['CHAR','AEON','PATH','ORGN','PLAC','WRLD','CONC','ARTF','RACE']
        predicates = ['MEMBER_OF','ALLY_OF','EMBODIES','LOCATED_IN','LEADS','EMISSARY_OF']
        n_entities = random.randint(3, 10)
        n_relations = random.randint(2, 6)
        for i in range(n_entities):
            t = random.choice(types)
            good_objects.append({
                'type': t, 'canonical_name': f'实体-{chunk_id}-{i}', 'aliases': [],
                'summary': {'text': f'实体-{chunk_id}-{i}的摘要。','claim_type': 'fact','confidence': 'attested',
                    'citations': [random.choice(real_cites)]},
                'attributes': [{'key': '身份', 'value': f'示例身份-{i}', 'claim_type': 'fact', 'confidence': 'attested',
                    'citations': [random.choice(real_cites)]}],
                'source_volume': volume,
            })
        for i in range(n_relations):
            good_objects.append({
                'subject_name': f'实体-{chunk_id}-{i}',
                'predicate': random.choice(predicates),
                'object_name': f'实体-{chunk_id}-{(i+1) % n_entities}',
                'qualifiers': {}, 'claim_type': 'fact', 'confidence': 'attested',
                'citations': [random.choice(real_cites)], 'source_volume': volume,
            })

    elif 'event' in task_id.lower() and 'timeline' not in task_id.lower():
        for i in range(random.randint(2, 6)):
            good_objects.append({
                'name': f'事件-{chunk_id}-{i}',
                'summary': {'text': '事件描述。','claim_type': 'fact','confidence': 'attested',
                    'citations': [random.choice(real_cites)]},
                'participants': [f'角色-{random.randint(1,10)}'], 'locations': [],
                'confidence': 'attested', 'citations': [random.choice(real_cites)], 'source_volume': volume,
            })

    elif 'relation' in task_id.lower():
        # T5: cross-volume relations — similar to T1 but outputs only relations
        predicates = ['MEMBER_OF','ALLY_OF','EMBODIES','LOCATED_IN','LEADS','EMISSARY_OF']
        n_relations = random.randint(3, 10)
        for i in range(n_relations):
            good_objects.append({
                'subject_name': f'跨卷实体-{chunk_id}-{i}',
                'predicate': random.choice(predicates),
                'object_name': f'跨卷实体-{chunk_id}-{(i+1) % max(n_relations-1, 1)}',
                'qualifiers': {}, 'claim_type': 'fact', 'confidence': 'attested',
                'citations': [random.choice(real_cites)], 'source_volume': volume,
            })

    elif 'discrepancy' in task_id.lower():
        for i in range(random.randint(1, 3)):
            good_objects.append({
                'kind': 'ambiguity', 'topic': f'矛盾-{chunk_id}-{i}',
                'statements': [{'text': 'A','citation': random.choice(real_cites)},
                              {'text': 'B','citation': random.choice(real_cites)}],
                'analysis': {'text': '分析。','claim_type': 'interpretation','confidence': 'inferred',
                    'citations': [random.choice(real_cites)]},
                'impact': 'low', 'source_volume': volume,
            })

    elif 'merge' in task_id.lower():
        for i in range(random.randint(1, 3)):
            good_objects.append({
                'merged_name': f'归并-{chunk_id}-{i}',
                'source_names': [f'实体A-{i}', f'实体B-{i}'],
                'method': 'alias_match',
                'rationale': {'text': '归并理由','claim_type': 'interpretation','confidence': 'inferred',
                    'citations': [random.choice(real_cites)]},
                'confidence': 'inferred',
            })

    elif 'timeline' in task_id.lower():
        for i in range(random.randint(2, 4)):
            good_objects.append({
                'event_name': f'事件-其他块-{i}',
                'relative_to': [{'relation': 'before', 'event_name': f'事件-其他块-{i+1}'}],
            })

    if not good_objects:
        return '', []

    # Inject ~15% bad data
    n_bad = max(1, int(len(good_objects) * 0.20))  # 20% for margin
    bad_indices = random.sample(range(len(good_objects)), min(n_bad, len(good_objects)))

    # Ensure diverse violations
    violations = list(VIOLATION_TYPES)
    random.shuffle(violations)
    violations = violations * 3  # Cycle through multiple times

    for j, idx in enumerate(sorted(bad_indices, reverse=True)):
        vtype = violations[j % len(VIOLATION_TYPES)]
        try:
            bad_obj, expected = inject_bad_mutation(good_objects[idx], vtype, cite_ids)
            bad_objects.append(bad_obj)
            expected_rejections.append(expected)
        except:
            pass
        good_objects.pop(idx)

    all_objects = good_objects + bad_objects
    random.shuffle(all_objects)

    lines = '\n'.join(json.dumps(o, ensure_ascii=False) for o in all_objects)
    return lines, expected_rejections
