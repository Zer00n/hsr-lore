"""
Pass2 prompt builder
读 pass1 产出，按各 pass2 任务卡模板槽位拼装 prompt。
同时构造该块的 cite_whitelist。
"""
import json
import re
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).parent.parent


def load_pass1_objects(pass1_dir, obj_type):
    """Collect all objects of a type from all volumes in pass1 output.

    Returns list of dicts (with _source_volume annotation).
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
                            obj['_source_volume'] = volume
                            objects.append(obj)
                        except json.JSONDecodeError:
                            pass
    return objects


def collect_cite_ids_from_objects(objects):
    """Recursively extract all cite_ids from a list of objects."""
    ids = set()

    def walk(obj):
        if isinstance(obj, dict):
            if 'cite_id' in obj:
                ids.add(obj['cite_id'])
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    for obj in objects:
        walk(obj)
    return sorted(ids)


def format_entity_list(entities):
    """Format entities for {entity_list} slot (T4).

    One entity per line: canonical_name (type) [source_volume]
    """
    lines = []
    for e in entities:
        name = e.get('canonical_name', '?')
        etype = e.get('type', '?')
        vol = e.get('_source_volume', e.get('source_volume', '?'))
        aliases = e.get('aliases', [])
        alias_str = f" (别名: {', '.join(aliases)})" if aliases else ''
        summary = e.get('summary', {}).get('text', '')[:120]
        lines.append(f"- {name} [{etype}] [{vol}]{alias_str}: {summary}")
    return '\n'.join(lines)


def format_all_entities(entities):
    """Format all entities for {all_entities} slot (T5, T6).

    Full JSON representation, compact.
    """
    return json.dumps(entities, ensure_ascii=False, indent=1)


def format_all_relations(relations):
    """Format relations for {all_relations} slot (T5).

    Full JSON representation, compact.
    """
    return json.dumps(relations, ensure_ascii=False, indent=1)


def format_all_events(events):
    """Format events for {all_events} slot (T7).

    Full JSON representation, compact.
    """
    return json.dumps(events, ensure_ascii=False, indent=1)


def format_all_discrepancies(discrepancies):
    """Format discrepancies for {all_intra_discrepancies} slot (T6).

    Full JSON representation, compact.
    """
    return json.dumps(discrepancies, ensure_ascii=False, indent=1)


def format_cite_whitelist(whitelist_ids):
    """Format cite whitelist for {cite_whitelist} slot (T5, T6).

    Simple list of cite_ids.
    """
    return '\n'.join(sorted(whitelist_ids))


def format_retrieved_corpus(entries):
    """Format retrieved corpus for {retrieved_corpus} slot (T5, T6).

    Uses mock data in dev mode — real OpenViking in production.
    """
    if not entries:
        # Mock placeholder — would be real OpenViking results in production
        return "[retrieved_corpus: mock — no OpenViking hits in dev mode]"
    lines = []
    for entry in entries:
        lines.append(f"[{entry['cite_id']}]\n{entry.get('clean', '')}\n")
    return '\n'.join(lines)


def format_ov_navigation(entity_pairs):
    """Format OpenViking navigation for {ov_navigation_results} slot (T4).

    Mock data in dev mode.
    """
    if not entity_pairs:
        return "[OV navigation: mock — no entity pairs in dev mode]"
    lines = []
    for i, (e1, e2) in enumerate(entity_pairs):
        lines.append(f"检索 '{e1}' + '{e2}': [MOCK] No real OV hits in dev mode.")
    return '\n'.join(lines)


def build_pass2_prompt(task_name, task_card, pass1_dir, cite_index):
    """Build the full prompt (system + user) for a pass2 task.

    Returns (messages, cite_whitelist_ids, prompt_text) tuple.
    """
    system_prompt = task_card.get('system_prompt', '')
    user_template = task_card.get('user_prompt_template', '')

    # Load all pass1 data
    all_entities = load_pass1_objects(pass1_dir, 'entities')
    all_relations = load_pass1_objects(pass1_dir, 'relations')
    all_events = load_pass1_objects(pass1_dir, 'events')
    all_discrepancies = load_pass1_objects(pass1_dir, 'discrepancies')

    # Build whitelist: all cite_ids from all pass1 objects
    cite_whitelist_ids = collect_cite_ids_from_objects(
        all_entities + all_relations + all_events + all_discrepancies)

    # Build slot content per task
    user_prompt = user_template

    if task_name == 'T4_entity_merge':
        entity_list = format_entity_list(all_entities)
        ov_nav = format_ov_navigation([])  # Mock — in production, extract entity pairs
        user_prompt = user_prompt.replace('{entity_list}', entity_list)
        user_prompt = user_prompt.replace('{ov_navigation_results}', ov_nav)

    elif task_name == 'T5_relation_crossvol':
        wl_text = format_cite_whitelist(cite_whitelist_ids)
        ents_text = format_all_entities(all_entities)
        rels_text = format_all_relations(all_relations)
        corpus_text = format_retrieved_corpus([])  # Mock
        user_prompt = user_prompt.replace('{cite_whitelist}', wl_text)
        user_prompt = user_prompt.replace('{all_entities}', ents_text)
        user_prompt = user_prompt.replace('{all_relations}', rels_text)
        user_prompt = user_prompt.replace('{retrieved_corpus}', corpus_text)

    elif task_name == 'T6_discrepancy_cross':
        wl_text = format_cite_whitelist(cite_whitelist_ids)
        ents_text = format_all_entities(all_entities)
        discs_text = format_all_discrepancies(all_discrepancies)
        corpus_text = format_retrieved_corpus([])  # Mock
        user_prompt = user_prompt.replace('{cite_whitelist}', wl_text)
        user_prompt = user_prompt.replace('{all_entities}', ents_text)
        user_prompt = user_prompt.replace('{all_intra_discrepancies}', discs_text)
        user_prompt = user_prompt.replace('{retrieved_corpus}', corpus_text)

    elif task_name == 'T7_event_timeline':
        events_text = format_all_events(all_events)
        user_prompt = user_prompt.replace('{all_events}', events_text)

    # Check for unreplaced placeholders
    unreplaced = re.findall(r'\{[a-z_]+\}', user_prompt)
    if unreplaced:
        for ph in unreplaced:
            user_prompt = user_prompt.replace(ph, f'[{ph}: NOT AVAILABLE]')

    full_prompt = system_prompt + '\n\n' + user_prompt

    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_prompt},
    ]

    return messages, cite_whitelist_ids, full_prompt


def save_prompt_and_whitelist(task_name, messages, whitelist_ids, full_prompt, run_logs):
    """Save pass2 prompt to work/prompts/pass2/ and whitelist to run dir."""
    prompts_dir = BASE / 'work' / 'prompts' / 'pass2'
    prompts_dir.mkdir(parents=True, exist_ok=True)

    # Save full prompt
    prompt_path = prompts_dir / f'{task_name}.txt'
    with open(prompt_path, 'w', encoding='utf-8') as f:
        f.write(full_prompt)

    # Save whitelist to run logs
    wl_dir = run_logs / 'pass2_whitelist'
    wl_dir.mkdir(parents=True, exist_ok=True)
    wl_path = wl_dir / f'{task_name}_chunk.json'
    with open(wl_path, 'w', encoding='utf-8') as f:
        json.dump({'task_name': task_name, 'cite_ids': whitelist_ids,
                    'count': len(whitelist_ids)}, f, ensure_ascii=False, indent=2)

    return prompt_path, wl_path, len(whitelist_ids)
