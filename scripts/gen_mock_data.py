"""Generate mock test data — 20 valid + 15 invalid objects."""
import json, random, hashlib, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

idx = {}
for line in open('D:/Office/claudecode/star/hsr-lore/work/cite_index.jsonl', 'r', encoding='utf-8'):
    if line.strip():
        r = json.loads(line)
        idx[r['cite_id']] = r['clean']

random.seed(42)
cids = sorted(idx.keys())
# Pick diverse cite_ids from different volumes
from collections import defaultdict
by_vol = defaultdict(list)
for cid, info in idx.items():
    if 30 <= len(info) <= 200:
        by_vol[idx[cid][:10]].append(cid)  # dummy key
# Actually pick by volume
by_vol2 = defaultdict(list)
for line in open('D:/Office/claudecode/star/hsr-lore/work/cite_index.jsonl', 'r', encoding='utf-8'):
    if line.strip():
        r = json.loads(line)
        cid = r['cite_id']
        vol = r['volume']
        clean = r['clean']
        if 30 <= len(clean) <= 200:
            by_vol2[vol].append(cid)

diverse = []
for vol in ['lore', 'books', 'characters', 'narrative', 'dialogue', 'artifacts', 'rogue']:
    if by_vol2[vol]:
        diverse.append(random.choice(by_vol2[vol]))
# Add more from dialogue
while len(diverse) < 10:
    diverse.append(random.choice(by_vol2['dialogue']))
print('Diverse cite_ids:', diverse)

# --- 20 VALID objects ---
valid = []

def pick_quote(i):
    c = diverse[i % len(diverse)]
    q = idx[c][:40]
    return c, q

# Entities (8 + 2 extra for relation targets)
for i, (eid, typ, name) in enumerate([
    ('CHAR:三月七', 'CHAR', '三月七'),
    ('AEON:纳努克', 'AEON', '纳努克'),
    ('WRLD:雅利洛-Ⅵ', 'WRLD', '雅利洛-Ⅵ'),
    ('ORGN:星穹列车', 'ORGN', '星穹列车'),
    ('PLAC:黑塔空间站', 'PLAC', '黑塔空间站'),
    ('CONC:星核', 'CONC', '星核'),
    ('RACE:持明族', 'RACE', '持明族'),
    ('PATH:毁灭', 'PATH', '毁灭'),
    ('CHAR:丹恒', 'CHAR', '丹恒'),
    ('AEON:岚', 'AEON', '岚'),
]):
    c, q = pick_quote(i)
    valid.append({
        'entity_id': eid, 'type': typ, 'canonical_name': name,
        'aliases': [name[:2]] if i < 2 else [],
        'summary': {
            'text': name + '是星铁世界观中的存在。',
            'claim_type': 'fact', 'confidence': 'attested',
            'citations': [{'cite_id': c, 'quote': q, 'offset_start': 0, 'offset_end': len(q)}]
        },
        'attributes': [{
            'key': '描述', 'value': '来自游戏文本',
            'claim_type': 'fact', 'confidence': 'attested',
            'citations': [{'cite_id': c, 'quote': q, 'offset_start': 0, 'offset_end': len(q)}]
        }] if i < 3 else [],
        'source_volume': ['characters', 'lore', 'lore', 'narrative', 'books', 'artifacts', 'rogue', 'lore', 'characters', 'lore'][i]
    })

# Relations (5)
rels = [
    ('CHAR:三月七', 'MEMBER_OF', 'ORGN:星穹列车'),
    ('AEON:纳努克', 'EMBODIES', 'PATH:毁灭'),
    ('CHAR:三月七', 'RELATED_TO', 'CHAR:丹恒'),
    ('AEON:纳努克', 'OPPOSES', 'AEON:岚'),
    ('CHAR:三月七', 'LOCATED_IN', 'WRLD:雅利洛-Ⅵ'),
]
for i, (s, p, o) in enumerate(rels):
    c, q = pick_quote(i)
    rid = 'REL:' + hashlib.sha1((s + '|' + p + '|' + o).encode()).hexdigest()[:12]
    valid.append({
        'relation_id': rid, 'subject_id': s, 'predicate': p, 'object_id': o,
        'qualifiers': {'note': '测试关系'} if p == 'RELATED_TO' else {},
        'claim_type': 'fact', 'confidence': 'attested',
        'citations': [{'cite_id': c, 'quote': q, 'offset_start': 0, 'offset_end': len(q)}],
        'source_volume': 'characters'
    })

# Events (3)
for i, name in enumerate(['EVT:星核坠落', 'EVT:贝洛伯格建城', 'EVT:第一次开拓']):
    c, q = pick_quote(i)
    valid.append({
        'event_id': name, 'name': name.replace('EVT:', ''),
        'summary': {
            'text': name.replace('EVT:', '') + '的相关描述。',
            'claim_type': 'fact', 'confidence': 'attested',
            'citations': [{'cite_id': c, 'quote': q, 'offset_start': 0, 'offset_end': len(q)}]
        },
        'participants': [], 'locations': [],
        'stated_time': '未知',
        'relative_to': [] if i == 0 else [{'relation': 'after', 'event_id': 'EVT:星核坠落'}],
        'order_hint': i * 1000, 'confidence': 'attested',
        'citations': [{'cite_id': c, 'quote': q, 'offset_start': 0, 'offset_end': len(q)}]
    })

# Discrepancies (3)
valid.append({
    'discrepancy_id': 'DSC:' + 'a' * 12,
    'kind': 'contradiction', 'topic': '某角色的战斗能力',
    'statements': [
        {'text': '角色A战斗力极强。', 'citation': {'cite_id': diverse[0], 'quote': idx[diverse[0]][:30], 'offset_start': 0, 'offset_end': 30}},
        {'text': '角色A在战斗中落败。', 'citation': {'cite_id': diverse[1], 'quote': idx[diverse[1]][:30], 'offset_start': 0, 'offset_end': 30}}
    ],
    'analysis': {
        'text': '两处表述存在矛盾。', 'claim_type': 'interpretation', 'confidence': 'inferred',
        'citations': [{'cite_id': diverse[0], 'quote': idx[diverse[0]][:30], 'offset_start': 0, 'offset_end': 30}]
    },
    'related_entities': ['CHAR:三月七'], 'impact': 'medium'
})
valid.append({
    'discrepancy_id': 'DSC:' + 'b' * 12, 'kind': 'ambiguity', 'topic': '某事件的起因',
    'statements': [
        {'text': '起因不明。', 'citation': {'cite_id': diverse[2], 'quote': idx[diverse[2]][:30], 'offset_start': 0, 'offset_end': 30}}
    ],
    'analysis': {
        'text': '原文表述含混。', 'claim_type': 'interpretation', 'confidence': 'inferred',
        'citations': [{'cite_id': diverse[0], 'quote': idx[diverse[0]][:30], 'offset_start': 0, 'offset_end': 30}]
    },
    'related_entities': [], 'impact': 'low'
})
valid.append({
    'discrepancy_id': 'DSC:' + 'c' * 12, 'kind': 'gap', 'topic': '未解释的设定',
    'statements': [
        {'text': '某些设定未被解释。', 'citation': {'cite_id': diverse[3], 'quote': idx[diverse[3]][:30], 'offset_start': 0, 'offset_end': 30}}
    ],
    'analysis': {
        'text': '这是一个官方留白。', 'claim_type': 'interpretation', 'confidence': 'inferred',
        'citations': [{'cite_id': diverse[0], 'quote': idx[diverse[0]][:30], 'offset_start': 0, 'offset_end': 30}]
    },
    'related_entities': [], 'impact': 'low'
})

# MergeRecord (1)
valid.append({
    'merge_id': 'MRG:' + 'd' * 12,
    'merged_entity_id': 'CHAR:丹恒',
    'source_entity_ids': ['CHAR:丹恒', 'CHAR:丹恒•饮月'],
    'method': 'alias_match',
    'rationale': {
        'text': '同一角色的不同形态，通过别名关联确认。',
        'claim_type': 'interpretation',
        'citations': [{'cite_id': diverse[0], 'quote': idx[diverse[0]][:30], 'offset_start': 0, 'offset_end': 30}]
    },
    'confidence': 'inferred'
})

with open('D:/Office/claudecode/star/hsr-lore/tests/fixtures/valid/all.json', 'w', encoding='utf-8') as f:
    json.dump(valid, f, ensure_ascii=False, indent=2)
print('Valid: %d objects' % len(valid))

# --- 15 INVALID objects ---
invalid = []

# 1. quote too long (>200) — find a real long entry
long_cid = None
long_quote = None
for cid, info in idx.items():
    if len(info) >= 250:
        long_cid = cid
        long_quote = info[:250]
        break
if not long_cid:
    # Fallback: just repeat a short quote to exceed 200
    long_cid = diverse[0]
    long_quote = (idx[diverse[0]][:50] + ' ') * 5

invalid.append({
    'entity_id': 'CHAR:TooLong', 'type': 'CHAR', 'canonical_name': 'TooLong',
    'summary': {'text': 'test', 'claim_type': 'fact', 'confidence': 'attested',
        'citations': [{'cite_id': long_cid, 'quote': long_quote, 'offset_start': 0, 'offset_end': len(long_quote)}]},
    'source_volume': 'lore'
})

# 2. cite_id not in whitelist
invalid.append({
    'entity_id': 'CHAR:FakeID', 'type': 'CHAR', 'canonical_name': 'FakeID',
    'summary': {'text': 'test', 'claim_type': 'fact', 'confidence': 'attested',
        'citations': [{'cite_id': 'FAKE-99999', 'quote': 'fake quote', 'offset_start': 0, 'offset_end': 10}]},
    'source_volume': 'lore'
})

# 3. quote not substring
c = diverse[1]
invalid.append({
    'entity_id': 'CHAR:FakeQuote', 'type': 'CHAR', 'canonical_name': 'FakeQuote',
    'summary': {'text': 'test', 'claim_type': 'fact', 'confidence': 'attested',
        'citations': [{'cite_id': c, 'quote': 'THIS TEXT DOES NOT EXIST IN SOURCE', 'offset_start': 0, 'offset_end': 10}]},
    'source_volume': 'lore'
})

# 4. offset mismatch
c = diverse[2]; q = idx[c][:30]
invalid.append({
    'entity_id': 'CHAR:BadOffset', 'type': 'CHAR', 'canonical_name': 'BadOffset',
    'summary': {'text': 'test', 'claim_type': 'fact', 'confidence': 'attested',
        'citations': [{'cite_id': c, 'quote': q, 'offset_start': 999, 'offset_end': 999+len(q)}]},
    'source_volume': 'lore'
})

# 5. empty citations
invalid.append({
    'entity_id': 'CHAR:NoCite', 'type': 'CHAR', 'canonical_name': 'NoCite',
    'summary': {'text': 'test', 'claim_type': 'fact', 'confidence': 'attested', 'citations': []},
    'source_volume': 'lore'
})

# 6. invalid predicate
invalid.append({
    'relation_id': 'REL:' + 'e' * 12,
    'subject_id': 'CHAR:三月七', 'predicate': 'IS_BEST_FRIEND', 'object_id': 'CHAR:丹恒',
    'claim_type': 'fact', 'confidence': 'attested',
    'citations': [{'cite_id': diverse[0], 'quote': idx[diverse[0]][:30], 'offset_start': 0, 'offset_end': 30}],
    'source_volume': 'characters'
})

# 7. invalid confidence
invalid.append({
    'entity_id': 'CHAR:BadConf', 'type': 'CHAR', 'canonical_name': 'BadConf',
    'summary': {'text': 'test', 'claim_type': 'fact', 'confidence': 'maybe',
        'citations': [{'cite_id': diverse[0], 'quote': idx[diverse[0]][:30], 'offset_start': 0, 'offset_end': 30}]},
    'source_volume': 'lore'
})

# 8. invalid entity_id format
invalid.append({
    'entity_id': 'WRONG_FORMAT', 'type': 'CHAR', 'canonical_name': 'BadFormat',
    'summary': {'text': 'test', 'claim_type': 'fact', 'confidence': 'attested',
        'citations': [{'cite_id': diverse[0], 'quote': idx[diverse[0]][:30], 'offset_start': 0, 'offset_end': 30}]},
    'source_volume': 'lore'
})

# 9. contradiction with 1 statement
invalid.append({
    'discrepancy_id': 'DSC:' + 'f' * 12, 'kind': 'contradiction', 'topic': 'test',
    'statements': [
        {'text': 'only one', 'citation': {'cite_id': diverse[0], 'quote': idx[diverse[0]][:30], 'offset_start': 0, 'offset_end': 30}}
    ],
    'analysis': {'text': 'analysis', 'claim_type': 'interpretation', 'confidence': 'inferred', 'citations': []},
    'related_entities': [], 'impact': 'low'
})

# 10. analysis not interpretation
invalid.append({
    'discrepancy_id': 'DSC:' + 'g' * 12, 'kind': 'ambiguity', 'topic': 'test',
    'statements': [
        {'text': 'stmt', 'citation': {'cite_id': diverse[0], 'quote': idx[diverse[0]][:30], 'offset_start': 0, 'offset_end': 30}}
    ],
    'analysis': {'text': 'analysis', 'claim_type': 'fact', 'confidence': 'inferred', 'citations': [{'cite_id': diverse[0], 'quote': idx[diverse[0]][:30], 'offset_start': 0, 'offset_end': 30}]},
    'related_entities': [], 'impact': 'low'
})

# 11. subject_id not declared
invalid.append({
    'relation_id': 'REL:' + 'h' * 12,
    'subject_id': 'CHAR:UndefinedEntity', 'predicate': 'ALLY_OF', 'object_id': 'CHAR:三月七',
    'claim_type': 'fact', 'confidence': 'attested',
    'citations': [{'cite_id': diverse[0], 'quote': idx[diverse[0]][:30], 'offset_start': 0, 'offset_end': 30}],
    'source_volume': 'characters'
})

# 12. invalid relation_id format
invalid.append({
    'relation_id': 'WRONG_REL_ID',
    'subject_id': 'CHAR:三月七', 'predicate': 'ALLY_OF', 'object_id': 'CHAR:丹恒',
    'claim_type': 'fact', 'confidence': 'attested',
    'citations': [{'cite_id': diverse[0], 'quote': idx[diverse[0]][:30], 'offset_start': 0, 'offset_end': 30}],
    'source_volume': 'characters'
})

# 13. invalid claim_type
invalid.append({
    'entity_id': 'CHAR:BadClaim', 'type': 'CHAR', 'canonical_name': 'BadClaim',
    'summary': {'text': 'test', 'claim_type': 'guess', 'confidence': 'attested',
        'citations': [{'cite_id': diverse[0], 'quote': idx[diverse[0]][:30], 'offset_start': 0, 'offset_end': 30}]},
    'source_volume': 'lore'
})

# 14. merge_record rationale not interpretation
invalid.append({
    'merge_id': 'MRG:' + 'i' * 12,
    'merged_entity_id': 'CHAR:Test', 'source_entity_ids': ['CHAR:Test1', 'CHAR:Test2'],
    'method': 'exact_name',
    'rationale': {'text': 'reason', 'claim_type': 'fact', 'citations': [{'cite_id': diverse[0], 'quote': idx[diverse[0]][:30], 'offset_start': 0, 'offset_end': 30}]},
    'confidence': 'inferred'
})

# 15. invalid source_volume
invalid.append({
    'entity_id': 'CHAR:BadVol', 'type': 'CHAR', 'canonical_name': 'BadVol',
    'summary': {'text': 'test', 'claim_type': 'fact', 'confidence': 'attested',
        'citations': [{'cite_id': diverse[0], 'quote': idx[diverse[0]][:30], 'offset_start': 0, 'offset_end': 30}]},
    'source_volume': 'invalid_volume'
})

# 16. interpretation text without citations (new — tightened constraint)
invalid.append({
    'entity_id': 'CHAR:NoCiteInterp', 'type': 'CHAR', 'canonical_name': 'NoCiteInterp',
    'summary': {
        'text': '这是一个模型分析，应该有引证。',
        'claim_type': 'interpretation', 'confidence': 'inferred',
        'citations': []
    },
    'source_volume': 'lore'
})

with open('D:/Office/claudecode/star/hsr-lore/tests/fixtures/invalid/all.json', 'w', encoding='utf-8') as f:
    json.dump(invalid, f, ensure_ascii=False, indent=2)
print('Invalid: %d objects' % len(invalid))
print('Done!')