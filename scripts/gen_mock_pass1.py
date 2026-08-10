"""
B1: Mock pass1 产出生成器
生成结构完全真实、内容虚构的 pass1 产出，用于 pass2 基础设施开发与验证。
覆盖全部 8 个卷，每卷 entities/relations/events/discrepancies 四类文件。
"""
import json
import sys
import io
import random
import hashlib
from pathlib import Path
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(__file__).parent.parent
WORK = BASE / 'work'
FIXTURES = BASE / 'tests' / 'fixtures' / 'mock_pass1'

# ── Volume configuration ──────────────────────────────────────────

VOLUMES = ['lore', 'books', 'characters', 'narrative', 'dialogue', 'artifacts', 'rogue', 'unattributed']

# Target entity counts per volume (total 800-1500)
VOLUME_ENTITY_TARGETS = {
    'lore': 200, 'books': 120, 'characters': 250, 'narrative': 200,
    'dialogue': 80, 'artifacts': 80, 'rogue': 70, 'unattributed': 100,
}

# Entity type distribution
ENTITY_TYPES = ['CHAR', 'AEON', 'PATH', 'ORGN', 'PLAC', 'WRLD', 'CONC', 'ARTF', 'RACE']
ENTITY_TYPE_WEIGHTS = [0.30, 0.03, 0.05, 0.12, 0.10, 0.10, 0.15, 0.08, 0.07]

# Predicates
PREDICATES = [
    'EMBODIES', 'EMISSARY_OF', 'FOLLOWER_OF', 'OPPOSES',
    'MEMBER_OF', 'LEADS', 'MENTOR_OF', 'KIN_OF', 'ALLY_OF',
    'ENEMY_OF', 'SUCCEEDS', 'CREATED', 'KILLED', 'TRANSFORMED_INTO',
    'LOCATED_IN', 'ORIGINATES_FROM', 'RULES',
    'PARTICIPATED_IN', 'CAUSED', 'RESULTED_IN',
    'RELATED_TO',
]

# Cross-volume entity names (these will appear in multiple volumes)
CROSS_VOLUME_ENTITIES = [
    {'canonical_name': '三月七', 'type': 'CHAR', 'volumes': ['characters', 'narrative', 'dialogue']},
    {'canonical_name': '丹恒', 'type': 'CHAR', 'volumes': ['characters', 'narrative', 'dialogue']},
    {'canonical_name': '开拓者', 'type': 'CHAR', 'volumes': ['characters', 'narrative', 'dialogue']},
    {'canonical_name': '姬子', 'type': 'CHAR', 'volumes': ['characters', 'narrative', 'dialogue']},
    {'canonical_name': '瓦尔特', 'type': 'CHAR', 'volumes': ['characters', 'narrative']},
    {'canonical_name': '景元', 'type': 'CHAR', 'volumes': ['characters', 'narrative', 'dialogue']},
    {'canonical_name': '星穹列车', 'type': 'ORGN', 'volumes': ['lore', 'narrative', 'dialogue']},
    {'canonical_name': '星核猎手', 'type': 'ORGN', 'volumes': ['lore', 'characters', 'narrative']},
    {'canonical_name': '贝洛伯格', 'type': 'PLAC', 'volumes': ['lore', 'narrative']},
    {'canonical_name': '仙舟罗浮', 'type': 'PLAC', 'volumes': ['lore', 'narrative', 'characters']},
    {'canonical_name': '星核', 'type': 'CONC', 'volumes': ['lore', 'narrative', 'dialogue']},
    {'canonical_name': '存护', 'type': 'PATH', 'volumes': ['lore', 'narrative']},
]

# Alias relationships
ALIAS_ENTITIES = [
    {'canonical_name': '丹恒', 'alias': '丹恒•饮月', 'volume': 'characters'},
    {'canonical_name': '开拓者', 'alias': '{NICKNAME}', 'volume': 'dialogue'},
    {'canonical_name': '星核猎手', 'alias': 'Stellaron Hunters', 'volume': 'lore'},
    {'canonical_name': '贝洛伯格', 'alias': '雅利洛-VI', 'volume': 'lore'},
    {'canonical_name': '仙舟罗浮', 'alias': '罗浮', 'volume': 'characters'},
]

# ── Load cite_index ──────────────────────────────────────────────

def load_cite_index():
    idx = {}
    path = WORK / 'cite_index.jsonl'
    if not path.exists():
        print("WARNING: cite_index.jsonl not found")
        return idx
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            idx[rec['cite_id']] = rec
    return idx


def make_citation(cite_id, clean_text):
    """Create a valid citation with real quote from clean text."""
    if not clean_text:
        return None
    # Take first 30-80 chars as quote
    end = min(random.randint(30, 80), len(clean_text))
    quote = clean_text[:end]
    return {'cite_id': cite_id, 'quote': quote}


# ── Entity generators ────────────────────────────────────────────

def generate_entity(entity_type, name, volume, cite_ids_pool):
    """Generate a single entity object."""
    cite = random.choice(cite_ids_pool) if cite_ids_pool else None
    eid = f"{entity_type}:{name}"
    return {
        'entity_id': eid,
        'type': entity_type,
        'canonical_name': name,
        'aliases': [],
        'summary': {
            'text': f'{name}是《崩坏：星穹铁道》世界观中的一个{entity_type}型实体。',
            'claim_type': 'fact',
            'confidence': 'attested',
            'citations': [make_citation(cite['cite_id'], cite['clean'])] if cite else [],
        },
        'attributes': [
            {
                'key': '身份',
                'value': f'{name}的基本信息',
                'claim_type': 'fact',
                'confidence': 'attested',
                'citations': [make_citation(cite['cite_id'], cite['clean'])] if cite else [],
            }
        ],
        'source_volume': volume,
    }


def generate_relation(subj_name, predicate, obj_name, volume, cite_ids_pool):
    """Generate a single relation object."""
    cite = random.choice(cite_ids_pool) if cite_ids_pool else None
    rid_hash = hashlib.sha256(f"{subj_name}{predicate}{obj_name}{volume}".encode()).hexdigest()[:12]
    return {
        'relation_id': f'REL:{rid_hash}',
        'subject_name': subj_name,
        'predicate': predicate,
        'object_name': obj_name,
        'qualifiers': {},
        'claim_type': 'fact',
        'confidence': 'attested',
        'citations': [make_citation(cite['cite_id'], cite['clean'])] if cite else [],
        'source_volume': volume,
    }


def generate_event(name, volume, participants, cite_ids_pool):
    """Generate a single event object."""
    cite = random.choice(cite_ids_pool) if cite_ids_pool else None
    eid_hash = hashlib.sha256(f"{name}{volume}".encode()).hexdigest()[:8]
    return {
        'event_id': f'EVT:{volume}-{eid_hash}',
        'name': name,
        'summary': {
            'text': f'{name}事件发生于{volume}卷。',
            'claim_type': 'fact',
            'confidence': 'attested',
            'citations': [make_citation(cite['cite_id'], cite['clean'])] if cite else [],
        },
        'participants': participants,
        'locations': [f'{volume}-地点'],
        'stated_time': random.choice(['琥珀纪2157年', '第三纪元', '寒潮之前', '']),
        'relative_to': [],
        'order_hint': random.randint(0, 100),
        'confidence': 'attested',
        'citations': [make_citation(cite['cite_id'], cite['clean'])] if cite else [],
    }


def generate_discrepancy(kind, topic, volume, cite_ids_pool):
    """Generate a single discrepancy object."""
    c1 = random.choice(cite_ids_pool) if cite_ids_pool else None
    c2 = random.choice(cite_ids_pool) if cite_ids_pool else None
    c3 = random.choice(cite_ids_pool) if cite_ids_pool else None
    did_hash = hashlib.sha256(f"{topic}{volume}".encode()).hexdigest()[:12]
    return {
        'discrepancy_id': f'DSC:{did_hash}',
        'kind': kind,
        'topic': topic,
        'statements': [
            {
                'text': f'关于{topic}的陈述A',
                'citation': make_citation(c1['cite_id'], c1['clean']) if c1 else {},
            },
            {
                'text': f'关于{topic}的陈述B',
                'citation': make_citation(c2['cite_id'], c2['clean']) if c2 else {},
            },
        ],
        'analysis': {
            'text': f'对{topic}矛盾的分析。',
            'claim_type': 'interpretation',
            'confidence': 'inferred',
            'citations': [make_citation(c3['cite_id'], c3['clean'])] if c3 else [],
        },
        'related_entities': [],
        'impact': random.choice(['low', 'medium', 'high']),
    }


# ── Main generator ───────────────────────────────────────────────

def main():
    print("B1: Generating mock pass1 output...")
    print()

    cite_index = load_cite_index()
    if not cite_index:
        print("ERROR: cite_index.jsonl is required for mock generation")
        return 1

    cite_ids = list(cite_index.keys())
    print(f"Loaded {len(cite_ids)} cite_ids from index")

    # Pre-allocate cite_ids per volume for locality
    volume_cites = defaultdict(list)
    for cid, rec in cite_index.items():
        vol = rec.get('volume', 'unattributed')
        volume_cites[vol].append({'cite_id': cid, 'clean': rec['clean']})

    # Ensure every volume has some cites (borrow from others if empty)
    all_cites_list = [{'cite_id': cid, 'clean': cite_index[cid]['clean']} for cid in cite_ids[:5000]]
    for vol in VOLUMES:
        if not volume_cites.get(vol):
            volume_cites[vol] = all_cites_list[:100]

    random.seed(42)  # Deterministic output

    total_entities = 0
    total_relations = 0
    total_events = 0
    total_discrepancies = 0

    for volume in VOLUMES:
        vdir = FIXTURES / volume
        vdir.mkdir(parents=True, exist_ok=True)

        cites = volume_cites.get(volume, all_cites_list[:100])
        n_entities_target = VOLUME_ENTITY_TARGETS.get(volume, 30)

        # ── Entities ──
        entities = []

        # Add cross-volume entities that belong to this volume
        for cv_ent in CROSS_VOLUME_ENTITIES:
            if volume in cv_ent['volumes']:
                ent = generate_entity(cv_ent['type'], cv_ent['canonical_name'], volume, cites)
                # Add aliases
                for alias_info in ALIAS_ENTITIES:
                    if alias_info['canonical_name'] == cv_ent['canonical_name'] and alias_info['volume'] == volume:
                        if alias_info['alias'] not in ent['aliases']:
                            ent['aliases'].append(alias_info['alias'])
                entities.append(ent)

        # Generate remaining entities
        remaining = n_entities_target - len(entities)
        entity_names_used = {e['canonical_name'] for e in entities}
        for i in range(max(0, remaining)):
            etype = random.choices(ENTITY_TYPES, weights=ENTITY_TYPE_WEIGHTS, k=1)[0]
            name = f'{volume}-{etype}-实体-{i}'
            while name in entity_names_used:
                name = f'{volume}-{etype}-实体-{i}-{random.randint(0, 999)}'
            entity_names_used.add(name)
            entities.append(generate_entity(etype, name, volume, cites))

        # ── Relations ──
        relations = []
        n_relations = random.randint(max(5, n_entities_target // 3), max(8, n_entities_target // 2))
        entity_names = [e['canonical_name'] for e in entities]
        for i in range(n_relations):
            if len(entity_names) >= 2:
                s = random.choice(entity_names)
                o = random.choice([n for n in entity_names if n != s])
                p = random.choice(PREDICATES)
                relations.append(generate_relation(s, p, o, volume, cites))

        # ── Events ──
        events = []
        n_events = random.randint(3, 12)
        if volume in ['dialogue', 'artifacts', 'rogue']:
            n_events = random.randint(1, 3)
        for i in range(n_events):
            evt_name = f'{volume}-事件-{i}'
            participants = random.sample(entity_names, min(3, len(entity_names)))
            evt = generate_event(evt_name, volume, participants, cites)

            # Cross-volume temporal clues: add relative_to for related events
            if i > 0:
                evt['relative_to'].append({
                    'relation': 'after',
                    'event_name': f'{volume}-事件-{i - 1}',
                })
            events.append(evt)

        # ── Discrepancies ──
        discrepancies = []
        n_discrepancies = random.randint(1, 4)
        discrepancy_kinds = ['contradiction', 'ambiguity', 'gap', 'retcon']
        for i in range(n_discrepancies):
            kind = random.choice(discrepancy_kinds)
            topic = f'{volume}-矛盾-{i}'
            d = generate_discrepancy(kind, topic, volume, cites)
            d['related_entities'] = random.sample(entity_names, min(2, len(entity_names)))
            discrepancies.append(d)

        # ── Write files ──
        def write_jsonl(path, objects):
            with open(path, 'w', encoding='utf-8') as f:
                for obj in objects:
                    f.write(json.dumps(obj, ensure_ascii=False) + '\n')

        write_jsonl(vdir / 'entities.jsonl', entities)
        write_jsonl(vdir / 'relations.jsonl', relations)
        write_jsonl(vdir / 'events.jsonl', events)
        write_jsonl(vdir / 'discrepancies.jsonl', discrepancies)

        total_entities += len(entities)
        total_relations += len(relations)
        total_events += len(events)
        total_discrepancies += len(discrepancies)

        print(f"  {volume:>15s}: {len(entities):>4d} entities, {len(relations):>3d} relations, "
              f"{len(events):>2d} events, {len(discrepancies):>2d} discrepancies")

    print()
    print("=" * 60)
    print(f"Mock pass1 complete:")
    print(f"  Total entities:     {total_entities}")
    print(f"  Total relations:    {total_relations}")
    print(f"  Total events:       {total_events}")
    print(f"  Total discrepancies: {total_discrepancies}")
    print(f"  Cross-volume entities: {len(CROSS_VOLUME_ENTITIES)}")
    print(f"  Alias relationships:   {len(ALIAS_ENTITIES)}")
    print(f"\n  Output: {FIXTURES}")


if __name__ == '__main__':
    main()
