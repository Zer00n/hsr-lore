"""
星铁世界观站 校验器
输入 JSONL 对象，输出通过/拒收结果与统计报告。
12 项检查，违反即整条拒收。
"""
import json, os, sys, io, re, hashlib, glob
from pathlib import Path
from collections import defaultdict, Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(__file__).parent.parent
SCHEMA_DIR = BASE / 'schema'
WORK_DIR = BASE / 'work'
DEBUG_DIR = BASE / 'work' / 'debug'

# ── JSON Tolerant Parser ──────────────────────────────────────

def tolerant_json_parse(line):
    """
    Try to parse a JSON line, with conservative fixes for common errors.
    Returns (obj, status) where status is 'direct', 'fixed', or 'unparseable'.
    Only applies deterministic fixes — no guessing.
    """
    original = line.strip()
    if not original:
        return None, 'empty'

    # Attempt 1: direct parse
    try:
        return json.loads(original), 'direct'
    except json.JSONDecodeError:
        pass

    # Attempt 2: count braces, add missing closers at end
    # Only handles the case where braces are simply missing at the end
    open_braces = original.count('{') - original.count('}')
    open_brackets = original.count('[') - original.count(']')
    if open_braces > 0 or open_brackets > 0:
        fixed = original.rstrip()
        # Fix bracket count: don't blindly add ] because we don't know where
        # Only add missing }] at the end if consistent
        if open_brackets == 1:
            # Missing one ]  — common when model skips closing a citations array
            # Try adding ] before the final } sequence
            if open_braces == 0:
                # Braces balanced, just missing ]
                fixed = fixed + ']'
            elif open_braces == 1:
                fixed = fixed + ']' + '}'
            elif open_braces >= 2:
                fixed = fixed + ']' + '}' * open_braces
            else:
                return original, 'unparseable'
        elif open_braces == 1 and open_brackets == 0:
            # Single missing closing brace
            fixed = fixed + '}'
        elif open_braces == 2 and open_brackets == 0:
            fixed = fixed + '}}'
        else:
            # Too ambiguous — don't guess
            return original, 'unparseable'

        try:
            obj = json.loads(fixed)
            return obj, 'fixed'
        except json.JSONDecodeError:
            pass

    # Attempt 3: missing ] before }  (common pattern: citations array missing closing bracket)
    # Model writes: ..."quote":"...一员。"}},...  but should be: ...一员。"}]},...
    # "}} = close citation } + close summary }. Missing: close array ].
    # Fix: insert ] between the two } of "}}
    if original.count('[') == original.count(']') + 1:
        fixed = original
        for m in re.finditer(r'"(}})', fixed):
            pos = m.start(1)  # start of }}
            if pos > 0 and fixed[pos-1] == '"':
                # Insert ] after first } of }}: "}}  → "}]}
                fixed = fixed[:pos+1] + ']' + fixed[pos+1:]
                try:
                    obj = json.loads(fixed)
                    return obj, 'fixed'
                except json.JSONDecodeError:
                    pass
                break  # only fix first occurrence

    return original, 'unparseable'

# ── Chinese Predicate Mapper ─────────────────────────────────

PREDICATE_ZH_MAP = {}

def load_predicate_zh_map():
    global PREDICATE_ZH_MAP
    map_path = SCHEMA_DIR / 'predicate_zh_map.json'
    if map_path.exists():
        with open(map_path, 'r', encoding='utf-8') as f:
            PREDICATE_ZH_MAP = json.load(f)

PREDICATE_MAPPING_LOG = []

def map_predicate(obj, chunk_id=''):
    """
    Map Chinese predicates to English codes.
    Returns the modified object (possibly with swapped subject/object).
    Records mapping events to PREDICATE_MAPPING_LOG.
    """
    pred = obj.get('predicate', '')
    if not pred:
        return obj

    # If predicate is already a valid English code in the vocabulary, leave it
    VALID_PREDICATES = {
        'EMBODIES', 'EMISSARY_OF', 'FOLLOWER_OF', 'OPPOSES',
        'MEMBER_OF', 'LEADS', 'MENTOR_OF', 'KIN_OF', 'ALLY_OF',
        'ENEMY_OF', 'SUCCEEDS', 'CREATED', 'KILLED', 'TRANSFORMED_INTO',
        'LOCATED_IN', 'ORIGINATES_FROM', 'RULES',
        'PARTICIPATED_IN', 'CAUSED', 'RESULTED_IN', 'RELATED_TO'
    }
    if pred in VALID_PREDICATES:
        return obj

    # Check explicit mapping table
    if pred in PREDICATE_ZH_MAP:
        mapping = PREDICATE_ZH_MAP[pred]
        target = mapping['target']
        swap = mapping.get('swap', False)
        note_extra = mapping.get('note', '')

        PREDICATE_MAPPING_LOG.append({
            'chunk_id': chunk_id,
            'original_predicate': pred,
            'mapped_to': target,
            'swapped_direction': swap,
            'note_added': note_extra,
        })

        obj['predicate'] = target

        if swap:
            subj = obj.get('subject_name', '')
            objj = obj.get('object_name', '')
            obj['subject_name'] = objj
            obj['object_name'] = subj

        if note_extra and not obj.get('qualifiers'):
            obj['qualifiers'] = {}
        if note_extra:
            existing_note = obj.get('qualifiers', {}).get('note', '')
            obj['qualifiers']['note'] = (existing_note + '; ' if existing_note else '') + note_extra

        return obj

    # Fallback: any unknown Chinese predicate → RELATED_TO with note
    PREDICATE_MAPPING_LOG.append({
        'chunk_id': chunk_id,
        'original_predicate': pred,
        'mapped_to': 'RELATED_TO',
        'swapped_direction': False,
        'note_added': pred,
    })
    obj['predicate'] = 'RELATED_TO'
    if not obj.get('qualifiers'):
        obj['qualifiers'] = {}
    existing_note = obj.get('qualifiers', {}).get('note', '')
    obj['qualifiers']['note'] = (existing_note + '; ' if existing_note else '') + f'原始谓词: {pred}'
    return obj

def flush_predicate_log():
    if not PREDICATE_MAPPING_LOG:
        return
    log_path = WORK_DIR / 'predicate_mapping_log.jsonl'
    with open(log_path, 'a', encoding='utf-8') as f:
        for entry in PREDICATE_MAPPING_LOG:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    PREDICATE_MAPPING_LOG.clear()

# ── Load references ────────────────────────────────────────────

def load_schema(name):
    with open(SCHEMA_DIR / name, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_cite_index():
    idx = {}
    path = WORK_DIR / 'cite_index.jsonl'
    if not path.exists():
        print('WARNING: cite_index.jsonl not found, cite-check disabled')
        return idx
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                idx[rec['cite_id']] = rec
    return idx

def load_whitelist():
    path = WORK_DIR / 'cite_whitelist.txt'
    if not path.exists():
        return set()
    with open(path, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip())

def load_predicates():
    with open(SCHEMA_DIR / 'predicates.json', 'r', encoding='utf-8') as f:
        return json.load(f)

cite_index = load_cite_index()
cite_whitelist = load_whitelist()
block_whitelist_mode = False  # True when using per-block whitelist
predicates_data = load_predicates()
VALID_PREDICATES = set(predicates_data['all'])
ENTITY_TYPES = {'AEON', 'PATH', 'CHAR', 'ORGN', 'PLAC', 'WRLD', 'CONC', 'ARTF', 'RACE'}
CONFIDENCE_VALUES = {'attested', 'inferred', 'disputed'}
CLAIM_TYPES = {'fact', 'interpretation'}
VOLUMES = {'lore', 'books', 'characters', 'narrative', 'dialogue', 'artifacts', 'rogue', 'unattributed'}

def load_attribute_keys():
    path = SCHEMA_DIR / 'attribute_keys.json'
    if not path.exists():
        return set(), 0.15
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return set(data.get('keys', {}).keys()), data.get('custom_warning_threshold', 0.15)

VALID_ATTR_KEYS, ATTR_CUSTOM_THRESHOLD = load_attribute_keys()

print(f'Cite index: {len(cite_index)} entries')
print(f'Cite whitelist: {len(cite_whitelist)} IDs')
print(f'Predicates: {len(VALID_PREDICATES)} in vocabulary')
print(f'Attribute keys: {len(VALID_ATTR_KEYS)} in vocabulary\n')

# ── Validation functions ────────────────────────────────────────

REJECTION_REASONS = Counter()

def reject(obj, reason, detail=''):
    REJECTION_REASONS[(reason, detail[:120])] += 1
    return {'status': 'REJECTED', 'reason': reason, 'detail': detail}

def accept(obj):
    return {'status': 'ACCEPTED'}

def normalize_for_match(text):
    """
    Normalize text before exact substring matching.
    Removes formatting artifacts (newlines/whitespace) that cause
    false negatives without changing the semantic content.
    Rules documented in article: normalize whitespace only.
    """
    return re.sub(r'\s+', '', text)

def validate_citation(cit, obj_context=''):
    """Validate a single Citation object."""
    errors = []

    # Check cite_id in whitelist
    cid = cit.get('cite_id', '')
    if cid and cite_whitelist and cid not in cite_whitelist:
        if block_whitelist_mode:
            # Block-level whitelist: cite_id exists in corpus but isn't in this block's scope
            errors.append(('cite_id_out_of_scope', f'cid={cid} (in corpus but not in block whitelist)'))
        else:
            errors.append(('cite_id not in whitelist', cid))

    # Check quote length
    quote = cit.get('quote', '')
    if len(quote) > 200:
        errors.append(('quote exceeds 200 chars', f'len={len(quote)}'))

    # Check quote is exact substring of clean (with whitespace normalization)
    if cid and cid in cite_index:
        clean = cite_index[cid]['clean']
        if quote not in clean and normalize_for_match(quote) not in normalize_for_match(clean):
            errors.append(('quote not exact substring of clean', f'cid={cid}, quote={quote[:60]}...'))
        else:
            # Check offsets
            start = cit.get('offset_start', -1)
            end = cit.get('offset_end', -1)
            if start >= 0 and end >= 0:
                actual = clean[start:end]
                if actual != quote:
                    errors.append(('offset mismatch', f'expected {quote[:30]}... got {actual[:30]}...'))

    return errors

def validate_entity_ids(obj, declared_entities):
    """Check that entity references point to declared entities."""
    errors = []
    eid = obj.get('entity_id', '')
    if eid:
        # Check format
        if not re.match(r'^(AEON|PATH|CHAR|ORGN|PLAC|WRLD|CONC|ARTF|RACE):.+$', eid):
            errors.append(('invalid entity_id format', eid))
    return errors

def validate_relation_ids(obj, declared_entities):
    """Check subject_id and object_id exist."""
    errors = []
    sid = obj.get('subject_id', '')
    oid = obj.get('object_id', '')
    if declared_entities and sid not in declared_entities:
        errors.append(('subject_id not declared', sid))
    if declared_entities and oid not in declared_entities:
        errors.append(('object_id not declared', oid))
    return errors

def validate_cycle_detection(events):
    """Check relative_to for cycles."""
    # Build graph
    graph = defaultdict(list)
    for evt in events:
        eid = evt.get('event_id', '')
        for rel in evt.get('relative_to', []):
            target = rel.get('event_id', '')
            if eid and target:
                graph[eid].append(target)

    # DFS cycle detection
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {}

    def dfs(node):
        color[node] = GRAY
        for neighbor in graph.get(node, []):
            if neighbor not in color:
                if dfs(neighbor):
                    return True
            elif color[neighbor] == GRAY:
                return True
        color[node] = BLACK
        return False

    cycles = []
    for node in graph:
        color = {}
        if node not in color:
            if dfs(node):
                cycles.append(node)
    return cycles

# ── Main validator ──────────────────────────────────────────────

def validate_objects(objects, chunk_id=''):
    """Validate a list of objects. Returns (results, stats)."""
    # ── Apply Chinese predicate mapping ──
    load_predicate_zh_map()
    mapped_count = 0
    for obj in objects:
        if 'predicate' in obj:
            old_pred = obj['predicate']
            map_predicate(obj, chunk_id)
            if old_pred != obj['predicate']:
                mapped_count += 1
    if mapped_count > 0:
        print(f'  Predicate mapped: {mapped_count} relations')

    results = []
    stats = {
        'total': len(objects),
        'accepted': 0,
        'rejected': 0,
        'by_type': Counter(),
        'by_reason': Counter(),
        'predicate_usage': Counter(),
        'custom_attr_keys': 0,
        'total_attr_keys': 0,
        'related_to_ratio': 0.0,
        'cycle_events': [],
        'predicate_mapped': 0,
        'predicate_mapping_details': [],
    }

    declared_entities = set()
    declared_events = set()

    # First pass: collect declared IDs
    for obj in objects:
        typ = obj.get('type', '') or obj.get('kind', '') or ''
        eid = obj.get('entity_id', '') or obj.get('event_id', '') or obj.get('discrepancy_id', '') or obj.get('merge_id', '') or obj.get('relation_id', '')
        if obj.get('entity_id'):
            declared_entities.add(obj['entity_id'])
        if obj.get('event_id'):
            declared_events.add(obj['event_id'])

    # Second pass: validate each object
    for i, obj in enumerate(objects):
        item_results = []
        obj_type = 'unknown'

        # Determine type
        if 'entity_id' in obj:
            obj_type = 'entity'
        elif 'relation_id' in obj:
            obj_type = 'relation'
        elif 'event_id' in obj:
            obj_type = 'event'
        elif 'discrepancy_id' in obj:
            obj_type = 'discrepancy'
        elif 'merge_id' in obj:
            obj_type = 'merge_record'
        # Fallback: content-based type detection for model output without IDs
        if obj_type == 'unknown':
            if 'predicate' in obj or 'relation_type' in obj or ('subject_name' in obj and 'object_name' in obj) or ('subject' in obj and 'object' in obj) or ('source_entity_id' in obj and 'target_entity_id' in obj):
                obj_type = 'relation'
            elif 'kind' in obj and obj.get('kind') in ('contradiction','ambiguity','gap','retcon'):
                obj_type = 'discrepancy'
            elif obj.get('type') == 'relation':
                obj_type = 'relation'
            elif obj.get('type') == 'event':
                obj_type = 'event'
            elif 'canonical_name' in obj or 'name' in obj or ('type' in obj and 'predicate' not in obj and 'relation_type' not in obj):
                obj_type = 'entity'
            elif 'name' in obj and ('stated_time' in obj or 'participants' in obj or 'relative_to' in obj):
                obj_type = 'event'

        stats['by_type'][obj_type] += 1

        # ── Schema normalization ──────────────────────────────────────
        # doubao-seed-evolving consistently uses its own field naming:
        # Entity:   {type:'entity', entity_type:'CHAR', name:'...', description:'...', id:'...', aliases:[...]}
        # Relation: {type:'relation', source_entity_id:'...', target_entity_id:'...', relation_type:'...', description:'...'}
        # Event:    {type:'event', name:'...', description:'...', ...}
        # Normalize to canonical form expected by downstream consumers.

        # ── Entity normalization ──
        if obj.get('type') == 'entity' and 'entity_type' in obj:
            obj['type'] = obj['entity_type']
            del obj['entity_type']
        if 'name' in obj and 'canonical_name' not in obj:
            obj['canonical_name'] = obj.pop('name')
        if 'description' in obj and 'summary' not in obj:
            desc = obj.pop('description')
            obj['summary'] = {
                'text': desc,
                'claim_type': obj.get('claim_type', 'fact'),
                'confidence': obj.get('confidence', 'attested'),
                'citations': obj.get('citations', [])
            }
        # Build citation from 'id' field if present (model uses id as entity/cite reference)
        if 'id' in obj and obj.get('id', '').startswith(('AEON-','PATH-','CHAR-','BOOK-','NOUN-','LOAD-','CHRN-','TALK-','WRLD-')):
            if 'summary' in obj:
                sid = obj.pop('id')
                existing = obj['summary'].get('citations', [])
                if not existing:
                    obj['summary']['citations'] = [{'cite_id': sid, 'quote': ''}]

        # ── Relation normalization ──
        if obj.get('type') == 'relation':
            if 'relation_type' in obj and 'predicate' not in obj:
                obj['predicate'] = obj.pop('relation_type')
            if 'source_entity_id' in obj and 'subject_name' not in obj:
                obj['subject_name'] = obj.pop('source_entity_id')
            if 'target_entity_id' in obj and 'object_name' not in obj:
                obj['object_name'] = obj.pop('target_entity_id')
            if 'description' in obj:
                desc = obj.pop('description')
                if 'qualifiers' not in obj:
                    obj['qualifiers'] = {}
                obj['qualifiers']['note'] = desc
                # Build citation stub
                if 'citations' not in obj or not obj['citations']:
                    obj['citations'] = []
            # Ensure required claim_type/confidence for relations
            if 'claim_type' not in obj:
                obj['claim_type'] = 'fact'
            if 'confidence' not in obj:
                obj['confidence'] = 'attested'

        # Clean up stray 'id' and 'source' from model output
        for f in ['id', 'source']:
            if f in obj and f not in ('subject_name', 'object_name', 'canonical_name', 'predicate', 'type'):
                pass  # keep, may be useful

        # ── Entity type code normalization ──
        if obj_type == 'entity':
            TYPE_CODE_ALIASES = {
                'CHARACTER': 'CHAR', 'PERSON': 'CHAR', 'PERSONA': 'CHAR',
                'FACTION': 'ORGN', 'FAC': 'ORGN', 'ORG': 'ORGN', 'ORGANIZATION': 'ORGN',
                'LOCATION': 'PLAC', 'LOC': 'PLAC', 'PLACE': 'PLAC',
                'ITEM': 'ARTF', 'ARTIFACT': 'ARTF', 'OBJECT': 'ARTF',
                'EVENT': 'CONC', 'OCCURRENCE': 'CONC',
                'VEHICLE': 'ARTF', 'SHIP': 'ARTF',
                'CONCEPT': 'CONC',
                'SPECIES': 'RACE', 'PEOPLE': 'RACE',
            }
            if obj.get('type', '') in TYPE_CODE_ALIASES:
                obj['type'] = TYPE_CODE_ALIASES[obj['type']]

        # ── Event normalization ──
        if obj.get('type') == 'event':
            if 'description' in obj and 'summary' not in obj:
                obj['summary'] = {'text': obj.pop('description'),
                                 'claim_type': 'fact', 'confidence': 'attested', 'citations': obj.get('citations', [])}
            if 'confidence' not in obj:
                obj['confidence'] = 'attested'
            if 'citations' not in obj:
                obj['citations'] = []

        # ── Required field checks ──
        VALID_ENTITY_TYPES = {'AEON', 'PATH', 'CHAR', 'ORGN', 'PLAC', 'WRLD', 'CONC', 'ARTF', 'RACE'}

        if obj_type == 'entity':
            # Required: type in valid codes
            if 'type' not in obj:
                item_results.append(('missing_required_field', 'entity: type'))
            elif obj['type'] not in VALID_ENTITY_TYPES:
                item_results.append(('invalid_entity_type', f"got '{obj['type']}', valid: {sorted(VALID_ENTITY_TYPES)}"))
            # Required: canonical_name
            if 'canonical_name' not in obj:
                item_results.append(('missing_required_field', 'entity: canonical_name'))
            # Required: summary with citations
            if 'summary' not in obj:
                item_results.append(('missing_required_field', 'entity: summary'))
            else:
                s = obj['summary']
                if 'text' not in s:
                    item_results.append(('missing_required_field', 'entity: summary.text'))
                if 'claim_type' not in s:
                    item_results.append(('missing_required_field', 'entity: summary.claim_type'))
                if 'confidence' not in s:
                    item_results.append(('missing_required_field', 'entity: summary.confidence'))
                if 'citations' not in s or len(s.get('citations', [])) == 0:
                    item_results.append(('citations_empty', 'entity: summary has no citations'))

        elif obj_type == 'relation':
            for field in ['subject_name', 'predicate', 'object_name']:
                if field not in obj:
                    item_results.append(('missing_required_field', f'relation: {field}'))
            if 'claim_type' not in obj:
                item_results.append(('missing_required_field', 'relation: claim_type'))
            if 'confidence' not in obj:
                item_results.append(('missing_required_field', 'relation: confidence'))
            if 'citations' not in obj or len(obj.get('citations', [])) == 0:
                item_results.append(('citations_empty', 'relation: no citations'))

        elif obj_type == 'event':
            for field in ['name', 'summary']:
                if field not in obj:
                    item_results.append(('missing_required_field', f'event: {field}'))
            if 'confidence' not in obj:
                item_results.append(('missing_required_field', 'event: confidence'))
            if 'citations' not in obj or len(obj.get('citations', [])) == 0:
                item_results.append(('citations_empty', 'event: no citations'))

        elif obj_type == 'discrepancy':
            for field in ['kind', 'topic', 'statements', 'analysis']:
                if field not in obj:
                    item_results.append(('missing_required_field', f'discrepancy: {field}'))
            if 'analysis' in obj:
                a = obj['analysis']
                if 'citations' not in a or len(a.get('citations', [])) == 0:
                    item_results.append(('citations_empty', 'discrepancy: analysis has no citations'))

        # Check all citations
        all_citations = []
        def collect_citations(o, path=''):
            if isinstance(o, dict):
                if 'cite_id' in o and 'quote' in o:
                    all_citations.append((path, o))
                for k, v in o.items():
                    collect_citations(v, f'{path}.{k}' if path else k)
            elif isinstance(o, list):
                for j, item in enumerate(o):
                    collect_citations(item, f'{path}[{j}]')
        collect_citations(obj)

        for path, cit in all_citations:
            cit_errors = validate_citation(cit, path)
            for reason, detail in cit_errors:
                item_results.append(('citation_error', f'{path}: {reason} ({detail})'))

        # Check natural language fields have non-empty citations
        def check_nl_fields(o, prefix=''):
            errors = []
            if isinstance(o, dict):
                if 'text' in o and 'claim_type' in o:
                    # ALL natural language fields must carry non-empty citations,
                    # regardless of claim_type. Fact citations point to the stated source;
                    # interpretation citations point to the interpreted source.
                    if 'citations' not in o or len(o.get('citations', [])) == 0:
                        errors.append(('citations_empty', f'{prefix} has text but no citations'))
                for k, v in o.items():
                    errors.extend(check_nl_fields(v, f'{prefix}.{k}' if prefix else k))
            elif isinstance(o, list):
                for j, item in enumerate(o):
                    errors.extend(check_nl_fields(item, f'{prefix}[{j}]'))
            return errors
        nl_errors = check_nl_fields(obj)
        for reason, detail in nl_errors:
            item_results.append(('citations_empty', detail))

        # Check confidence values
        def check_confidence(o, prefix=''):
            errors = []
            if isinstance(o, dict):
                if 'confidence' in o and o['confidence'] not in CONFIDENCE_VALUES:
                    errors.append(('invalid_confidence', f'{prefix}.confidence={o["confidence"]}'))
                if 'claim_type' in o and o['claim_type'] not in CLAIM_TYPES:
                    errors.append(('invalid_claim_type', f'{prefix}.claim_type={o["claim_type"]}'))
                for k, v in o.items():
                    errors.extend(check_confidence(v, f'{prefix}.{k}' if prefix else k))
            elif isinstance(o, list):
                for j, item in enumerate(o):
                    errors.extend(check_confidence(item, f'{prefix}[{j}]'))
            return errors
        conf_errors = check_confidence(obj)
        for reason, detail in conf_errors:
            item_results.append((reason, detail))

        # Type-specific checks
        if obj_type == 'relation':
            # Check predicate
            pred = obj.get('predicate', '')
            if pred not in VALID_PREDICATES:
                item_results.append(('invalid_predicate', pred))
            stats['predicate_usage'][pred] += 1
            # Check subject/object
            id_errors = validate_relation_ids(obj, declared_entities)
            for reason, detail in id_errors:
                item_results.append((reason, detail))

        elif obj_type == 'entity':
            id_errors = validate_entity_ids(obj, declared_entities)
            for reason, detail in id_errors:
                item_results.append((reason, detail))
            # Check attribute keys
            for attr in obj.get('attributes', []):
                k = attr.get('key', '')
                stats['total_attr_keys'] += 1
                if not k:
                    item_results.append(('attribute_key_empty', str(attr)[:80]))
                elif k.startswith('x:'):
                    stats['custom_attr_keys'] += 1
                elif k not in VALID_ATTR_KEYS:
                    item_results.append(('invalid_attribute_key', k))

        elif obj_type == 'discrepancy':
            # Check contradiction has >= 2 statements
            if obj.get('kind') == 'contradiction' and len(obj.get('statements', [])) < 2:
                item_results.append(('contradiction_needs_2_statements', f'has {len(obj.get("statements", []))}'))
            # Check analysis.claim_type is interpretation
            analysis = obj.get('analysis', {})
            if analysis.get('claim_type') != 'interpretation':
                item_results.append(('analysis_not_interpretation', analysis.get('claim_type', '')))

        elif obj_type == 'merge_record':
            rationale = obj.get('rationale', {})
            if rationale.get('claim_type') != 'interpretation':
                item_results.append(('rationale_not_interpretation', rationale.get('claim_type', '')))

        # Check source_volume
        sv = obj.get('source_volume', '')
        if sv and sv not in VOLUMES:
            item_results.append(('invalid_source_volume', sv))
        if obj_type == 'entity':
            if 'entity_id' in obj and not re.match(r'^(AEON|PATH|CHAR|ORGN|PLAC|WRLD|CONC|ARTF|RACE):.+$', obj.get('entity_id', '')):
                item_results.append(('invalid_entity_id', obj.get('entity_id', '')))
        elif obj_type == 'relation':
            if 'relation_id' in obj and not re.match(r'^REL:[a-f0-9]{12}$', obj.get('relation_id', '')):
                item_results.append(('invalid_relation_id', obj.get('relation_id', '')))
        elif obj_type == 'event':
            if 'event_id' in obj and not re.match(r'^EVT:.+$', obj.get('event_id', '')):
                item_results.append(('invalid_event_id', obj.get('event_id', '')))
        elif obj_type == 'discrepancy':
            if 'discrepancy_id' in obj and not re.match(r'^DSC:[a-f0-9]{12}$', obj.get('discrepancy_id', '')):
                item_results.append(('invalid_discrepancy_id', obj.get('discrepancy_id', '')))
        elif obj_type == 'merge_record':
            if 'merge_id' in obj and not re.match(r'^MRG:[a-f0-9]{12}$', obj.get('merge_id', '')):
                item_results.append(('invalid_merge_id', obj.get('merge_id', '')))

        if item_results:
            result = {'status': 'REJECTED', 'index': i, 'type': obj_type, 'errors': [{'reason': r, 'detail': d} for r, d in item_results]}
            stats['rejected'] += 1
            for r, d in item_results:
                stats['by_reason'][r] += 1
        else:
            result = {'status': 'ACCEPTED', 'index': i, 'type': obj_type}
            stats['accepted'] += 1

        results.append(result)

    # Cycle detection on events
    events = [o for o in objects if 'event_id' in o]
    cycles = validate_cycle_detection(events)
    if cycles:
        stats['cycle_events'] = cycles

    # RELATED_TO ratio
    total_relations = sum(stats['predicate_usage'].values())
    related_to_count = stats['predicate_usage'].get('RELATED_TO', 0)
    stats['related_to_ratio'] = related_to_count / total_relations if total_relations > 0 else 0.0

    # Custom attribute key ratio
    stats['custom_attr_ratio'] = stats['custom_attr_keys'] / stats['total_attr_keys'] if stats['total_attr_keys'] > 0 else 0.0

    return results, stats

# ── Report generation ───────────────────────────────────────────

def print_report(results, stats, label=''):
    print(f'\n{"="*60}')
    print(f'VALIDATION REPORT {label}')
    print(f'{"="*60}')
    print(f'Total: {stats["total"]}')
    print(f'Accepted: {stats["accepted"]} ({stats["accepted"]/stats["total"]*100:.1f}%)' if stats['total'] > 0 else 'Accepted: 0')
    print(f'Rejected: {stats["rejected"]} ({stats["rejected"]/stats["total"]*100:.1f}%)' if stats['total'] > 0 else 'Rejected: 0')

    print(f'\nBy type:')
    for typ, cnt in sorted(stats['by_type'].items()):
        print(f'  {typ}: {cnt}')

    print(f'\nRejection reasons:')
    for reason, cnt in sorted(stats['by_reason'].items(), key=lambda x: -x[1]):
        print(f'  [{cnt:3d}] {reason}')

    if stats['predicate_usage']:
        print(f'\nPredicate usage:')
        for pred, cnt in sorted(stats['predicate_usage'].items(), key=lambda x: -x[1]):
            print(f'  {pred}: {cnt}')
        if stats['related_to_ratio'] > 0:
            print(f'  RELATED_TO ratio: {stats["related_to_ratio"]*100:.1f}%')
            if stats['related_to_ratio'] > 0.1:
                print(f'  ⚠ WARNING: RELATED_TO exceeds 10% threshold!')

    if stats['total_attr_keys'] > 0:
        print(f'\nAttribute keys: {stats["total_attr_keys"]} total, {stats["custom_attr_keys"]} custom (x: {stats["custom_attr_ratio"]*100:.1f}%)')
        if stats['custom_attr_ratio'] > ATTR_CUSTOM_THRESHOLD:
            print(f'  WARNING: custom x: keys exceed {ATTR_CUSTOM_THRESHOLD*100:.0f}% threshold!')

    if stats['cycle_events']:
        print(f'\n⚠ Cycle detected in event relative_to:')
        for eid in stats['cycle_events']:
            print(f'  {eid}')

    # Print rejected items (first 5 per reason)
    print(f'\nRejected items (first 5 per reason):')
    shown = defaultdict(int)
    for r in results:
        if r['status'] == 'REJECTED':
            for err in r['errors']:
                reason = err['reason']
                if shown[reason] < 5:
                    print(f'  [{r["index"]}] {r["type"]}: {reason} — {err["detail"]}')
                    shown[reason] += 1

# ── CLI ─────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='HSR Lore Validator')
    parser.add_argument('inputs', nargs='*', help='JSONL files to validate')
    parser.add_argument('--dir', help='Directory of JSONL files to validate')
    parser.add_argument('--all', action='store_true', help='Validate all files in tests/fixtures/')
    parser.add_argument('--cite-whitelist', help='Path to block-level cite whitelist JSON file '
                        '(overrides global cite_whitelist.txt; enables cite_id_out_of_scope rejection)')
    args = parser.parse_args()

    # Load block-level whitelist if provided
    if args.cite_whitelist:
        whitelist_path = Path(args.cite_whitelist)
        if whitelist_path.exists():
            with open(whitelist_path, 'r', encoding='utf-8') as f:
                block_wl = json.load(f)
            if isinstance(block_wl, list):
                cite_whitelist = set(block_wl)
            elif isinstance(block_wl, dict):
                cite_whitelist = set(block_wl.get('cite_ids', block_wl.get('whitelist', [])))
            block_whitelist_mode = True
            print(f'Block-level whitelist: {len(cite_whitelist)} allowed cite_ids '
                  f'(cite_id_out_of_scope enabled)')
        else:
            print(f'WARNING: whitelist file not found: {args.cite_whitelist}')

    if args.all:
        args.inputs = sorted(glob.glob(str(BASE / 'tests/fixtures/valid/*.json')))
        args.inputs += sorted(glob.glob(str(BASE / 'tests/fixtures/invalid/*.json')))

    if args.dir:
        args.inputs = sorted(glob.glob(os.path.join(args.dir, '*.json')))

    if not args.inputs:
        print('Usage: python validate.py <file.jsonl ...>')
        print('       python validate.py --dir tests/fixtures/valid/')
        print('       python validate.py --all')
        sys.exit(1)

    all_objects = []
    parse_status = {'direct': 0, 'fixed': 0, 'unparseable': 0}
    unparseable_lines = []
    chunk_id = ''

    for fpath in args.inputs:
        # Extract chunk_id from filename (e.g., T123_combined_C001_backfilled.jsonl → C001)
        fname = os.path.basename(fpath)
        chunk_id = fname.split('_')[-1].replace('.jsonl', '').replace('_backfilled', '')

        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content.startswith('['):
                objs = json.loads(content)
                parse_status['direct'] += len(objs)
                all_objects.extend(objs)
                print(f'Loaded {len(objs)} objects from {fname} (JSON array)')
            else:
                for line in content.split('\n'):
                    if not line.strip():
                        continue
                    obj, status = tolerant_json_parse(line)
                    if status == 'unparseable':
                        parse_status['unparseable'] += 1
                        unparseable_lines.append(line.strip())
                    else:
                        parse_status[status] += 1
                        all_objects.append(obj)
                loaded = parse_status['direct'] + parse_status['fixed']
                print(f'Loaded {loaded} objects from {fname} '
                      f'(direct={parse_status["direct"]}, fixed={parse_status["fixed"]}, '
                      f'unparseable={parse_status["unparseable"]})')

    # Save unparseable lines
    if unparseable_lines and chunk_id:
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        unparse_path = DEBUG_DIR / f'{chunk_id}_unparsed.jsonl'
        with open(unparse_path, 'w', encoding='utf-8') as f:
            for line in unparseable_lines:
                f.write(line + '\n')
        print(f'  Unparseable lines saved to {unparse_path}')

    results, stats = validate_objects(all_objects, chunk_id)
    # Add parse status to stats
    stats['parse_status'] = parse_status
    parse_total = sum(parse_status.values())
    stats['format_compliance'] = round((parse_status['direct'] + parse_status['fixed']) / max(parse_total, 1), 3)
    # Add predicate mapping stats
    if PREDICATE_MAPPING_LOG:
        stats['predicate_mapped'] = len(PREDICATE_MAPPING_LOG)
        stats['predicate_mapping_details'] = PREDICATE_MAPPING_LOG[:]
    flush_predicate_log()
    print_report(results, stats, '')