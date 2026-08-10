"""
C2: 站点数据构建器
读 output/pass1/ 与 output/pass2/，按 C1 数据契约生成 site/public/data/*.json。
pass2 缺失时只用 pass1 数据生成完整可用数据集。
"""
import json
import sys
import io
import re
from pathlib import Path
from collections import defaultdict, Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(__file__).parent.parent
OUTPUT = BASE / 'output'
SITE_DATA = BASE / 'site' / 'public' / 'data'

VOLUMES = ['lore', 'books', 'characters', 'narrative', 'dialogue', 'artifacts', 'rogue', 'unattributed']
OBJECT_TYPES = ['entities', 'relations', 'events', 'discrepancies']


def read_jsonl(path):
    """Read a JSONL file, return list of objects."""
    objects = []
    if not path.exists():
        return objects
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    objects.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return objects


def collect_from_pass1(pass1_dir):
    """Collect all pass1 objects per volume and type."""
    data = {t: [] for t in OBJECT_TYPES}
    for vol in VOLUMES:
        vdir = pass1_dir / vol
        if not vdir.is_dir():
            continue
        for obj_type in OBJECT_TYPES:
            fpath = vdir / f'{obj_type}.jsonl'
            if fpath.exists():
                objs = read_jsonl(fpath)
                data[obj_type].extend(objs)
    return data


def collect_from_pass2(pass2_dir):
    """Collect pass2 merged entities and cross-volume data."""
    data = {'entities': [], 'relations': [], 'events': [], 'discrepancies': [],
            'merge_records': []}

    # Look for pass2 output files
    if not pass2_dir.is_dir():
        return data

    for fpath in sorted(pass2_dir.glob('*.jsonl')):
        objs = read_jsonl(fpath)
        for obj in objs:
            if 'merge_id' in obj:
                data['merge_records'].append(obj)
            elif 'merged_entity_id' in obj:
                data['entities'].append(obj)
            elif 'entity_id' in obj:
                data['entities'].append(obj)
            elif 'relation_id' in obj:
                data['relations'].append(obj)
            elif 'event_id' in obj:
                data['events'].append(obj)
            elif 'discrepancy_id' in obj:
                data['discrepancies'].append(obj)

    # Also look in subdirectories
    for subdir in pass2_dir.iterdir():
        if subdir.is_dir():
            for fpath in sorted(subdir.glob('*.jsonl')):
                objs = read_jsonl(fpath)
                for obj in objs:
                    if 'merge_id' in obj:
                        data['merge_records'].append(obj)
                    elif 'entity_id' in obj:
                        data['entities'].append(obj)
                    elif 'relation_id' in obj:
                        data['relations'].append(obj)
                    elif 'event_id' in obj:
                        data['events'].append(obj)
                    elif 'discrepancy_id' in obj:
                        data['discrepancies'].append(obj)

    return data


def build_entities_with_merges(pass1_entities, pass2_entities, merge_records):
    """Merge pass1 and pass2 entities, applying merge records.

    Returns list of entities with _merged, _merge_ids, _source_volumes annotations.
    """
    # Build name → entities map
    entities = list(pass1_entities)

    # Track merge info
    merge_map = {}  # entity_id → merged_entity_id
    for mr in merge_records:
        merged_id = mr.get('merged_entity_id', '')
        for src_id in mr.get('source_entity_ids', []):
            merge_map[src_id] = merged_id

    merged_entities = {}
    for ent in pass2_entities:
        eid = ent.get('entity_id', '')
        merged_entities[eid] = ent

    # Annotate pass1 entities
    result = []
    seen_ids = set()
    seen_names = set()  # fallback dedup: type+name+volume

    for ent in entities:
        eid = ent.get('entity_id', '')
        # Generate fallback ID if model didn't output one
        if not eid:
            name_key = (ent.get('type',''), ent.get('canonical_name',''), ent.get('source_volume',''))
            # Skip true duplicates (same type+name+volume)
            if name_key in seen_names:
                continue
            seen_names.add(name_key)
            eid = f"{ent.get('type','')}:{ent.get('canonical_name','')}:{ent.get('source_volume','')}"
        else:
            if eid in seen_ids:
                continue
        seen_ids.add(eid)

        ent['_merged'] = eid in merge_map
        ent['_merge_ids'] = [eid]
        ent['_source_volumes'] = [ent.get('source_volume', '')]

        # If merged, add merge info
        if eid in merge_map:
            ent['_merge_ids'].append(merge_map[eid])
            if merge_map[eid] in merged_entities:
                merged = merged_entities[merge_map[eid]]
                ent['_merged'] = True
                ent['canonical_name'] = merged.get('canonical_name', ent.get('canonical_name', ''))

        result.append(ent)

    # Add pass2 entities not in pass1
    for eid, ent in merged_entities.items():
        if eid not in seen_ids:
            ent['_merged'] = True
            ent['_merge_ids'] = [eid]
            ent['_source_volumes'] = ['_pass2']
            result.append(ent)

    return result


def build_relations(pass1_relations, pass2_relations):
    """Combine pass1 and pass2 relations."""
    seen = set()
    result = []
    for rel in pass1_relations + pass2_relations:
        rid = rel.get('relation_id', '')
        if not rid:
            # Generate fallback key
            rid = f"{rel.get('subject_name','')}:{rel.get('predicate','')}:{rel.get('object_name','')}:{rel.get('source_volume','')}"
        if rid and rid not in seen:
            seen.add(rid)
            result.append(rel)
    return result


def build_events(pass1_events, pass2_events):
    """Combine events. Annotate with _timeline_inferred."""
    event_map = {}
    result = []
    seen_keys = set()
    for evt in pass1_events:
        eid = evt.get('event_id', '')
        if not eid:
            eid = f"{evt.get('name','')}:{evt.get('source_volume','')}"
        if eid in seen_keys:
            continue
        seen_keys.add(eid)
        evt['_timeline_inferred'] = True  # Default: pass2 missing → inferred
        event_map[eid] = evt
        result.append(evt)

    # T7 pass2 events may have relative_to additions
    for evt in pass2_events:
        eid = evt.get('event_id', '')
        name = evt.get('event_name', '') or evt.get('name', '')
        if eid and eid in event_map:
            # Merge relative_to from pass2
            existing = event_map[eid]
            existing_rels = existing.get('relative_to', [])
            new_rels = evt.get('relative_to', [])
            existing_rel_names = {(r.get('event_id', ''), r.get('relation', '')) for r in existing_rels}
            for rel in new_rels:
                key = (rel.get('event_id', ''), rel.get('relation', ''))
                if key not in existing_rel_names:
                    existing_rels.append(rel)
            existing['_timeline_inferred'] = False  # T7 provided this
        elif name:
            # New timeline relation from T7
            evt['_timeline_inferred'] = False
            result.append(evt)

    return result


def build_discrepancies(pass1_discrepancies, pass2_discrepancies):
    """Combine discrepancies. Annotate with _cross_volume."""
    result = []
    for d in pass1_discrepancies:
        d['_cross_volume'] = False
        result.append(d)
    for d in pass2_discrepancies:
        d['_cross_volume'] = True
        result.append(d)
    return result


def build_citations(all_objects, cite_index_path):
    """Build a quote-only citation index.

    Returns [{cite_id, quote, volume}] — only the cite_ids actually referenced
    by entities/relations/events/discrepancies, carrying the quoted excerpt used,
    never the full cleaned corpus text.
    """
    cited_ids = set()
    quotes_map = defaultdict(set)

    def extract(obj):
        if isinstance(obj, dict):
            cid = obj.get('cite_id')
            if isinstance(cid, str) and cid:
                cited_ids.add(cid)
                q = obj.get('quote')
                if isinstance(q, str) and q:
                    quotes_map[cid].add(q)
            for v in obj.values():
                extract(v)
        elif isinstance(obj, list):
            for item in obj:
                extract(item)

    for obj in all_objects:
        extract(obj)

    # Resolve volume from the index; entry text is the quoted excerpt only.
    entries = []
    cite_index_path = Path(cite_index_path)
    if cite_index_path.exists():
        with open(cite_index_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                cid = rec.get('cite_id')
                if cid in cited_ids:
                    quotes = sorted(quotes_map.get(cid, ()), key=len, reverse=True)
                    quote = quotes[0][:500] if quotes else ''
                    entries.append({
                        'cite_id': cid,
                        'quote': quote,
                        'volume': rec.get('volume', ''),
                    })
    else:
        for cid in sorted(cited_ids):
            quotes = sorted(quotes_map.get(cid, ()), key=len, reverse=True)
            entries.append({
                'cite_id': cid,
                'quote': quotes[0][:500] if quotes else '',
                'volume': '',
            })

    entries.sort(key=lambda e: e['cite_id'])
    return entries


# ── 内容质量过滤 ────────────────────────────────────────────────

# 判据 1: 内部 ID 出现在文本中（扩展版，覆盖多种泄漏形态）
#   xxx-实体-N、xxx-矛盾-N、xxx-事件-N    （现有 mock 格式）
#   TYPE:名称 如 CHAR:三月七、ORGN:星穹列车  （entity_id 格式）
#   TYPE-数字 如 AEON-5、CHAR-1             （简写 ID 格式）
#   xxx_NAME-N、xxx_name_N 等下划线形式     （snake_case ID）
RE_INTERNAL_ID = re.compile(
    r'\b\w+[-:]\w*[-:]?(?:实体|矛盾|事件|CHAR|AEON|PATH|ORGN|PLAC|WRLD|CONC|ARTF|RACE)[-_:]?\d*\b'
    r'|\b[a-z]+_[A-Z]+_\d+\b'  # snake_case identifiers like lore_CHAR_146
    r'|\b(?:CHAR|AEON|PATH|ORGN|PLAC|WRLD|CONC|ARTF|RACE)[:-]\d+\b'  # type:number only (not any 2-6 letter acronym)
)

# 判据 2: 模板句式（保持精确匹配，避免误伤自然语言）
RE_TEMPLATE = re.compile(r'是《崩坏：星穹铁道》世界观中的一个\S{1,4}型实体')

# 判据 3: subject_name / object_name 为内部 ID
def _is_id_name(name):
    if not isinstance(name, str) or not name:
        return False
    # 匹配形如 lore-PLAC-实体-146, narrative-CHAR-实体-66 等
    return bool(RE_INTERNAL_ID.search(name))


QUALITY_RULES = [
    'text_contains_internal_id',     # 结论文本含内部 ID
    'template_sentence',             # 模板句式
    'name_is_internal_id',           # 关系端点名称是 ID
    'text_too_short',                # summary/analysis < 10 字
    'empty_or_id_attribute',         # attribute value 为空/ID/与 key 相同
]


def quality_filter(data, filter_log_path, mode='filter'):
    """Apply content quality rules.

    mode='filter': remove bad entries, write filter log.
    mode='audit': only collect stats + samples, do NOT remove entries.
    Returns (filtered_data, stats, audit_samples).
    """
    filtered_out = []
    audit_samples = {rule: [] for rule in QUALITY_RULES}  # up to 20 samples per rule
    stats = {rule: 0 for rule in QUALITY_RULES}
    stats['total_filtered'] = 0

    # ── 判据函数 ──
    def check_text_for_internal_id(obj):
        """Check summary.text, statements[].text, topic, analysis.text etc."""
        fields_to_check = []
        # summary
        if isinstance(obj.get('summary'), dict):
            fields_to_check.append(obj['summary'].get('text', ''))
        # statements
        for s in (obj.get('statements') or []):
            fields_to_check.append(s.get('text', ''))
        # analysis
        if isinstance(obj.get('analysis'), dict):
            fields_to_check.append(obj['analysis'].get('text', ''))
        # name fields
        for f in ('name', 'canonical_name', 'topic'):
            if isinstance(obj.get(f), str):
                fields_to_check.append(obj[f])
        # event/entity: description-like fields
        for f in ('description',):
            if isinstance(obj.get(f), str):
                fields_to_check.append(obj[f])
        for text in fields_to_check:
            if text and RE_INTERNAL_ID.search(str(text)):
                return True
        return False

    def check_template_sentence(obj):
        """Check for template boilerplate like 'X是《崩坏：星穹铁道》世界观中的一个Y型实体'"""
        if isinstance(obj.get('summary'), dict):
            t = obj['summary'].get('text', '')
            if t and RE_TEMPLATE.search(str(t)):
                return True
        for s in (obj.get('statements') or []):
            if s.get('text') and RE_TEMPLATE.search(str(s['text'])):
                return True
        return False

    def check_relation_names(obj):
        """Check if subject_name / object_name are internal IDs"""
        return _is_id_name(obj.get('subject_name')) or _is_id_name(obj.get('object_name'))

    def check_text_length(obj):
        """summary.text or analysis.text shorter than 10 characters"""
        if isinstance(obj.get('summary'), dict):
            t = obj['summary'].get('text', '')
            if t and len(str(t).strip()) < 10:
                return True
        if isinstance(obj.get('analysis'), dict):
            t = obj['analysis'].get('text', '')
            if t and len(str(t).strip()) < 10:
                return True
        return False

    def check_attribute_quality(obj):
        """attribute value is empty, is internal ID, or equals key"""
        for attr in (obj.get('attributes') or []):
            v = attr.get('value', '')
            k = attr.get('key', '')
            if not v or not str(v).strip():
                return True
            if _is_id_name(str(v)):
                return True
            if k and v == k:
                return True
        return False

    # ── 对各类条目执行判据 ──
    def filter_category(entries, category):
        keep = []
        for ent in entries:
            reasons = []

            # Rule 1: ID in text (applies to all)
            if category in ('entities', 'events', 'discrepancies'):
                if check_text_for_internal_id(ent):
                    reasons.append('text_contains_internal_id')

            # Rule 2: template sentence (applies to entities, events, discrepancies)
            if category in ('entities', 'events', 'discrepancies'):
                if check_template_sentence(ent):
                    reasons.append('template_sentence')

            # Rule 3: ID names (applies to relations)
            if category == 'relations':
                if check_relation_names(ent):
                    reasons.append('name_is_internal_id')

            # Rule 4: short text (applies to all)
            if check_text_length(ent):
                reasons.append('text_too_short')

            # Rule 5: attribute quality (applies to entities)
            if category == 'entities':
                if check_attribute_quality(ent):
                    reasons.append('empty_or_id_attribute')

            if reasons:
                rec = {
                    'category': category,
                    'entity_id': ent.get('entity_id') or ent.get('relation_id') or ent.get('event_id') or ent.get('discrepancy_id') or ent.get('topic', ''),
                    'reasons': reasons,
                }
                # Include a snippet for auditing
                if ent.get('summary'):
                    rec['text_snippet'] = str(ent['summary'].get('text', ''))[:120]
                elif ent.get('analysis'):
                    rec['text_snippet'] = str(ent['analysis'].get('text', ''))[:120]
                elif ent.get('canonical_name'):
                    rec['text_snippet'] = str(ent.get('canonical_name', ''))
                filtered_out.append(rec)
                for r in reasons:
                    stats[r] = stats.get(r, 0) + 1
                    if len(audit_samples[r]) < 20:
                        audit_samples[r].append({
                            'category': category, 'entity_id': rec['entity_id'],
                            'text_snippet': rec.get('text_snippet', ''),
                            'full_summary': str(ent.get('summary', {}).get('text', '') or ent.get('analysis', {}).get('text', '') or ent.get('canonical_name', ''))[:300],
                        })
                stats['total_filtered'] += 1
            else:
                keep.append(ent)
        return keep

    # Apply filtering per category
    result = {}
    result['entities'] = filter_category(data.get('entities', []), 'entities')
    result['relations'] = filter_category(data.get('relations', []), 'relations')
    result['events'] = filter_category(data.get('events', []), 'events')
    result['discrepancies'] = filter_category(data.get('discrepancies', []), 'discrepancies')

    # Write filtered-out log (filter mode only)
    if mode == 'filter' and filter_log_path and filtered_out:
        filter_log_path = Path(filter_log_path)
        filter_log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(filter_log_path, 'w', encoding='utf-8') as f:
            for rec in filtered_out:
                f.write(json.dumps(rec, ensure_ascii=False) + '\n')

    return result, stats, filtered_out, audit_samples


def build_entities_core(entities, relations):
    """Generate slim entities-core.json for first-screen graph.

    Selects core entities: all AEON + PATH types, then top CHAR/ORGN/WRLD by degree
    until ~150 total. Fields: id, canonical_name, type, degree, summary_short.
    """
    # Compute degree for every entity_id
    degree = Counter()
    for rel in (relations or []):
        subj = rel.get('subject_id') or rel.get('subject_name') or ''
        obj = rel.get('object_id') or rel.get('object_name') or ''
        if subj:
            degree[subj] += 1
        if obj:
            degree[obj] += 1

    CORE_PRIORITY = ['AEON', 'PATH']
    SECONDARY = ['CHAR', 'ORGN', 'WRLD']
    TARGET = 150

    core = []
    others = []
    for ent in (entities or []):
        eid = ent.get('entity_id', ent.get('canonical_name', ''))
        d = degree.get(eid, 0)
        summary_text = ''
        if isinstance(ent.get('summary'), dict):
            summary_text = str(ent['summary'].get('text', ''))[:60]
        slim = {
            'id': eid,
            'canonical_name': ent.get('canonical_name', eid),
            'type': ent.get('type', '?'),
            'degree': d,
            'summary_short': summary_text,
        }
        if ent.get('type') in CORE_PRIORITY:
            core.append(slim)
        else:
            others.append(slim)

    # Sort others by degree desc, fill up to TARGET
    others.sort(key=lambda x: (-x['degree'], x['canonical_name']))
    while len(core) < TARGET and others:
        core.append(others.pop(0))

    return core


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Build site data from pass1/pass2 outputs')
    parser.add_argument('--input', default='',
                        help='Pass1 directory (default: output/pass1/ for prod, tests/fixtures/mock_pass1/ for dev)')
    parser.add_argument('--pass2', action='store_true',
                        help='Include pass2 output (default: pass1 only)')
    parser.add_argument('--pass2-dir', default='',
                        help='Pass2 directory (default: output/pass2/)')
    parser.add_argument('--output', default='',
                        help='Output directory (default: site/public/data/)')
    parser.add_argument('--filter-mode', default='audit', choices=['audit', 'filter', 'off'],
                        help='Content quality filter mode: audit (stats only), filter (remove bad entries), off (skip)')
    args = parser.parse_args()

    pass1_dir = Path(args.input) if args.input else OUTPUT / 'pass1'
    pass2_dir = Path(args.pass2_dir) if args.pass2_dir else OUTPUT / 'pass2'
    out_dir = Path(args.output) if args.output else SITE_DATA

    out_dir.mkdir(parents=True, exist_ok=True)
    cite_index_path = BASE / 'work' / 'cite_index.jsonl'

    print(f"C2: Building site data")
    print(f"  Pass1: {pass1_dir}")
    print(f"  Pass2: {pass2_dir} ({'enabled' if args.pass2 else 'disabled'})")
    print(f"  Output: {out_dir}")
    print()

    # Collect pass1 data
    pass1 = collect_from_pass1(pass1_dir)
    print(f"Pass1: {len(pass1['entities'])} entities, {len(pass1['relations'])} relations, "
          f"{len(pass1['events'])} events, {len(pass1['discrepancies'])} discrepancies")

    # Collect pass2 data if enabled
    pass2 = {'entities': [], 'relations': [], 'events': [], 'discrepancies': [], 'merge_records': []}
    if args.pass2:
        pass2 = collect_from_pass2(pass2_dir)
        print(f"Pass2: {len(pass2['entities'])} entities, {len(pass2['relations'])} relations, "
              f"{len(pass2['events'])} events, {len(pass2['discrepancies'])} discrepancies, "
              f"{len(pass2['merge_records'])} merge_records")

    # Build output files
    # Entities with merge annotations
    entities = build_entities_with_merges(
        pass1['entities'], pass2['entities'], pass2['merge_records'])

    # Relations / Events / Discrepancies (raw, before quality filter)
    relations = build_relations(pass1['relations'], pass2['relations'])
    events = build_events(pass1['events'], pass2['events'])
    discrepancies = build_discrepancies(pass1['discrepancies'], pass2['discrepancies'])

    # ── 内容质量过滤 ──
    filter_log = BASE / 'work' / 'site_filtered_out.jsonl'
    pre_filter = {
        'entities': entities,
        'relations': relations,
        'events': events,
        'discrepancies': discrepancies,
    }

    filter_mode = args.filter_mode
    filter_stats = {r: 0 for r in QUALITY_RULES}
    filter_stats['total_filtered'] = 0
    audit_samples = {}

    if filter_mode == 'off':
        print(f"\n  [Quality Filter] OFF — skipping content quality checks")
    else:
        filtered_data, filter_stats, filtered_entries, audit_samples = quality_filter(
            pre_filter, filter_log, mode=filter_mode)
        if filter_mode == 'filter':
            entities = filtered_data['entities']
            relations = filtered_data['relations']
            events = filtered_data['events']
            discrepancies = filtered_data['discrepancies']
            print(f"\n  [Quality Filter] FILTER mode — {filter_stats['total_filtered']} entries removed → {filter_log}")
        else:  # audit mode
            print(f"\n  [Quality Filter] AUDIT mode — {filter_stats['total_filtered']} entries flagged (NOT removed)")
            # Write quality audit JSON
            audit_path = BASE / 'work' / 'quality_audit.json'
            audit_path.parent.mkdir(parents=True, exist_ok=True)
            with open(audit_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'mode': 'audit',
                    'total_entries': sum(len(v) for v in pre_filter.values()),
                    'total_flagged': filter_stats['total_filtered'],
                    'flag_rate': round(filter_stats['total_filtered'] / max(1, sum(len(v) for v in pre_filter.values())), 4),
                    'by_rule': {r: {
                        'count': filter_stats.get(r, 0),
                        'samples': audit_samples.get(r, [])[:20],
                    } for r in QUALITY_RULES},
                }, f, ensure_ascii=False, indent=2)
            print(f"  Audit report → {audit_path}")

    for rule in QUALITY_RULES:
        if filter_stats.get(rule, 0) > 0:
            print(f"    {rule}: {filter_stats[rule]}")
    print()

    # ── 首屏瘦身：entities-core.json ──
    entities_core = build_entities_core(entities, relations)
    with open(out_dir / 'entities-core.json', 'w', encoding='utf-8') as f:
        json.dump(entities_core, f, ensure_ascii=False, indent=2)
    print(f"  entities-core.json: {len(entities_core)} core entities for first screen")
    print()

    with open(out_dir / 'entities.json', 'w', encoding='utf-8') as f:
        json.dump(entities, f, ensure_ascii=False, indent=2)
    print(f"  entities.json: {len(entities)} entities "
          f"({sum(1 for e in entities if e.get('_merged'))} merged)")

    with open(out_dir / 'relations.json', 'w', encoding='utf-8') as f:
        json.dump(relations, f, ensure_ascii=False, indent=2)
    print(f"  relations.json: {len(relations)} relations")

    n_inferred = sum(1 for e in events if e.get('_timeline_inferred'))
    with open(out_dir / 'events.json', 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    print(f"  events.json: {len(events)} events ({n_inferred} with inferred timeline)")

    n_cross = sum(1 for d in discrepancies if d.get('_cross_volume'))
    with open(out_dir / 'discrepancies.json', 'w', encoding='utf-8') as f:
        json.dump(discrepancies, f, ensure_ascii=False, indent=2)
    print(f"  discrepancies.json: {len(discrepancies)} ({n_cross} cross-volume)")

    # Citations (subset: only cited ones)
    all_objects = entities + relations + events + discrepancies
    citations = build_citations(all_objects, cite_index_path)
    with open(out_dir / 'citations.json', 'w', encoding='utf-8') as f:
        json.dump(citations, f, ensure_ascii=False, indent=2)
    print(f"  citations.json: {len(citations)} cited entries (from {Path(cite_index_path).stat().st_size // 1024 // 1024 if cite_index_path.exists() else 0}MB index)")

    # Build summary
    summary = {
        'build_args': {
            'pass1': str(pass1_dir),
            'pass2_enabled': args.pass2,
            'pass2_dir': str(pass2_dir) if args.pass2 else '',
        },
        'outputs': {
            'entities': len(entities),
            'relations': len(relations),
            'events': len(events),
            'discrepancies': len(discrepancies),
            'citations': len(citations),
            'entities_core': len(entities_core),
        },
        'quality_filter': {
            'total_filtered': filter_stats['total_filtered'],
            'by_rule': {r: filter_stats.get(r, 0) for r in QUALITY_RULES},
        },
        'degradation': {
            'pass2_missing': not args.pass2,
            'entities_unmerged': sum(1 for e in entities if not e.get('_merged')),
            'timeline_inferred': n_inferred,
            'cross_volume_discrepancies': n_cross,
        },
    }
    with open(out_dir / 'build_summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\nBuild summary:")
    print(f"  entities:    {len(entities)}")
    print(f"  relations:   {len(relations)}")
    print(f"  events:      {len(events)}")
    print(f"  discrepancies: {len(discrepancies)}")
    print(f"  citations:   {len(citations)}")
    print(f"  stats:       (generated by build_stats.py)")
    if not args.pass2:
        print(f"\n  NOTE: pass2 disabled. Site will render in degraded mode:")
        print(f"    - Entities: not merged (同名实体各自显示，标注「未归并」)")
        print(f"    - Events: timeline inferred from order_hint (标注「推断」)")
        print(f"    - Discrepancies: cross-volume section hidden")


if __name__ == '__main__':
    main()
