"""
OpenViking 干跑脚本 v3
读 corpus/，按目录树规则计算文件清单与文件数分布，不联网。
输出 work/ov_plan.json

v3 修正：
- 光锥按实体聚合（ItemDesc + ItemBGDesc → 一个文件）
- 遗器按 RelicSet 聚合（通过 RelicConfig → RelicSetConfig）
- lore/worlds 拆分为 worlds/（BookSeriesWorld）和 loading/（LoadingDesc）
- 文件名碰撞检测
- push 使用 --parent 而非 --to，避免 URI 包裹问题
"""
import json, os, sys, io, re
from pathlib import Path
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(__file__).parent.parent.parent
CORPUS = BASE / 'corpus'
WORK = BASE / 'work'
VENDOR = BASE / 'vendor' / 'StarRailData'
OUTPUT = WORK / 'ov_plan.json'

# ── TextMap loader ────────────────────────────────────────────────

def load_textmap():
    """Load TextMapCHS.json → {hash: text}."""
    tm_path = VENDOR / 'TextMap' / 'TextMapCHS.json'
    if not tm_path.exists():
        print("  WARNING: TextMapCHS.json not found, TextMap lookup disabled")
        return {}
    with open(tm_path, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    # TextMap is {hash_str: text}
    return raw

print("Loading TextMap...")
textmap = load_textmap()
print(f"  {len(textmap)} entries")

def resolve_hash(hash_val):
    """Resolve a Hash integer/string to Chinese text via TextMap."""
    if isinstance(hash_val, int):
        hash_val = str(hash_val)
    return textmap.get(hash_val, textmap.get(str(hash_val), ''))

# ── Relic set mapping ──────────────────────────────────────────────

def build_relic_set_map():
    """
    Build relic ID → (SetID, SetName) mapping.
    Path: ItemConfigRelic.ID → RelicConfig[ID].SetID → RelicSetConfig[SetID].SetName
    """
    relic_config_path = VENDOR / 'ExcelOutput' / 'RelicConfig.json'
    relic_set_config_path = VENDOR / 'ExcelOutput' / 'RelicSetConfig.json'

    if not relic_config_path.exists() or not relic_set_config_path.exists():
        print("  WARNING: RelicConfig/RelicSetConfig not found, relics won't be grouped by set")
        return {}, {}

    with open(relic_config_path, 'r', encoding='utf-8') as f:
        relic_config = json.load(f)
    with open(relic_set_config_path, 'r', encoding='utf-8') as f:
        relic_set_config = json.load(f)

    # Build ID → SetID
    id_to_setid = {}
    if isinstance(relic_config, list):
        for item in relic_config:
            id_to_setid[item['ID']] = item['SetID']

    # Build SetID → SetName
    setid_to_name = {}
    if isinstance(relic_set_config, list):
        for item in relic_set_config:
            sid = item['SetID']
            name_hash = item.get('SetName', {}).get('Hash', 0)
            name = resolve_hash(name_hash) if name_hash else f'Set-{sid}'
            setid_to_name[sid] = name

    print(f"  Relic ID→SetID: {len(id_to_setid)} mappings")
    print(f"  SetID→Name: {len(setid_to_name)} sets")
    return id_to_setid, setid_to_name

print("Building relic set map...")
RELIC_ID_TO_SETID, RELIC_SETID_TO_NAME = build_relic_set_map()

# ── Load corpus data ────────────────────────────────────────────

def load_corpus(volume):
    path = CORPUS / f'{volume}.jsonl'
    if not path.exists():
        return []
    entries = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    return entries

print("\nLoading corpus...")
volumes = {}
for vol in ['lore', 'books', 'characters', 'narrative', 'dialogue', 'artifacts', 'rogue', 'unattributed']:
    volumes[vol] = load_corpus(vol)
    print(f'  {vol}: {len(volumes[vol])} entries')

# ── Plan generation ─────────────────────────────────────────────

plan = {
    'namespace': 'viking://resources/hsr',
    'directories': {},
    'total_files': 0,
    'total_bytes': 0,
    'max_file_bytes': 0,
    'avg_file_bytes': 0,
}

# Track all used file paths to detect collisions
_used_paths = {}  # path → count
_collision_count = 0

def add_file(dir_path, filename, content, metadata=None):
    """Add a file to the plan. Detects and resolves slug collisions."""
    global _collision_count

    if dir_path not in plan['directories']:
        plan['directories'][dir_path] = {'files': [], 'file_count': 0, 'total_bytes': 0}

    d = plan['directories'][dir_path]

    # Collision detection
    full_path = f'{dir_path}/{filename}'
    if full_path in _used_paths:
        _collision_count += 1
        base, ext = os.path.splitext(filename)
        suffix = _used_paths[full_path]
        filename = f'{base}-{suffix}{ext}'
        full_path = f'{dir_path}/{filename}'
        _used_paths[full_path] = suffix + 1
    else:
        _used_paths[full_path] = 1

    file_entry = {
        'path': full_path,
        'size_bytes': len(content.encode('utf-8')),
        'entry_count': metadata.get('entry_count', 1) if metadata else 1,
    }
    d['files'].append(file_entry)
    d['file_count'] += 1
    d['total_bytes'] += file_entry['size_bytes']
    plan['total_files'] += 1
    plan['total_bytes'] += file_entry['size_bytes']
    plan['max_file_bytes'] = max(plan['max_file_bytes'], file_entry['size_bytes'])
    return file_entry

def fmt_md(frontmatter, body):
    """Format a markdown file with YAML frontmatter."""
    fm_lines = ['---']
    for k, v in frontmatter.items():
        if v is not None and v != '' and v != 0:
            fm_lines.append(f'{k}: {v}')
    fm_lines.append('---')
    return '\n'.join(fm_lines) + '\n\n' + body

KB = 1024
MAX_FILE_BYTES = 97 * KB  # 100KB target minus ~3KB frontmatter overhead
MAX_ENTRIES = 500

# ── 1. lore ─────────────────────────────────────────────────────

print("\nPlanning lore...")
lore_dir = 'lore'

# nouns/
for e in volumes['lore']:
    if e['source_table'] == 'NounAtlas' and e['source_field'] == 'NounDesc':
        slug = re.sub(r'[^\w一-鿿-]', '', e.get('title', 'unknown'))[:40] or f"noun-{e['source_pk']}"
        body = f'[{e["cite_id"]}]\n{e["clean"]}'
        content = fmt_md({
            'volume': 'lore', 'source_table': 'NounAtlas',
            'entry_count': 1,
        }, body)
        add_file(f'{lore_dir}/nouns', f'{slug}.md', content, {'entry_count': 1})

# titans/
for e in volumes['lore']:
    if e['source_table'] in ('TitanAtlas', 'TitanAtlasGroup'):
        slug = re.sub(r'[^\w一-鿿-]', '', e.get('title', 'unknown'))[:40] or f"titan-{e['source_pk']}"
        body = f'[{e["cite_id"]}]\n{e["clean"]}'
        content = fmt_md({
            'volume': 'lore', 'source_table': e['source_table'],
            'entry_count': 1,
        }, body)
        add_file(f'{lore_dir}/titans', f'{slug}.md', content, {'entry_count': 1})

# aeons/
for e in volumes['lore']:
    if e['source_table'] in ('RogueAeonStoryConfig', 'RogueAeonDisplay'):
        slug = re.sub(r'[^\w一-鿿-]', '', e.get('title', 'unknown'))[:40] or f"aeon-{e['source_pk']}"
        body = f'[{e["cite_id"]}]\n{e["clean"]}'
        content = fmt_md({
            'volume': 'lore', 'source_table': e['source_table'],
            'entry_count': 1,
        }, body)
        add_file(f'{lore_dir}/aeons', f'{slug}.md', content, {'entry_count': 1})

# worlds/ — BookSeriesWorld only (6 entries), NOT LoadingDesc
for e in volumes['lore']:
    if e['source_table'] == 'BookSeriesWorld':
        wname = e.get('meta', {}).get('world_name', '') or e.get('title', 'unknown')
        slug = re.sub(r'[^\w一-鿿-]', '', wname)[:40] or f"world-{e['source_pk']}"
        body = f'[{e["cite_id"]}]\n{e["clean"]}'
        content = fmt_md({
            'volume': 'lore', 'source_table': 'BookSeriesWorld',
            'entry_count': 1,
        }, body)
        add_file(f'{lore_dir}/worlds', f'{slug}.md', content, {'entry_count': 1})

# loading/ — LoadingDesc only (403 entries), simple ID-range split, ≤30 per file
loading_entries = [e for e in volumes['lore'] if e['source_table'] == 'LoadingDesc']
if loading_entries:
    # Sort by source_pk (LOAD cite_id number) for stable ordering
    loading_entries.sort(key=lambda e: e.get('source_pk', 0))

    LOADING_PER_FILE = 30
    for chunk_start in range(0, len(loading_entries), LOADING_PER_FILE):
        chunk = loading_entries[chunk_start:chunk_start + LOADING_PER_FILE]
        first_id = chunk[0].get('source_pk', chunk_start)
        last_id = chunk[-1].get('source_pk', chunk_start + len(chunk) - 1)
        chunk_parts = []
        for e in chunk:
            chunk_parts.append(f'[{e["cite_id"]}]\n{e["clean"]}\n\n')
        content = fmt_md({
            'volume': 'lore', 'source_table': 'LoadingDesc',
            'id_range': f'{first_id}-{last_id}',
            'entry_count': len(chunk),
        }, ''.join(chunk_parts))
        fname = f'{first_id:05d}-{last_id:05d}.md'
        add_file(f'{lore_dir}/loading', fname, content, {'entry_count': len(chunk)})

# ── 2. books ─────────────────────────────────────────────────────

print("Planning books...")
books_dir = 'books'

books_by_series = defaultdict(list)
for e in volumes['books']:
    if e['source_table'] == 'BookSeriesConfig':
        bsid = e.get('meta', {}).get('book_series_id', 0) or e['source_pk']
        books_by_series[bsid].append(('series', e))
    elif e['source_table'] == 'LocalbookConfig':
        bsid = e.get('meta', {}).get('book_series_id', 0) or 0
        books_by_series[bsid].append(('book', e))

for bsid, entries in sorted(books_by_series.items()):
    series_name = ''
    series_entries = [e for t, e in entries if t == 'series']
    book_entries = [e for t, e in entries if t == 'book']

    if series_entries:
        series_name = series_entries[0].get('title', f'series-{bsid}')
    else:
        series_name = f'series-{bsid}'

    series_slug = re.sub(r'[^\w一-鿿-]', '', series_name)[:40]
    series_path = f'{books_dir}/{series_slug}'

    # _series.md
    if series_entries:
        body_parts = []
        for e in series_entries:
            body_parts.append(f'[{e["cite_id"]}]\n{e["clean"]}')
        content = fmt_md({
            'volume': 'books', 'source_table': 'BookSeriesConfig',
            'book_series_id': bsid, 'entry_count': len(series_entries),
        }, '\n\n'.join(body_parts))
        add_file(series_path, '_series.md', content, {'entry_count': len(series_entries)})

    # Individual books
    for e in book_entries:
        book_name = e.get('title', f'book-{e["source_pk"]}')
        book_slug = re.sub(r'[^\w一-鿿-]', '', book_name)[:50]
        wname = e.get('meta', {}).get('world_name', '')
        body = f'[{e["cite_id"]}]\n{e["clean"]}'
        content = fmt_md({
            'volume': 'books', 'source_table': 'LocalbookConfig',
            'book_series_id': bsid, 'world_name': wname,
            'entry_count': 1,
        }, body)
        add_file(series_path, f'{book_slug}.md', content, {'entry_count': 1})

# ── 3. characters ───────────────────────────────────────────────

print("Planning characters...")
char_dir = 'characters'

# Group by avatar_id — each source_table field is already unique per avatar,
# so no multi-field issue like lightcones
chars_by_avatar = defaultdict(lambda: {'profile': [], 'stories': [], 'voices': []})
for e in volumes['characters']:
    aid = e.get('meta', {}).get('avatar_id', 0) or e['source_pk']
    if e['source_table'] == 'AvatarConfig':
        chars_by_avatar[aid]['profile'].append(e)
    elif e['source_table'] == 'StoryAtlas':
        chars_by_avatar[aid]['stories'].append(e)
    elif e['source_table'] == 'VoiceAtlas':
        chars_by_avatar[aid]['voices'].append(e)

for aid, data in sorted(chars_by_avatar.items()):
    av_name = data['profile'][0].get('meta', {}).get('avatar_name', '') if data['profile'] else f'char-{aid}'
    if not av_name:
        av_name = data['stories'][0].get('meta', {}).get('avatar_name', '') if data['stories'] else f'char-{aid}'
    char_slug = re.sub(r'[^\w一-鿿-]', '', av_name)[:40] or f'char-{aid}'
    char_path = f'{char_dir}/{char_slug}'

    # profile.md
    if data['profile']:
        body_parts = []
        for e in data['profile']:
            body_parts.append(f'[{e["cite_id"]}]\n{e["clean"]}')
        content = fmt_md({
            'volume': 'characters', 'source_table': 'AvatarConfig',
            'avatar_id': aid, 'avatar_name': av_name,
            'entry_count': len(data['profile']),
        }, '\n\n'.join(body_parts))
        add_file(char_path, 'profile.md', content, {'entry_count': len(data['profile'])})

    # stories.md
    if data['stories']:
        body_parts = []
        for e in data['stories']:
            si = e.get('meta', {}).get('story_index', 0)
            body_parts.append(f'## 故事 {si}\n\n[{e["cite_id"]}]\n{e["clean"]}')
        content = fmt_md({
            'volume': 'characters', 'source_table': 'StoryAtlas',
            'avatar_id': aid, 'avatar_name': av_name,
            'entry_count': len(data['stories']),
        }, '\n\n'.join(body_parts))
        add_file(char_path, 'stories.md', content, {'entry_count': len(data['stories'])})

    # voices.md
    if data['voices']:
        body_parts = []
        for e in data['voices']:
            vt = e.get('meta', {}).get('voice_title', '')
            body_parts.append(f'### {vt}\n\n[{e["cite_id"]}]\n{e["clean"]}')
        content = fmt_md({
            'volume': 'characters', 'source_table': 'VoiceAtlas',
            'avatar_id': aid, 'avatar_name': av_name,
            'entry_count': len(data['voices']),
        }, '\n\n'.join(body_parts))
        add_file(char_path, 'voices.md', content, {'entry_count': len(data['voices'])})

# ── 4. narrative ────────────────────────────────────────────────

print("Planning narrative...")
narr_dir = 'narrative'

narr_by_world = defaultdict(list)
for e in volumes['narrative']:
    wid = e.get('meta', {}).get('world_id', 0) or 0
    narr_by_world[wid].append(e)

# Load world names
world_names = {}
for e in volumes['lore']:
    if e['source_table'] == 'BookSeriesWorld':
        wid = e['source_pk']
        world_names[wid] = e.get('clean', f'world-{wid}')

for wid, entries in sorted(narr_by_world.items()):
    wname = world_names.get(wid, f'world-{wid}')
    world_slug = re.sub(r'[^\w一-鿿-]', '', wname)[:40]

    # Group by mission_id
    by_mission = defaultdict(list)
    for e in entries:
        mid = e.get('meta', {}).get('mission_id', 0) or e.get('meta', {}).get('main_mission_id', 0) or 0
        by_mission[mid].append(e)

    for mid, m_entries in sorted(by_mission.items()):
        mname = m_entries[0].get('meta', {}).get('mission_name', '') or f'mission-{mid}'
        mslug = re.sub(r'[^\w一-鿿-]', '', mname)[:50] or f'mission-{mid}'
        mission_path = f'{narr_dir}/{world_slug}'

        # Split large missions into chunks
        chunk_idx = 0
        chunk_body = []
        chunk_size = 0
        for e in m_entries:
            chunk = f'[{e["cite_id"]}]\n{e["clean"]}\n\n'
            cs = len(chunk.encode('utf-8'))
            if chunk_body and (chunk_size + cs > MAX_FILE_BYTES or len(chunk_body) >= MAX_ENTRIES):
                content = fmt_md({
                    'volume': 'narrative', 'mission_id': mid,
                    'mission_name': mname, 'world_id': wid, 'world_name': wname,
                    'entry_count': len(chunk_body),
                }, ''.join(chunk_body))
                suffix = f'-{chunk_idx:02d}' if chunk_idx > 0 else ''
                add_file(mission_path, f'{mslug}{suffix}.md', content, {'entry_count': len(chunk_body)})
                chunk_idx += 1
                chunk_body = []
                chunk_size = 0
            chunk_body.append(chunk)
            chunk_size += cs
        if chunk_body:
            content = fmt_md({
                'volume': 'narrative', 'mission_id': mid,
                'mission_name': mname, 'world_id': wid, 'world_name': wname,
                'entry_count': len(chunk_body),
            }, ''.join(chunk_body))
            suffix = f'-{chunk_idx:02d}' if chunk_idx > 0 else ''
            add_file(mission_path, f'{mslug}{suffix}.md', content, {'entry_count': len(chunk_body)})

# ── 5. dialogue ─────────────────────────────────────────────────

print("Planning dialogue...")
dial_dir = 'dialogue'

# Group by speaker (or sender for MSG)
dial_by_speaker = defaultdict(list)
for e in volumes['dialogue']:
    sp = e.get('meta', {}).get('speaker', '') or e.get('meta', {}).get('sender', '')
    if not sp:
        sp = 'system'
    # Normalize {NICKNAME} → 开拓者
    if sp == '{NICKNAME}':
        sp = '开拓者'
    dial_by_speaker[sp].append(e)

# Special handling
protagonist_entries = dial_by_speaker.pop('开拓者', [])
anonymous_entries = dial_by_speaker.pop('？？？', [])

def write_dialogue_files(dir_path, entries, sp_label, sp_type=None):
    """Write dialogue entries, splitting if over MAX_FILE_BYTES or MAX_ENTRIES."""
    body_parts = []
    current_bytes = 0
    file_idx = 0
    for e in entries:
        sp = e.get('meta', {}).get('speaker', '') or e.get('meta', {}).get('sender', '')
        chunk = f'[{e["cite_id"]}]\n**{sp}**: {e["clean"]}\n\n'
        cs = len(chunk.encode('utf-8'))
        if body_parts and (current_bytes + cs > MAX_FILE_BYTES or len(body_parts) >= MAX_ENTRIES):
            fm = {'volume': 'dialogue', 'speaker': sp_label, 'entry_count': len(body_parts)}
            if sp_type: fm['speaker_type'] = sp_type
            content = fmt_md(fm, ''.join(body_parts))
            suffix = f'-{file_idx:02d}' if file_idx > 0 else ''
            add_file(dir_path, f'{sp_label}{suffix}.md', content, {'entry_count': len(body_parts)})
            file_idx += 1
            body_parts = []
            current_bytes = 0
        body_parts.append(chunk)
        current_bytes += cs
    if body_parts:
        fm = {'volume': 'dialogue', 'speaker': sp_label, 'entry_count': len(body_parts)}
        if sp_type: fm['speaker_type'] = sp_type
        content = fmt_md(fm, ''.join(body_parts))
        suffix = f'-{file_idx:02d}' if file_idx > 0 else ''
        add_file(dir_path, f'{sp_label}{suffix}.md', content, {'entry_count': len(body_parts)})

# 开拓者 (protagonist)
if protagonist_entries:
    write_dialogue_files(f'{dial_dir}/by-speaker', protagonist_entries, '开拓者', 'protagonist')
# ？？？ (anonymous)
if anonymous_entries:
    write_dialogue_files(f'{dial_dir}/by-speaker', anonymous_entries, '？？？', 'anonymous')

major_speakers = {sp: entries for sp, entries in dial_by_speaker.items() if len(entries) >= 100}
minor_speakers = {sp: entries for sp, entries in dial_by_speaker.items() if len(entries) < 100}

for sp, entries in sorted(major_speakers.items()):
    sp_slug = re.sub(r'[^\w一-鿿-]', '', sp)[:40] or f'speaker-{hash(sp)}'
    write_dialogue_files(f'{dial_dir}/by-speaker', entries, sp_slug)

# minor/ (grouped, ~MAX_FILE_BYTES per file)
minor_entries = []
for sp, entries in sorted(minor_speakers.items()):
    minor_entries.extend(entries)

group_idx = 0
group_body = []
group_size = 0
for e in minor_entries:
    sp = e.get('meta', {}).get('speaker', '') or e.get('meta', {}).get('sender', '')
    chunk = f'[{e["cite_id"]}]\n**{sp}**: {e["clean"]}\n\n'
    chunk_size = len(chunk.encode('utf-8'))
    if group_body and (group_size + chunk_size > MAX_FILE_BYTES or len(group_body) >= MAX_ENTRIES):
        content = fmt_md({'volume': 'dialogue', 'group': group_idx, 'entry_count': len(group_body)}, ''.join(group_body))
        add_file(f'{dial_dir}/minor', f'group-{group_idx:04d}.md', content, {'entry_count': len(group_body)})
        group_idx += 1
        group_body = []
        group_size = 0
    group_body.append(chunk)
    group_size += chunk_size

if group_body:
    content = fmt_md({'volume': 'dialogue', 'group': group_idx, 'entry_count': len(group_body)}, ''.join(group_body))
    add_file(f'{dial_dir}/minor', f'group-{group_idx:04d}.md', content, {'entry_count': len(group_body)})

# ── 6. artifacts ─────────────────────────────────────────────────

print("Planning artifacts...")
art_dir = 'artifacts'

# Categorize by source table
art_by_type = defaultdict(list)
for e in volumes['artifacts']:
    if e['source_table'] == 'ItemConfigEquipment':
        art_by_type['lightcones'].append(e)
    elif e['source_table'] == 'ItemConfigRelic':
        art_by_type['relics'].append(e)
    elif e['source_table'] == 'ItemConfig':
        art_by_type['items'].append(e)
    elif e['source_table'] == 'ItemConfigDisk':
        art_by_type['disks'].append(e)
    elif e['source_table'] == 'MonsterConfig':
        art_by_type['monsters'].append(e)
    else:
        art_by_type['others'].append(e)

# ── Lightcones: group by EquipmentID (one entity → one file) ──

if art_by_type.get('lightcones'):
    lc_by_id = defaultdict(list)
    for e in art_by_type['lightcones']:
        lc_by_id[e['source_pk']].append(e)

    for equip_id, entries in sorted(lc_by_id.items()):
        name = entries[0].get('title', f'lightcone-{equip_id}')
        slug = re.sub(r'[^\w一-鿿-]', '', name)[:50] or f'lightcone-{equip_id}'
        body_parts = []
        for e in sorted(entries, key=lambda x: x['source_field']):
            field_label = e['source_field']
            body_parts.append(f'### {field_label}\n\n[{e["cite_id"]}]\n{e["clean"]}')
        content = fmt_md({
            'volume': 'artifacts', 'source_table': 'ItemConfigEquipment',
            'equipment_id': equip_id, 'item_name': name,
            'entry_count': len(entries),
        }, '\n\n'.join(body_parts))
        add_file(f'{art_dir}/lightcones', f'{slug}.md', content, {'entry_count': len(entries)})

# ── Relics: group by RelicSet ──

if art_by_type.get('relics'):
    relics_by_setid = defaultdict(list)
    ungrouped = []
    for e in art_by_type['relics']:
        relic_id = e['source_pk']
        set_id = RELIC_ID_TO_SETID.get(relic_id)
        if set_id and set_id in RELIC_SETID_TO_NAME:
            relics_by_setid[set_id].append(e)
        else:
            ungrouped.append(e)

    for set_id, entries in sorted(relics_by_setid.items()):
        set_name = RELIC_SETID_TO_NAME.get(set_id, f'Set-{set_id}')
        set_slug = re.sub(r'[^\w一-鿿-]', '', set_name)[:50] or f'set-{set_id}'
        body_parts = []
        for e in entries:
            name = e.get('title', '')
            body_parts.append(f'[{e["cite_id"]}]\n**{name}**: {e["clean"]}')
        content = fmt_md({
            'volume': 'artifacts', 'source_table': 'ItemConfigRelic',
            'relic_set_id': set_id, 'relic_set_name': set_name,
            'entry_count': len(entries),
        }, '\n\n'.join(body_parts))
        add_file(f'{art_dir}/relics', f'{set_slug}.md', content, {'entry_count': len(entries)})

    # Ungrouped relics (no SetID or SetName not found) → flat file
    if ungrouped:
        print(f"  WARNING: {len(ungrouped)} relics could not be grouped by set")
        chunk_idx = 0
        chunk_body = []
        chunk_size = 0
        for e in ungrouped:
            name = e.get('title', '')
            chunk = f'[{e["cite_id"]}]\n**{name}**: {e["clean"]}\n\n'
            cs = len(chunk.encode('utf-8'))
            if chunk_body and (chunk_size + cs > MAX_FILE_BYTES or len(chunk_body) >= MAX_ENTRIES):
                content = fmt_md({
                    'volume': 'artifacts', 'source_table': 'ItemConfigRelic',
                    'note': 'ungrouped', 'entry_count': len(chunk_body),
                }, ''.join(chunk_body))
                add_file(f'{art_dir}/relics', f'ungrouped-{chunk_idx:03d}.md', content, {'entry_count': len(chunk_body)})
                chunk_idx += 1
                chunk_body = []
                chunk_size = 0
            chunk_body.append(chunk)
            chunk_size += cs
        if chunk_body:
            content = fmt_md({
                'volume': 'artifacts', 'source_table': 'ItemConfigRelic',
                'note': 'ungrouped', 'entry_count': len(chunk_body),
            }, ''.join(chunk_body))
            add_file(f'{art_dir}/relics', f'ungrouped-{chunk_idx:03d}.md', content, {'entry_count': len(chunk_body)})

# ── Disks: one per entity (ItemDesc only, 1:1) ──

if art_by_type.get('disks'):
    for e in art_by_type['disks']:
        name = e.get('title', f'disk-{e["source_pk"]}')
        slug = re.sub(r'[^\w一-鿿-]', '', name)[:50] or f'disk-{e["source_pk"]}'
        body = f'[{e["cite_id"]}]\n{e["clean"]}'
        content = fmt_md({
            'volume': 'artifacts', 'source_table': 'ItemConfigDisk',
            'item_name': e.get('meta', {}).get('item_name', ''),
            'entry_count': 1,
        }, body)
        add_file(f'{art_dir}/disks', f'{slug}.md', content, {'entry_count': 1})

# ── Items: group by ItemSubType (if available), split at limit ──

if art_by_type.get('items'):
    # Check if meta has item_subtype
    items_by_subtype = defaultdict(list)
    for e in art_by_type['items']:
        subtype = e.get('meta', {}).get('item_subtype', 'general')
        items_by_subtype[subtype].append(e)

    for subtype, entries in sorted(items_by_subtype.items()):
        sub_slug = re.sub(r'[^\w一-鿿-]', '', subtype)[:40] or 'general'
        chunk_idx = 0
        chunk_body = []
        chunk_size = 0
        for e in entries:
            name = e.get('title', '')
            chunk = f'[{e["cite_id"]}]\n**{name}**: {e["clean"]}\n\n'
            cs = len(chunk.encode('utf-8'))
            if chunk_body and (chunk_size + cs > MAX_FILE_BYTES or len(chunk_body) >= MAX_ENTRIES):
                content = fmt_md({
                    'volume': 'artifacts', 'source_table': 'ItemConfig',
                    'item_subtype': subtype, 'entry_count': len(chunk_body),
                }, ''.join(chunk_body))
                suffix = f'-{chunk_idx:02d}' if chunk_idx > 0 else ''
                add_file(f'{art_dir}/items', f'{sub_slug}{suffix}.md', content, {'entry_count': len(chunk_body)})
                chunk_idx += 1
                chunk_body = []
                chunk_size = 0
            chunk_body.append(chunk)
            chunk_size += cs
        if chunk_body:
            content = fmt_md({
                'volume': 'artifacts', 'source_table': 'ItemConfig',
                'item_subtype': subtype, 'entry_count': len(chunk_body),
            }, ''.join(chunk_body))
            suffix = f'-{chunk_idx:02d}' if chunk_idx > 0 else ''
            add_file(f'{art_dir}/items', f'{sub_slug}{suffix}.md', content, {'entry_count': len(chunk_body)})

# ── Monsters: group by MonsterTemplateID prefix ──

if art_by_type.get('monsters'):
    # MonsterTemplateID first 3 digits for grouping
    mons_by_prefix = defaultdict(list)
    for e in art_by_type['monsters']:
        mons_id = str(e['source_pk'])
        prefix = mons_id[:3] if len(mons_id) >= 3 else mons_id
        mons_by_prefix[prefix].append(e)

    for prefix, entries in sorted(mons_by_prefix.items()):
        chunk_idx = 0
        chunk_body = []
        chunk_size = 0
        for e in entries:
            name = e.get('title', '')
            chunk = f'[{e["cite_id"]}]\n**{name}**: {e["clean"]}\n\n'
            cs = len(chunk.encode('utf-8'))
            if chunk_body and (chunk_size + cs > MAX_FILE_BYTES or len(chunk_body) >= MAX_ENTRIES):
                content = fmt_md({
                    'volume': 'artifacts', 'source_table': 'MonsterConfig',
                    'template_prefix': prefix, 'entry_count': len(chunk_body),
                }, ''.join(chunk_body))
                suffix = f'-{chunk_idx:02d}' if chunk_idx > 0 else ''
                add_file(f'{art_dir}/monsters', f'mons-{prefix}{suffix}.md', content, {'entry_count': len(chunk_body)})
                chunk_idx += 1
                chunk_body = []
                chunk_size = 0
            chunk_body.append(chunk)
            chunk_size += cs
        if chunk_body:
            content = fmt_md({
                'volume': 'artifacts', 'source_table': 'MonsterConfig',
                'template_prefix': prefix, 'entry_count': len(chunk_body),
            }, ''.join(chunk_body))
            suffix = f'-{chunk_idx:02d}' if chunk_idx > 0 else ''
            add_file(f'{art_dir}/monsters', f'mons-{prefix}{suffix}.md', content, {'entry_count': len(chunk_body)})

# ── 7. rogue ─────────────────────────────────────────────────────

print("Planning rogue...")
rogue_dir = 'rogue'

rogue_by_cat = defaultdict(list)
for e in volumes['rogue']:
    if e['source_table'] in ('RogueMiracleDisplay', 'RogueTournMiracleDisplay', 'RogueMagicScepterDisplay', 'RogueTournHexDisplay'):
        rogue_by_cat['miracles'].append(e)
    elif e['source_table'] == 'RogueTournFormulaDisplay':
        rogue_by_cat['formulas'].append(e)
    else:
        rogue_by_cat['others'].append(e)

for cat, entries in sorted(rogue_by_cat.items()):
    cat_path = f'{rogue_dir}/{cat}'
    chunk_idx = 0
    chunk_body = []
    chunk_size = 0
    for e in entries:
        name = e.get('title', '')
        chunk = f'[{e["cite_id"]}]\n**{name}**: {e["clean"]}\n\n'
        cs = len(chunk.encode('utf-8'))
        if chunk_body and (chunk_size + cs > MAX_FILE_BYTES or len(chunk_body) >= MAX_ENTRIES):
            content = fmt_md({
                'volume': 'rogue', 'category': cat,
                'entry_count': len(chunk_body),
            }, ''.join(chunk_body))
            add_file(cat_path, f'{cat}-{chunk_idx:03d}.md', content, {'entry_count': len(chunk_body)})
            chunk_idx += 1
            chunk_body = []
            chunk_size = 0
        chunk_body.append(chunk)
        chunk_size += cs
    if chunk_body:
        content = fmt_md({
            'volume': 'rogue', 'category': cat,
            'entry_count': len(chunk_body),
        }, ''.join(chunk_body))
        add_file(cat_path, f'{cat}-{chunk_idx:03d}.md', content, {'entry_count': len(chunk_body)})

# ── 8. unattributed ─────────────────────────────────────────────

print("Planning unattributed...")
unattr_dir = 'unattributed'

unattr_by_prefix = defaultdict(list)
for e in volumes['unattributed']:
    pk = str(e.get('source_pk', ''))
    prefix = pk[:5] if len(pk) >= 5 else pk
    unattr_by_prefix[prefix].append(e)

UNATTR_PER_FILE = 500

for prefix, entries in sorted(unattr_by_prefix.items()):
    chunk_idx = 0
    chunk_body = []
    chunk_size = 0
    for e in entries:
        cat = e.get('meta', {}).get('text_layer', 'unclassified')
        chunk = f'[{e["cite_id"]}] [{cat}] {e.get("clean", "")}\n\n'
        cs = len(chunk.encode('utf-8'))
        if chunk_body and (chunk_size + cs > MAX_FILE_BYTES or len(chunk_body) >= UNATTR_PER_FILE):
            content = fmt_md({
                'volume': 'unattributed', 'prefix': prefix,
                'entry_count': len(chunk_body),
            }, ''.join(chunk_body))
            suffix = f'-{chunk_idx:02d}' if chunk_idx > 0 else ''
            add_file(f'{unattr_dir}/{prefix}', f'{prefix}{suffix}.md', content, {'entry_count': len(chunk_body)})
            chunk_idx += 1
            chunk_body = []
            chunk_size = 0
        chunk_body.append(chunk)
        chunk_size += cs
    if chunk_body:
        content = fmt_md({
            'volume': 'unattributed', 'prefix': prefix,
            'entry_count': len(chunk_body),
        }, ''.join(chunk_body))
        suffix = f'-{chunk_idx:02d}' if chunk_idx > 0 else ''
        add_file(f'{unattr_dir}/{prefix}', f'{prefix}{suffix}.md', content, {'entry_count': len(chunk_body)})

# ── Summary ──────────────────────────────────────────────────────

all_sizes = []
for d in plan['directories'].values():
    for f in d['files']:
        all_sizes.append(f['size_bytes'])

if all_sizes:
    plan['avg_file_bytes'] = int(sum(all_sizes) / len(all_sizes))

# Billing estimate
base_rate = 5  # AFP/hour
plan['billing'] = {
    'afp_per_hour': base_rate,
    'afp_per_day': base_rate * 24,
    'total_files': plan['total_files'],
    'under_threshold': plan['total_files'] <= 40000,
    'note': f'{base_rate} AFP/hour, files={plan["total_files"]} (< 40000 threshold)'
}

# Add collision report
plan['slug_collisions'] = _collision_count

print(f"\n{'='*60}")
print(f"DRY RUN COMPLETE")
print(f"{'='*60}")
print(f"Total files: {plan['total_files']}")
print(f"Total bytes: {plan['total_bytes']:,}")
print(f"Max file size: {plan['max_file_bytes']:,} bytes")
print(f"Avg file size: {plan['avg_file_bytes']:,} bytes")
print(f"Directories: {len(plan['directories'])}")
print(f"Slug collisions resolved: {_collision_count}")
print(f"\nDirectory distribution:")
for d in sorted(plan['directories'].keys()):
    info = plan['directories'][d]
    print(f"  {d}: {info['file_count']} files, {info['total_bytes']:,} bytes")
print(f"\nBilling: {plan['billing']['afp_per_hour']} AFP/hour, "
      f"{plan['billing']['afp_per_day']} AFP/day")

# Warning
if plan['total_files'] > 15000:
    print(f"\n⚠ WARNING: {plan['total_files']} files exceeds 15,000 threshold!")
elif plan['total_files'] > 40000:
    print(f"\n⚠ CRITICAL: {plan['total_files']} files exceeds 40,000 threshold! Rate increases!")

# Save
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(plan, f, ensure_ascii=False, indent=2)
print(f"\nPlan saved to: {OUTPUT}")
