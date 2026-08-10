"""
B2: pass2 分块生成器
读 pass1 产出（开发阶段读 mock fixture），按任务策略动态分块。
T4: 实体归并 — 按规范名首字符分组
T5: 跨卷关系 — 按实体分组
T6: 跨卷矛盾 — 按涉及实体分组
T7: 事件时序 — 量小，尽量一块
"""
import json
import sys
import io
import os
from pathlib import Path
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(__file__).parent.parent
WORK = BASE / 'work'
CONFIG = BASE / 'config'
OUTPUT = BASE / 'output'

sys.path.insert(0, str(BASE / 'scripts'))
from token_utils import MAX_TOKENS_PER_CHUNK, estimate_tokens

MAX_TOKENS = MAX_TOKENS_PER_CHUNK  # 550K


def collect_pass1_objects(pass1_dir, obj_type):
    """Collect all objects of a given type from all volumes in pass1 output.

    Args:
        pass1_dir: Path to pass1 output directory
        obj_type: One of 'entities', 'relations', 'events', 'discrepancies'

    Returns list of (volume, object) tuples.
    """
    objects = []
    for vol_dir in sorted(pass1_dir.iterdir()):
        if not vol_dir.is_dir():
            continue
        volume = vol_dir.name
        fpath = vol_dir / f'{obj_type}.jsonl'
        if fpath.exists():
            with open(fpath, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            obj = json.loads(line)
                            objects.append((volume, obj))
                        except json.JSONDecodeError:
                            pass
    return objects


def chunk_by_first_char(objects, max_tokens=MAX_TOKENS):
    """T4 strategy: group entities by canonical_name first char.
    Same-char entities must stay in the same chunk.
    """
    by_char = defaultdict(list)
    for vol, obj in objects:
        name = obj.get('canonical_name', '') or obj.get('merged_name', '') or '?'
        first_char = name[0] if name else '?'
        by_char[first_char].append((vol, obj))

    chunks = []
    current = []
    current_est = 0

    for char in sorted(by_char):
        char_objects = by_char[char]
        char_text = json.dumps([o for _, o in char_objects], ensure_ascii=False)
        char_tokens = estimate_tokens(char_text)

        if current and current_est + char_tokens > max_tokens:
            chunks.append(current)
            current = []
            current_est = 0

        current.extend(char_objects)
        current_est += char_tokens

    if current:
        chunks.append(current)

    return chunks


def chunk_by_entity_group(entities, relations, max_tokens=MAX_TOKENS):
    """T5 strategy: group entities + relations by entity groups.

    Entities that share relations go to the same chunk. Simple connected-component
    approach on the undirected relation graph.
    """
    # Build adjacency
    neighbors = defaultdict(set)
    entity_set = {e.get('canonical_name', '') for _, e in entities}
    for _, rel in relations:
        s = rel.get('subject_name', '') or rel.get('subject_id', '')
        o = rel.get('object_name', '') or rel.get('object_id', '')
        if s and o:
            neighbors[s].add(o)
            neighbors[o].add(s)

    # Find connected components
    visited = set()
    components = []

    for name in sorted(entity_set):
        if name in visited:
            continue
        # BFS
        component = set()
        stack = [name]
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            component.add(node)
            for nb in neighbors.get(node, []):
                if nb not in visited:
                    stack.append(nb)
        components.append(component)

    # Assign entities to components, merge small components
    entity_map = {}
    for _, ent in entities:
        name = ent.get('canonical_name', '')
        entity_map[name] = ent

    chunks = []
    current_ents = []
    current_rels = []
    current_est = 0

    for comp in sorted(components, key=len, reverse=True):
        comp_ents = [(vol, entity_map[name]) for vol, _ in entities
                     if entity_map.get(name) and name in comp]
        comp_rels = [(vol, rel) for vol, rel in relations
                     if rel.get('subject_name', '') in comp or rel.get('object_name', '') in comp]

        comp_text = json.dumps({
            'entities': [o for _, o in comp_ents],
            'relations': [o for _, o in comp_rels],
        }, ensure_ascii=False)
        comp_tokens = estimate_tokens(comp_text)

        if current_ents and current_est + comp_tokens > max_tokens:
            chunks.append({'entities': current_ents, 'relations': current_rels})
            current_ents = []
            current_rels = []
            current_est = 0

        current_ents.extend(comp_ents)
        current_rels.extend(comp_rels)
        current_est += comp_tokens

    if current_ents:
        chunks.append({'entities': current_ents, 'relations': current_rels})

    return chunks


def chunk_by_related_entity(discrepancies, entities, max_tokens=MAX_TOKENS):
    """T6 strategy: group discrepancies by related entity."""
    entity_map = {}
    for _, ent in entities:
        name = ent.get('canonical_name', '')
        entity_map[name] = ent

    # Group discrepancies by their related_entities
    by_entity = defaultdict(list)
    orphans = []
    for vol, d in discrepancies:
        related = d.get('related_entities', [])
        if related:
            for e in related:
                by_entity[e].append((vol, d))
        else:
            orphans.append((vol, d))

    chunks = []
    current = []
    current_est = 0

    all_groups = list(by_entity.items()) + [('_orphans', orphans)]
    for entity_name, discs in all_groups:
        disc_text = json.dumps([o for _, o in discs], ensure_ascii=False)
        disc_tokens = estimate_tokens(disc_text)

        if current and current_est + disc_tokens > max_tokens:
            chunks.append(current)
            current = []
            current_est = 0

        current.extend(discs)
        current_est += disc_tokens

    if current:
        chunks.append(current)

    return chunks


def chunk_events(events, max_tokens=MAX_TOKENS):
    """T7 strategy: all events in one chunk (quantity is small)."""
    event_text = json.dumps([o for _, o in events], ensure_ascii=False)
    event_tokens = estimate_tokens(event_text)

    if event_tokens <= max_tokens:
        return [events]

    # If somehow exceeds limit, split into halves
    mid = len(events) // 2
    return [events[:mid], events[mid:]]


def write_chunk_plan(chunks, task_id, out_path):
    """Write chunk plan as JSON."""
    plan = {
        'task_id': task_id,
        'chunks': [],
    }
    for i, chunk in enumerate(chunks):
        if task_id == 'T4_entity_merge':
            entry_count = len(chunk) if isinstance(chunk, list) else len(chunk.get('entities', []))
            plan['chunks'].append({
                'chunk_id': f'P2-{task_id}-C{i+1:03d}',
                'task_id': task_id,
                'entry_count': entry_count,
                'description': f'T4 merge chunk {i+1}: {entry_count} entities',
            })
        elif task_id == 'T5_relation_crossvol':
            plan['chunks'].append({
                'chunk_id': f'P2-{task_id}-C{i+1:03d}',
                'task_id': task_id,
                'entity_count': len(chunk.get('entities', [])),
                'relation_count': len(chunk.get('relations', [])),
                'description': f'T5 relations chunk {i+1}',
            })
        else:
            plan['chunks'].append({
                'chunk_id': f'P2-{task_id}-C{i+1:03d}',
                'task_id': task_id,
                'entry_count': len(chunk),
                'description': f'{task_id} chunk {i+1}: {len(chunk)} entries',
            })

    plan['total_chunks'] = len(plan['chunks'])
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    return plan


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Pass2 chunk plan generator')
    parser.add_argument('--input', default='',
                        help='Pass1 output directory (default: tests/fixtures/mock_pass1/ for dev, output/pass1/ for prod)')
    parser.add_argument('--output', default='',
                        help='Output JSON path (default: work/pass2_chunks.json)')
    args = parser.parse_args()

    pass1_dir = Path(args.input) if args.input else BASE / 'tests' / 'fixtures' / 'mock_pass1'
    out_path = Path(args.output) if args.output else WORK / 'pass2_chunks.json'

    print(f"Reading pass1 from: {pass1_dir}")
    print(f"Write pass2 plan to: {out_path}")
    print()

    # Collect all pass1 data
    all_entities = collect_pass1_objects(pass1_dir, 'entities')
    all_relations = collect_pass1_objects(pass1_dir, 'relations')
    all_events = collect_pass1_objects(pass1_dir, 'events')
    all_discrepancies = collect_pass1_objects(pass1_dir, 'discrepancies')

    print(f"Pass1 objects: {len(all_entities)} entities, {len(all_relations)} relations, "
          f"{len(all_events)} events, {len(all_discrepancies)} discrepancies")
    print()

    # T4: chunk by first char of canonical_name
    t4_chunks = chunk_by_first_char(all_entities)
    t4_plan = write_chunk_plan(t4_chunks, 'T4_entity_merge',
                                out_path.parent / 'pass2_chunks_T4.json')
    print(f"T4: {len(t4_chunks)} chunks (entities by first char)")

    # T5: chunk by entity groups
    t5_chunks = chunk_by_entity_group(all_entities, all_relations)
    t5_plan = write_chunk_plan(t5_chunks, 'T5_relation_crossvol',
                                out_path.parent / 'pass2_chunks_T5.json')
    print(f"T5: {len(t5_chunks)} chunks (entities+relations by group)")

    # T6: chunk by related entity
    t6_chunks = chunk_by_related_entity(all_discrepancies, all_entities)
    t6_plan = write_chunk_plan(t6_chunks, 'T6_discrepancy_cross',
                                out_path.parent / 'pass2_chunks_T6.json')
    print(f"T6: {len(t6_chunks)} chunks (discrepancies by entity)")

    # T7: all events
    t7_chunks = chunk_events(all_events)
    t7_plan = write_chunk_plan(t7_chunks, 'T7_event_timeline',
                                out_path.parent / 'pass2_chunks_T7.json')
    print(f"T7: {len(t7_chunks)} chunk(s) (all events)")

    # Combined plan
    combined = {
        'tasks': {
            'T4_entity_merge': t4_plan,
            'T5_relation_crossvol': t5_plan,
            'T6_discrepancy_cross': t6_plan,
            'T7_event_timeline': t7_plan,
        },
        'total_pass2_chunks': (len(t4_chunks) + len(t5_chunks) +
                               len(t6_chunks) + len(t7_chunks)),
        'note': 'pass2 chunks are dynamic — count depends on pass1 output volume, not pass1 chunk count',
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)

    total = combined['total_pass2_chunks']
    print(f"\nTotal pass2 chunks: {total}")
    print(f"  (pass1 had 34 chunks — pass2 chunk count is different)")
    print(f"\nPlan saved to: {out_path}")


if __name__ == '__main__':
    main()
