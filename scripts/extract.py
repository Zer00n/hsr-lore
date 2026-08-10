"""
星铁语料抽取器 v1 — 白名单驱动，按 hsr-extractor-spec.md

全局约束：
  cite_id 的每一个组成部分必须来自数据内容本身，
  不得依赖行号、遍历顺序、时间戳或任何运行时状态。

  语料工程只做标记，不做删除。
  凡是要排除的内容，一律隔离到独立文件并保留完整字段。
"""
import json, os, re, hashlib, sys, io, glob

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE = r'D:\Office\claudecode\star\hsr-lore\vendor\StarRailData'
EXCEL = os.path.join(BASE, 'ExcelOutput')
TEXTMAP_PATH = os.path.join(BASE, 'TextMap', 'TextMapCHS.json')
CORPUS = r'D:\Office\claudecode\star\hsr-lore\corpus'
SAMPLES = r'D:\Office\claudecode\star\hsr-lore\samples\pending'
os.makedirs(CORPUS, exist_ok=True)
os.makedirs(SAMPLES, exist_ok=True)

# ── Load TextMap ──────────────────────────────────────────────
print("Loading TextMapCHS...")
with open(TEXTMAP_PATH, 'r', encoding='utf-8') as f:
    textmap = json.load(f)
print(f"  {len(textmap)} entries")

def resolve(hash_val):
    """Resolve a Hash reference to Chinese text. Returns None if N/A or empty."""
    if isinstance(hash_val, dict) and 'Hash' in hash_val:
        h = str(hash_val['Hash'])
        t = textmap.get(h, '')
        if t and t != 'N/A':
            return t
    return None

def load_json(name):
    with open(os.path.join(EXCEL, name), 'r', encoding='utf-8') as f:
        return json.load(f)

# ── Preload reference tables ──────────────────────────────────
print("Preloading reference tables...")

# World mapping
book_series_world = load_json('BookSeriesWorld.json')
world_map = {}  # BookSeriesWorld ID → name
for w in book_series_world:
    name = resolve(w['BookSeriesWorldTextmapID'])
    if name:
        world_map[w['BookSeriesWorld']] = name

# MainMission lookup
main_missions = load_json('MainMission.json')
mission_lookup = {}  # MainMissionID → {name, world_id, chapter_id, type}
for m in main_missions:
    mid = m['MainMissionID']
    name = resolve(m.get('Name'))
    wid = m.get('WorldID', 0)
    cid = m.get('ChapterID', 0)
    mtype = m.get('Type', '')
    mission_lookup[mid] = {
        'name': name,
        'world_id': wid,
        'chapter_id': cid,
        'type': mtype,
    }

# BookSeries lookup
book_series = load_json('BookSeriesConfig.json')
book_series_lookup = {}  # BookSeriesID → {name, comments, world_id, num}
for bs in book_series:
    bsid = bs['BookSeriesID']
    book_series_lookup[bsid] = {
        'name': resolve(bs.get('BookSeries')),
        'comments': resolve(bs.get('BookSeriesComments')),
        'world_id': bs.get('BookSeriesWorld', 0),
        'num': bs.get('BookSeriesNum', 0),
    }

# AvatarConfig lookup
avatar_config = load_json('AvatarConfig.json')
avatar_lookup = {}  # AvatarID → {name, full_name, intro}
for a in avatar_config:
    aid = a['AvatarID']
    avatar_lookup[aid] = {
        'name': resolve(a.get('AvatarName')),
        'full_name': resolve(a.get('AvatarFullName')),
        'intro': resolve(a.get('AvatarCutinIntroText')),
    }

# AvatarAtlas lookup (for camp)
avatar_atlas = load_json('AvatarAtlas.json')
avatar_atlas_lookup = {}  # AvatarID → camp_id
for a in avatar_atlas:
    avatar_atlas_lookup[a['AvatarID']] = a.get('CampID', 0)

# Story file TalkSentenceID → mission mapping
print("Building Story→Mission mapping...")
story_talk_to_mission = {}  # TalkSentenceID → mission_id
story_dir = os.path.join(BASE, 'Story')
for root, dirs, files in os.walk(story_dir):
    dir_name = os.path.basename(root)
    if not dir_name.isdigit():
        continue
    mission_id = int(dir_name)
    for fn in files:
        if not fn.endswith('.json') or fn.endswith('.layout.json'):
            continue
        with open(os.path.join(root, fn), 'r', encoding='utf-8') as f:
            data = json.load(f)
        stack = [data]
        while stack:
            obj = stack.pop()
            if isinstance(obj, dict):
                if 'TalkSentenceID' in obj:
                    story_talk_to_mission[obj['TalkSentenceID']] = mission_id
                stack.extend(obj.values())
            elif isinstance(obj, list):
                stack.extend(obj)
print(f"  {len(story_talk_to_mission)} TalkSentenceID → Mission mappings")

# PerformanceSkipOverride → mission mapping
perf_skip = load_json('PerformanceSkipOverride.json')
perf_to_mission = {}  # PerformanceID → mission_id
for p in perf_skip:
    pid = p['PerformanceID']
    pid_str = str(pid)
    if len(pid_str) >= 7:
        prefix = int(pid_str[:7])
        if prefix in mission_lookup:
            perf_to_mission[pid] = prefix
print(f"  {len(perf_to_mission)} PerformanceID → Mission mappings ({len(perf_to_mission)/len(perf_skip)*100:.1f}%)")

# Message meta lookups
message_sections = load_json('MessageSectionConfig.json')
section_lookup = {}
for s in message_sections:
    section_lookup[s['ID']] = s.get('StartMessageItemIDList', [])

message_groups = load_json('MessageGroupConfig.json')
group_lookup = {}
for g in message_groups:
    group_lookup[g['ID']] = g.get('MessageContactsID', 0)

message_contacts_camp = load_json('MessageContactsCamp.json')
camp_lookup = {}
for c in message_contacts_camp:
    camp_lookup[c['ContactsCamp']] = resolve(c.get('Name'))

# TextJoinItem lookup for {TEXTJOIN#...} resolution
text_join_items = load_json('TextJoinItem.json')
textjoin_item_lookup = {}
for tj in text_join_items:
    if 'TextJoinText' in tj:
        text = resolve(tj.get('TextJoinText'))
        if text:
            textjoin_item_lookup[tj['TextJoinItemID']] = text

# TextJoinConfig: maps TextJoinID → DefaultItem → TextJoinItem → text
text_join_configs = load_json('TextJoinConfig.json')
textjoin_lookup = {}
for tjc in text_join_configs:
    tid = tjc['TextJoinID']
    default = tjc['DefaultItem']
    if isinstance(default, int):
        text = textjoin_item_lookup.get(default, '')
        if text:
            textjoin_lookup[tid] = text
    elif isinstance(default, dict) and 'Value' in default:
        text = textjoin_item_lookup.get(default['Value'], '')
        if text:
            textjoin_lookup[tid] = text
print(f"  TextJoinItem: {len(textjoin_item_lookup)} items, TextJoinConfig: {len(textjoin_lookup)} configs")

# StoryAtlas story index
story_atlas_data = load_json('StoryAtlas.json')
# Group by AvatarID and assign story_index
from collections import defaultdict
avatar_stories = defaultdict(list)
for s in story_atlas_data:
    avatar_stories[s['AvatarID']].append(s['StoryID'])
avatar_story_index = {}
for aid, sids in avatar_stories.items():
    for i, sid in enumerate(sorted(sids)):
        avatar_story_index[(aid, sid)] = i + 1

# ── Cleaning ──────────────────────────────────────────────────
# Statistics
cleaning_stats = {
    'color_tags': 0,
    'unbreak_tags': 0,
    'u_tags': 0,
    'i_tags': 0,
    'b_tags': 0,
    'size_tags': 0,
    'align_tags': 0,
    'icon_tags': 0,
    'nickname_replaced': 0,
    'gender_variants': 0,
    'ruby_annotations': 0,
    'textid_placeholders': 0,
    'numeric_placeholders': 0,
    'newline_escapes': 0,
}

unresolved_textids = set()
numeric_placeholder_records = set()

def clean_text(text):
    """Apply cleaning rules. Returns (clean_text, annotations_list, has_gender_variant, gender_variant_text)."""
    if not text:
        return '', [], False, ''

    raw = text
    annotations = []

    # 8. \n → real newline
    if '\\n' in raw:
        cleaning_stats['newline_escapes'] += 1
        raw = raw.replace('\\n', '\n')

    # 2. <icon ...> → delete
    icon_pattern = re.compile(r'<icon\s[^>]*>')
    icon_count = len(icon_pattern.findall(raw))
    if icon_count:
        cleaning_stats['icon_tags'] += icon_count
        raw = icon_pattern.sub('', raw)

    # 5. Ruby annotations {RUBY_B#...}text{RUBY_E#}
    ruby_pattern = re.compile(r'\{RUBY_B#([^}]*)}(.*?)\{RUBY_E#([^}]*)}')
    ruby_matches = ruby_pattern.findall(raw)
    if ruby_matches:
        cleaning_stats['ruby_annotations'] += len(ruby_matches)
        for rb, body, re_ in ruby_matches:
            annotations.append({'text': body, 'ruby': rb})
        raw = ruby_pattern.sub(r'\2', raw)

    # 4. Gender variants {M#...}{F#...} and individual {M#...} / {F#...}
    gender_pattern = re.compile(r'\{M#([^}]*)}\{F#([^}]*)}')
    gender_matches = gender_pattern.findall(raw)
    gender_variant = ''
    if gender_matches:
        cleaning_stats['gender_variants'] += len(gender_matches)
        gender_variant = '|'.join([f'F:{f}' for _, f in gender_matches])
        raw = gender_pattern.sub(r'\1', raw)
    # Also handle individual {F#...} or {M#...} (not paired)
    single_f = re.findall(r'\{F#([^}]*)}', raw)
    single_m = re.findall(r'\{M#([^}]*)}', raw)
    if single_f and not gender_matches:
        cleaning_stats['gender_variants'] += len(single_f)
        if not gender_variant:
            gender_variant = '|'.join([f'F:{f}' for f in single_f])
        raw = re.sub(r'\{F#([^}]*)}', '', raw)
    if single_m and not gender_matches:
        raw = re.sub(r'\{M#([^}]*)}', '', raw)

    # 3. {NICKNAME} → 开拓者
    if '{NICKNAME}' in raw:
        cleaning_stats['nickname_replaced'] += 1
        raw = raw.replace('{NICKNAME}', '开拓者')

    # 6. {TextID#...} and {TEXTJOIN#...} - resolve TEXTJOIN, track TextID
    textid_pattern = re.compile(r'\{TextID#([^}]+)}')
    textid_matches = textid_pattern.findall(raw)
    if textid_matches:
        cleaning_stats['textid_placeholders'] += len(textid_matches)
        for tid in textid_matches:
            unresolved_textids.add(tid)
    textjoin_pattern = re.compile(r'\{TEXTJOIN#([^}]+)}')
    textjoin_matches = textjoin_pattern.findall(raw)
    if textjoin_matches:
        for tj_id in textjoin_matches:
            tj_int = int(tj_id) if tj_id.isdigit() else None
            if tj_int is not None and tj_int in textjoin_lookup:
                raw = raw.replace(f'{{TEXTJOIN#{tj_id}}}', textjoin_lookup[tj_int])
            else:
                unresolved_textids.add(f'TEXTJOIN#{tj_id}')
                cleaning_stats['textid_placeholders'] += 1

    # 7. Numeric placeholders #1[i], #2[f1], #3[f2]% etc.
    num_pattern = re.compile(r'#\d+\[[^\]]*\]')
    num_matches = num_pattern.findall(raw)
    if num_matches:
        cleaning_stats['numeric_placeholders'] += len(num_matches)

    # 1. Strip rich text tags, keep inner text
    # <color=...>text</color>
    color_count = len(re.findall(r'<color=[^>]*>', raw))
    if color_count:
        cleaning_stats['color_tags'] += color_count
        raw = re.sub(r'<color=[^>]*>', '', raw)
        raw = raw.replace('</color>', '')

    unbreak_count = len(re.findall(r'<unbreak>', raw))
    if unbreak_count:
        cleaning_stats['unbreak_tags'] += unbreak_count
        raw = re.sub(r'</?unbreak>', '', raw)

    u_count = len(re.findall(r'<u>', raw))
    if u_count:
        cleaning_stats['u_tags'] += u_count
        raw = re.sub(r'</?u>', '', raw)

    i_count = len(re.findall(r'<i>', raw))
    if i_count:
        cleaning_stats['i_tags'] += i_count
        raw = re.sub(r'</?i>', '', raw)

    b_count = len(re.findall(r'<b>', raw))
    if b_count:
        cleaning_stats['b_tags'] += b_count
        raw = re.sub(r'</?b>', '', raw)

    s_count = len(re.findall(r'<s>', raw))
    if s_count:
        raw = re.sub(r'</?s>', '', raw)

    size_count = len(re.findall(r'<size=[+\-]?\d+>', raw))
    if size_count:
        cleaning_stats['size_tags'] += size_count
        raw = re.sub(r'<size=[+\-]?\d+>', '', raw)
        raw = raw.replace('</size>', '')

    align_count = len(re.findall(r'<align=[^>]*>', raw))
    if align_count:
        cleaning_stats['align_tags'] += align_count
        raw = re.sub(r'<align=[^>]*>', '', raw)
        raw = raw.replace('</align>', '')

    # 9. Trim whitespace, compress 3+ newlines
    raw = raw.strip()
    raw = re.sub(r'\n{3,}', '\n\n', raw)

    return raw, annotations, bool(gender_matches), gender_variant


# ── Output helpers ────────────────────────────────────────────
def make_entry(cite_id, volume, source_table, source_field, source_pk,
               title, raw_text, meta, annotations=None):
    clean, anns, has_gv, gv_text = clean_text(raw_text)
    if annotations:
        anns = annotations + anns
    entry = {
        'cite_id': cite_id,
        'volume': volume,
        'source_table': source_table,
        'source_field': source_field,
        'source_pk': source_pk,
        'text_hash': hash_text(clean),
        'title': title or '',
        'raw': raw_text,
        'clean': clean,
    }
    if anns:
        entry['annotations'] = anns
    if has_gv:
        entry['gender_variant'] = gv_text
    # Only add non-empty meta keys
    if meta:
        entry['meta'] = {k: v for k, v in meta.items() if v not in (None, '', 0)}
    return entry

def hash_text(s):
    """Simple deterministic hash of the clean text."""
    return int(hashlib.md5(s.encode('utf-8')).hexdigest()[:8], 16)

def get_world_name(world_id):
    if world_id and world_id > 0:
        bsw = world_id // 100
        return world_map.get(bsw, '')
    return ''

# ── Volume writers ────────────────────────────────────────────
volume_files = {}
volume_counts = {}
volume_chars = {}

def write_volume(volume, entries):
    path = os.path.join(CORPUS, f'{volume}.jsonl')
    with open(path, 'w', encoding='utf-8') as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + '\n')
    volume_files[volume] = path
    volume_counts[volume] = len(entries)
    volume_chars[volume] = sum(len(e['clean']) for e in entries)
    print(f"  {volume}: {len(entries)} entries, {volume_chars[volume]:,} chars")

# ── EXTRACTION ─────────────────────────────────────────────────
print("\n" + "=" * 60)
print("EXTRACTING")

# Isolation containers (mark, don't delete — project rule)
speakerless_entries = []
excluded_ip_entries = []

# ── 3.1 Lore ──────────────────────────────────────────────────
print("\n[3.1] Lore & Encyclopedia")
lore_entries = []

# NounAtlas
data = load_json('NounAtlas.json')
for n in data:
    title = resolve(n.get('NounTitle')) or ''
    desc = resolve(n.get('NounDesc')) or ''
    if desc:
        lore_entries.append(make_entry(
            f"NOUN-{n.get('NounTitle', {}).get('Hash', n.get('Type', ''))}",
            'lore', 'NounAtlas', 'NounDesc', n.get('Type', ''),
            title, desc, {},
        ))

# TitanAtlas
data = load_json('TitanAtlas.json')
for t in data:
    name = resolve(t.get('TitanName')) or ''
    desc = resolve(t.get('TitanDesc')) or ''
    if desc:
        lore_entries.append(make_entry(
            f"TITN-{t['TitanID']}", 'lore', 'TitanAtlas', 'TitanDesc',
            t['TitanID'], name, desc, {},
        ))

# TitanAtlasGroup
data = load_json('TitanAtlasGroup.json')
for t in data:
    name = resolve(t.get('TitanGroupName')) or ''
    desc = resolve(t.get('TitanGroupDesc')) or ''
    if desc:
        lore_entries.append(make_entry(
            f"TITN-G{t['TitanGroupID']}", 'lore', 'TitanAtlasGroup', 'TitanGroupDesc',
            t['TitanGroupID'], name, desc, {},
        ))

# RogueAeonStoryConfig
data = load_json('RogueAeonStoryConfig.json')
for a in data:
    name = resolve(a.get('AeonStory_Name')) or ''
    story = resolve(a.get('AeonStory')) or ''
    if story:
        lore_entries.append(make_entry(
            f"AEON-{a['RogueAeonID']}-{a['AeonStoryID']}", 'lore', 'RogueAeonStoryConfig', 'AeonStory',
            a['AeonStoryID'], name, story, {},
        ))

# RogueAeonDisplay
data = load_json('RogueAeonDisplay.json')
for a in data:
    name = resolve(a.get('RogueAeonName')) or ''
    path_name = resolve(a.get('RogueAeonPathName')) or ''
    if name:
        lore_entries.append(make_entry(
            f"AEON-D{a['DisplayID']}", 'lore', 'RogueAeonDisplay', 'RogueAeonName',
            a['DisplayID'], name, name,
            {'path_name': path_name} if path_name else {},
        ))

# BookSeriesWorld
data = load_json('BookSeriesWorld.json')
for w in data:
    name = resolve(w['BookSeriesWorldTextmapID']) or ''
    if name:
        lore_entries.append(make_entry(
            f"WRLD-{w['BookSeriesWorld']}", 'lore', 'BookSeriesWorld', 'BookSeriesWorldTextmapID',
            w['BookSeriesWorld'], name, name, {},
        ))

# LoadingDesc
data = load_json('LoadingDesc.json')
for ld in data:
    desc = resolve(ld.get('DescTextmapID')) or ''
    if desc:
        lore_entries.append(make_entry(
            f"LOAD-{ld['ID']}", 'lore', 'LoadingDesc', 'DescTextmapID',
            ld['ID'], desc[:40], desc, {},
        ))

write_volume('lore', lore_entries)

# ── 3.2 Books ─────────────────────────────────────────────────
print("\n[3.2] Books")
book_entries = []

# LocalbookConfig
data = load_json('LocalbookConfig.json')
for b in data:
    name = resolve(b.get('BookInsideName')) or ''
    content = resolve(b.get('BookContent')) or ''
    bid = b['BookID']
    bsid = b.get('BookSeriesID', 0)
    bs_info = book_series_lookup.get(bsid, {})
    world_id = bs_info.get('world_id', 0)
    world_name = get_world_name(world_id)
    meta = {
        'book_series_id': bsid if bsid else None,
        'book_series_name': bs_info.get('name'),
        'series_num': b.get('BookSeriesInsideID'),
        'world_id': world_id if world_id else None,
        'world_name': world_name if world_name else None,
    }
    if content:
        book_entries.append(make_entry(
            f"BOOK-{bid}", 'books', 'LocalbookConfig', 'BookContent',
            bid, name, content, meta,
        ))

# BookSeriesConfig
data = load_json('BookSeriesConfig.json')
for bs in data:
    name = resolve(bs.get('BookSeries')) or ''
    comments = resolve(bs.get('BookSeriesComments')) or ''
    bsid = bs['BookSeriesID']
    world_id = bs.get('BookSeriesWorld', 0)
    world_name = get_world_name(world_id)
    meta = {
        'book_series_name': name,  # BSER is the series itself
        'world_id': world_id if world_id else None,
        'world_name': world_name if world_name else None,
        'series_num': bs.get('BookSeriesNum', 0),
    }
    if comments:
        book_entries.append(make_entry(
            f"BSER-{bsid}", 'books', 'BookSeriesConfig', 'BookSeriesComments',
            bsid, name, comments, meta,
        ))

write_volume('books', book_entries)

# ── 3.3 Characters ────────────────────────────────────────────
print("\n[3.3] Characters")
char_entries = []

# StoryAtlas
data = load_json('StoryAtlas.json')
for s in data:
    story = resolve(s.get('Story')) or ''
    aid = s['AvatarID']
    sid = s['StoryID']
    av_info = avatar_lookup.get(aid, {})
    av_name = av_info.get('name') or ''
    camp_id = avatar_atlas_lookup.get(aid, 0)
    story_idx = avatar_story_index.get((aid, sid), 0)
    meta = {
        'avatar_id': aid,
        'avatar_name': av_name,
        'story_index': story_idx,
        'camp_id': camp_id,
    }
    if story:
        char_entries.append(make_entry(
            f"STRY-{aid}-{sid}", 'characters', 'StoryAtlas', 'Story',
            aid, f"{av_name} 故事{story_idx}", story, meta,
        ))

# VoiceAtlas
data = load_json('VoiceAtlas.json')
print(f"  VoiceAtlas: {len(data)} total records")

# Exclusion rule: only exclude AvatarIDs NOT in AvatarConfig
# These are Fate collab characters (1014, 1015, 1508, 1509) and any other non-playable entities
avatar_config_ids = set(a['AvatarID'] for a in avatar_config)
excluded_avatar_ids = set()
voice_filtered_out = 0
voice_kept = 0
voice_excluded_samples = []
for v in data:
    aid = v['AvatarID']
    voice_text = resolve(v.get('Voice_M')) or ''
    title = resolve(v.get('VoiceTitle')) or ''

    if aid not in avatar_config_ids:
        excluded_avatar_ids.add(aid)
        voice_filtered_out += 1
        if len(voice_excluded_samples) < 20:
            voice_excluded_samples.append((aid, title, voice_text[:80]))
        # Collect for excluded_ip isolation (mark, don't delete)
        excluded_ip_entries.append(make_entry(
            f"VOIC-{aid}-{v['VoiceID']}", 'excluded_ip', 'VoiceAtlas', 'Voice_M',
            aid, f"VoiceAtlas-only-{aid} - {title}", voice_text,
            {'exclusion_reason': 'AvatarID not in AvatarConfig (Fate collab IP)'},
        ))
        continue

    av_info = avatar_lookup.get(aid, {})
    av_name = av_info.get('name') or ''
    camp_id = avatar_atlas_lookup.get(aid, 0)
    meta = {
        'avatar_id': aid,
        'avatar_name': av_name,
        'voice_title': title,
        'camp_id': camp_id,
    }
    if voice_text:
        char_entries.append(make_entry(
            f"VOIC-{aid}-{v['VoiceID']}", 'characters', 'VoiceAtlas', 'Voice_M',
            aid, f"{av_name} - {title}", voice_text, meta,
        ))
        voice_kept += 1

# Collect excluded avatar names from VoiceAtlas (not in AvatarConfig, so no AvatarConfig name)
fate_avatar_names = {}
for aid in excluded_avatar_ids:
    fate_avatar_names[aid] = f'VoiceAtlas-only-{aid}'

print(f"  VoiceAtlas kept: {voice_kept}, filtered out: {voice_filtered_out}")
print(f"  Excluded AvatarIDs (not in AvatarConfig): {sorted(excluded_avatar_ids)}")

# AvatarConfig
data = load_json('AvatarConfig.json')
for a in data:
    aid = a['AvatarID']
    name = resolve(a.get('AvatarName')) or ''
    full_name = resolve(a.get('AvatarFullName')) or ''
    intro = resolve(a.get('AvatarCutinIntroText')) or ''
    camp_id = avatar_atlas_lookup.get(aid, 0)
    meta = {
        'avatar_id': aid,
        'camp_id': camp_id,
    }
    if name:
        char_entries.append(make_entry(
            f"AVTR-N-{aid}", 'characters', 'AvatarConfig', 'AvatarName',
            aid, name, name, meta,
        ))
    if full_name:
        char_entries.append(make_entry(
            f"AVTR-F-{aid}", 'characters', 'AvatarConfig', 'AvatarFullName',
            aid, full_name, full_name, meta,
        ))
    if intro:
        char_entries.append(make_entry(
            f"AVTR-I-{aid}", 'characters', 'AvatarConfig', 'AvatarCutinIntroText',
            aid, f"{name} 登场介绍", intro, meta,
        ))

write_volume('characters', char_entries)

# ── 3.4 Narrative ─────────────────────────────────────────────
print("\n[3.4] Narrative")
narrative_entries = []

# ChronicleConclusion — propagate world_id via MissionID
data = load_json('ChronicleConclusion.json')
for c in data:
    text = resolve(c.get('MissionConclusion')) or ''
    mid = c['MissionID']
    m_info = mission_lookup.get(mid, {})
    meta = {}
    if m_info:
        meta['main_mission_id'] = mid
        if m_info.get('name'):
            meta['mission_name'] = m_info['name']
        wid = m_info.get('world_id', 0)
        if wid:
            meta['world_id'] = wid
            wn = get_world_name(wid)
            if wn:
                meta['world_name'] = wn
    if text:
        narrative_entries.append(make_entry(
            f"CHRN-{mid}", 'narrative', 'ChronicleConclusion', 'MissionConclusion',
            mid, text[:40], text, meta,
        ))

# PerformanceSkipOverride
data = load_json('PerformanceSkipOverride.json')
for p in data:
    text = resolve(p.get('Desc')) or ''
    pid = p['PerformanceID']
    mid = perf_to_mission.get(pid, 0)
    m_info = mission_lookup.get(mid, {})
    meta = {}
    if mid:
        meta['main_mission_id'] = mid
        if m_info.get('name'):
            meta['mission_name'] = m_info['name']
        if m_info.get('type'):
            meta['mission_type'] = m_info['type']
        wid = m_info.get('world_id', 0)
        if wid:
            meta['world_id'] = wid
            wn = get_world_name(wid)
            if wn:
                meta['world_name'] = wn
    if text:
        narrative_entries.append(make_entry(
            f"SKIP-{p['PerformanceType']}-{pid}", 'narrative', 'PerformanceSkipOverride', 'Desc',
            pid, text[:40], text, meta,
        ))

# MainMission
data = load_json('MainMission.json')
for m in data:
    name = resolve(m.get('Name')) or ''
    mid = m['MainMissionID']
    wid = m.get('WorldID', 0)
    meta = {
        'main_mission_id': mid,
        'mission_type': m.get('Type', ''),
        'chapter_id': m.get('ChapterID', 0),
        'world_id': wid,
        'world_name': get_world_name(wid),
    }
    if name:
        narrative_entries.append(make_entry(
            f"MAIN-{mid}", 'narrative', 'MainMission', 'Name',
            mid, name, name, meta,
        ))

# SubMission — add mission attribution via ID prefix
data = load_json('SubMission.json')
sub_attributed = 0
sub_unattributed = 0
for s in data:
    target = resolve(s.get('TargetText')) or ''
    desc = resolve(s.get('DescrptionText')) or ''
    sid = s['SubMissionID']
    # Attribute via 7-digit prefix to MainMission
    sid_str = str(sid)
    mid = 0
    meta = {}
    if len(sid_str) >= 7:
        prefix = int(sid_str[:7])
        m_info = mission_lookup.get(prefix)
        if m_info:
            mid = prefix
            meta['main_mission_id'] = mid
            if m_info.get('name'):
                meta['mission_name'] = m_info['name']
            if m_info.get('type'):
                meta['mission_type'] = m_info['type']
            wid = m_info.get('world_id', 0)
            if wid:
                meta['world_id'] = wid
                wn = get_world_name(wid)
                if wn:
                    meta['world_name'] = wn
            sub_attributed += 1
        else:
            sub_unattributed += 1
    else:
        sub_unattributed += 1
    if target:
        narrative_entries.append(make_entry(
            f"SUBM-T-{sid}", 'narrative', 'SubMission', 'TargetText',
            sid, target[:40], target, meta,
        ))
    if desc:
        narrative_entries.append(make_entry(
            f"SUBM-D-{sid}", 'narrative', 'SubMission', 'DescrptionText',
            sid, desc[:40], desc, meta,
        ))

print(f"  SubMission attributed: {sub_attributed}/{sub_attributed+sub_unattributed} ({sub_attributed/(sub_attributed+sub_unattributed)*100:.1f}%)")

# TalkSentenceConfig - dialogue attributable to missions
data = load_json('TalkSentenceConfig.json')
talks_attributable = 0
talks_attributable_with_speaker = 0
talks_without_speaker = 0
talks_without_speaker_samples = []
for t in data:
    if 'TalkSentenceText' not in t:
        continue
    tid = t['TalkSentenceID']
    text = resolve(t.get('TalkSentenceText')) or ''
    speaker = resolve(t.get('TextmapTalkSentenceName')) or ''

    if tid in story_talk_to_mission:
        mid = story_talk_to_mission[tid]
        m_info = mission_lookup.get(mid, {})
        wid = m_info.get('world_id', 0)
        meta = {
            'mission_id': mid,
            'mission_name': m_info.get('name'),
            'world_id': wid,
            'world_name': get_world_name(wid),
        }
        if speaker:
            meta['speaker'] = speaker
            talks_attributable_with_speaker += 1
        if text:
            narrative_entries.append(make_entry(
                f"TALK-{tid}", 'narrative', 'TalkSentenceConfig', 'TalkSentenceText',
                tid, text[:40], text, meta,
            ))
            talks_attributable += 1

print(f"  Narrative dialog (attributable): {talks_attributable} (with speaker: {talks_attributable_with_speaker})")

write_volume('narrative', narrative_entries)

# ── 3.5 Dialogue & Messages ───────────────────────────────────
print("\n[3.5] Dialogue & Messages")
dialogue_entries = []

# TalkSentenceConfig - all remaining with speaker (skip narrative-attributed)
talks_in_narrative = set()
for e in narrative_entries:
    if e['source_table'] == 'TalkSentenceConfig':
        talks_in_narrative.add(e['source_pk'])

data = load_json('TalkSentenceConfig.json')
for t in data:
    if 'TalkSentenceText' not in t:
        continue
    tid = t['TalkSentenceID']
    text = resolve(t.get('TalkSentenceText')) or ''
    speaker = resolve(t.get('TextmapTalkSentenceName')) or ''

    if not speaker:
        talks_without_speaker += 1
        if len(talks_without_speaker_samples) < 20:
            talks_without_speaker_samples.append((tid, text[:120]))
        # Collect for speakerless isolation (mark, don't delete)
        speakerless_entries.append(make_entry(
            f"TALK-{tid}", 'speakerless', 'TalkSentenceConfig', 'TalkSentenceText',
            tid, text[:40], text, {'speaker_status': 'absent'},
        ))
        continue

    # Skip if already in narrative volume
    if tid in story_talk_to_mission:
        continue

    if text:
        dialogue_entries.append(make_entry(
            f"TALK-{tid}", 'dialogue', 'TalkSentenceConfig', 'TalkSentenceText',
            tid, text[:40], text, {'speaker': speaker},
        ))

print(f"  Talks without speaker (isolated to speakerless): {talks_without_speaker}")
print(f"  Dialogue volume talks: {len(dialogue_entries)}")

# MessageItemConfig
data = load_json('MessageItemConfig.json')
for m in data:
    text = resolve(m.get('MainText')) or ''
    mid = m['ID']
    sender = m.get('Sender', '')
    section_id = m.get('SectionID', 0)
    meta = {'sender': sender}
    if section_id:
        meta['section_id'] = section_id
    if text:
        dialogue_entries.append(make_entry(
            f"MSG-{mid}", 'dialogue', 'MessageItemConfig', 'MainText',
            mid, text[:40], text, meta,
        ))

# MessageContactsConfig
data = load_json('MessageContactsConfig.json')
for c in data:
    name = resolve(c.get('Name')) or ''
    sig = resolve(c.get('SignatureText')) or ''
    cid = c['ID']
    camp = c.get('ContactsCamp', 0)
    camp_name = camp_lookup.get(camp, '')
    meta = {'contacts_camp': camp, 'camp_name': camp_name} if camp_name else {}
    if name:
        dialogue_entries.append(make_entry(
            f"CTAC-N-{cid}", 'dialogue', 'MessageContactsConfig', 'Name',
            cid, name, name, meta,
        ))
    if sig:
        dialogue_entries.append(make_entry(
            f"CTAC-S-{cid}", 'dialogue', 'MessageContactsConfig', 'SignatureText',
            cid, sig[:40], sig, meta,
        ))

write_volume('dialogue', dialogue_entries)

# ── 3.6 Artifacts ─────────────────────────────────────────────
print("\n[3.6] Artifacts & Creatures")
artifact_entries = []

# ItemConfig
data = load_json('ItemConfig.json')
for it in data:
    name = resolve(it.get('ItemName')) or ''
    bgdesc = resolve(it.get('ItemBGDesc')) or ''
    iid = it['ID']
    meta = {'item_name': name, 'rarity': it.get('Rarity', '')}
    if bgdesc:
        artifact_entries.append(make_entry(
            f"ITEM-{iid}", 'artifacts', 'ItemConfig', 'ItemBGDesc',
            iid, name, bgdesc, meta,
        ))

# ItemConfigEquipment
data = load_json('ItemConfigEquipment.json')
for eq in data:
    name = resolve(eq.get('ItemName')) or ''
    desc = resolve(eq.get('ItemDesc')) or ''
    bgdesc = resolve(eq.get('ItemBGDesc')) or ''
    eid = eq['ID']
    meta = {'item_name': name, 'rarity': eq.get('Rarity', '')}
    if desc:
        artifact_entries.append(make_entry(
            f"EQUP-D-{eid}", 'artifacts', 'ItemConfigEquipment', 'ItemDesc',
            eid, name, desc, meta,
        ))
    if bgdesc:
        artifact_entries.append(make_entry(
            f"EQUP-B-{eid}", 'artifacts', 'ItemConfigEquipment', 'ItemBGDesc',
            eid, name, bgdesc, meta,
        ))

# ItemConfigRelic
data = load_json('ItemConfigRelic.json')
for r in data:
    name = resolve(r.get('ItemName')) or ''
    bgdesc = resolve(r.get('ItemBGDesc')) or ''
    rid = r['ID']
    meta = {'item_name': name, 'rarity': r.get('Rarity', '')}
    if bgdesc:
        artifact_entries.append(make_entry(
            f"RELC-{rid}", 'artifacts', 'ItemConfigRelic', 'ItemBGDesc',
            rid, name, bgdesc, meta,
        ))

# ItemConfigDisk
data = load_json('ItemConfigDisk.json')
for d in data:
    name = resolve(d.get('ItemName')) or ''
    desc = resolve(d.get('ItemDesc')) or ''
    did = d['ID']
    meta = {'item_name': name, 'rarity': d.get('Rarity', '')}
    if desc:
        artifact_entries.append(make_entry(
            f"DISK-{did}", 'artifacts', 'ItemConfigDisk', 'ItemDesc',
            did, name, desc, meta,
        ))

# MonsterConfig
data = load_json('MonsterConfig.json')
for m in data:
    name = resolve(m.get('MonsterName')) or ''
    intro = resolve(m.get('MonsterIntroduction')) or ''
    mid = m['MonsterID']
    meta = {'item_name': name}
    if intro:
        artifact_entries.append(make_entry(
            f"MONS-{mid}", 'artifacts', 'MonsterConfig', 'MonsterIntroduction',
            mid, name, intro, meta,
        ))

write_volume('artifacts', artifact_entries)

# ── 3.7 Rogue ─────────────────────────────────────────────────
print("\n[3.7] Simulated Universe")
rogue_entries = []

# RogueMiracleDisplay
data = load_json('RogueMiracleDisplay.json')
for r in data:
    name = resolve(r.get('MiracleName')) or ''
    bgdesc = resolve(r.get('MiracleBGDesc')) or ''
    if bgdesc:
        rogue_entries.append(make_entry(
            f"MIRC-{r['MiracleDisplayID']}", 'rogue', 'RogueMiracleDisplay', 'MiracleBGDesc',
            r['MiracleDisplayID'], name, bgdesc, {},
        ))

# RogueTournMiracleDisplay
data = load_json('RogueTournMiracleDisplay.json')
for r in data:
    name = resolve(r.get('MiracleName')) or ''
    bgdesc = resolve(r.get('MiracleBGDesc')) or ''
    if bgdesc:
        rogue_entries.append(make_entry(
            f"MIRC-T{r['MiracleDisplayID']}", 'rogue', 'RogueTournMiracleDisplay', 'MiracleBGDesc',
            r['MiracleDisplayID'], name, bgdesc, {},
        ))

# RogueTournFormulaDisplay
data = load_json('RogueTournFormulaDisplay.json')
for f in data:
    story = resolve(f.get('FormulaStory')) or ''
    if story:
        rogue_entries.append(make_entry(
            f"FRML-{f['FormulaDisplayID']}", 'rogue', 'RogueTournFormulaDisplay', 'FormulaStory',
            f['FormulaDisplayID'], story[:40], story, {},
        ))

# RogueMagicScepterDisplay
data = load_json('RogueMagicScepterDisplay.json')
for s in data:
    name = resolve(s.get('ScepterName')) or ''
    bgdesc = resolve(s.get('ScepterBGDesc')) or ''
    if bgdesc:
        rogue_entries.append(make_entry(
            f"MIRC-S{s['ScepterID']}", 'rogue', 'RogueMagicScepterDisplay', 'ScepterBGDesc',
            s['ScepterID'], name, bgdesc, {},
        ))

# RogueTournHexDisplay
data = load_json('RogueTournHexDisplay.json')
for h in data:
    name = resolve(h.get('Name')) or ''
    bgdesc = resolve(h.get('BgDesc')) or ''
    if bgdesc:
        rogue_entries.append(make_entry(
            f"MIRC-H{h['HexDisplayID']}", 'rogue', 'RogueTournHexDisplay', 'BgDesc',
            h['HexDisplayID'], name, bgdesc, {},
        ))

write_volume('rogue', rogue_entries)

# ── 3.8 Pending ───────────────────────────────────────────────
print("\n[3.8] Pending review samples")

# MappingInfo
data = load_json('MappingInfo.json')
samples = []
for m in data[:30]:
    text = resolve(m.get('Desc')) or ''
    samples.append({'source': 'MappingInfo', 'id': m['ID'], 'field': 'Desc', 'text': text})
with open(os.path.join(SAMPLES, 'mapping_info.json'), 'w', encoding='utf-8') as f:
    json.dump(samples, f, ensure_ascii=False, indent=2)

# ItemCureInfoData
data = load_json('ItemCureInfoData.json')
samples = []
for m in data[:30]:
    text = resolve(m.get('CureInfoDesc')) or ''
    samples.append({'source': 'ItemCureInfoData', 'id': m['ID'], 'field': 'CureInfoDesc', 'text': text})
with open(os.path.join(SAMPLES, 'item_cure_info.json'), 'w', encoding='utf-8') as f:
    json.dump(samples, f, ensure_ascii=False, indent=2)

# TarotBookSentence
data = load_json('TarotBookSentence.json')
samples = []
for m in data[:30]:
    text = resolve(m.get('Sentence')) or ''
    samples.append({'source': 'TarotBookSentence', 'id': m['ID'], 'field': 'Sentence', 'text': text})
with open(os.path.join(SAMPLES, 'tarot_book_sentence.json'), 'w', encoding='utf-8') as f:
    json.dump(samples, f, ensure_ascii=False, indent=2)

# LimaoNews series
for fname in ['LimaoNewsPost.json', 'LimaoNewsInterviewContent.json', 'LimaoNewsComment.json']:
    try:
        data = load_json(fname)
        samples = []
        for m in data[:30]:
            # Find text fields (obfuscated names)
            text_fields = {}
            for k, v in m.items():
                if isinstance(v, dict) and 'Hash' in v:
                    text_fields[k] = resolve(v) or ''
            samples.append({'source': fname, 'id': m.get(list(m.keys())[0], ''), 'fields': text_fields})
        with open(os.path.join(SAMPLES, fname.replace('.json', '_sample.json')), 'w', encoding='utf-8') as f:
            json.dump(samples, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"  {fname}: ERROR {e}")

print(f"  Pending samples saved to {SAMPLES}/")

# ── Fate collab isolation (mark, don't delete) ─────────────────
# Move Fate collab entries from main volumes to excluded_ip
fate_speakers = {
    '远坂凛', 'Saber', '吉尔伽美什', 'Lancer', 'Archer', '伊什塔尔',
    'Caster', 'Assassin', '远坂凛&Saber', '谜之Archer', '白厄&Saber', '遐蝶&远坂凛',
    '伊什塔尔•胡姆巴巴-艾格勒',
}
fate_mission_ids = {8034201, 8034202, 8034203}
fate_artifact_ids = {'ITEM-250608', 'ITEM-140615', 'EQUP-B-23061'}
fate_speakerless_kw = ['圣杯战争', '拟似圣杯', 'Saber', 'Archer', 'Lancer', 'Caster', 'Assassin',
                       '远坂凛', '吉尔伽美什', '伊什塔尔', '职阶', '令咒', '御主', '从者', 'Rider']

# Move from dialogue
new_dialogue = []
for e in dialogue_entries:
    sp = e.get('meta', {}).get('speaker', '')
    if sp in fate_speakers:
        reason = 'Fate collab IP: composite speaker (%s)' % sp if '&' in sp else 'Fate collab IP: speaker not in AvatarConfig (%s)' % sp
        e['meta']['exclusion_reason'] = reason
        excluded_ip_entries.append(e)
    else:
        new_dialogue.append(e)
dialogue_entries = new_dialogue

# Move from narrative
new_narrative = []
for e in narrative_entries:
    mid = e.get('meta', {}).get('mission_id', 0)
    if mid in fate_mission_ids:
        e['meta']['exclusion_reason'] = 'Fate collab IP: mission_id=%d (Fate crossover event)' % mid
        excluded_ip_entries.append(e)
    else:
        new_narrative.append(e)
narrative_entries = new_narrative

# Move from speakerless
new_speakerless = []
for e in speakerless_entries:
    clean = e.get('clean', '')
    if any(kw in clean for kw in fate_speakerless_kw):
        e['meta']['exclusion_reason'] = 'Fate collab IP: text contains Fate-specific keywords'
        excluded_ip_entries.append(e)
    else:
        new_speakerless.append(e)
speakerless_entries = new_speakerless

# Move from artifacts
new_artifacts = []
for e in artifact_entries:
    if e['cite_id'] in fate_artifact_ids:
        e['meta']['exclusion_reason'] = 'Fate collab IP: artifact references Fate content'
        excluded_ip_entries.append(e)
    else:
        new_artifacts.append(e)
artifact_entries = new_artifacts

print(f"  Fate isolation: moved to excluded_ip — dialogue, narrative, speakerless, artifacts")

# Recalculate volume counts after isolation
volume_counts['dialogue'] = len(dialogue_entries)
volume_chars['dialogue'] = sum(len(e['clean']) for e in dialogue_entries)
volume_counts['narrative'] = len(narrative_entries)
volume_chars['narrative'] = sum(len(e['clean']) for e in narrative_entries)
volume_counts['artifacts'] = len(artifact_entries)
volume_chars['artifacts'] = sum(len(e['clean']) for e in artifact_entries)

# Rewrite affected volumes
for vol_name, entries in [('dialogue', dialogue_entries), ('narrative', narrative_entries),
                           ('artifacts', artifact_entries)]:
    vol_path = os.path.join(CORPUS, f'{vol_name}.jsonl')
    with open(vol_path, 'w', encoding='utf-8') as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + '\n')

# ── Isolation outputs (mark, don't delete) ─────────────────────
print("\nWriting isolation outputs...")

# Speakerless dialogue
if speakerless_entries:
    sp_path = os.path.join(CORPUS, 'speakerless.jsonl')
    with open(sp_path, 'w', encoding='utf-8') as f:
        for e in speakerless_entries:
            f.write(json.dumps(e, ensure_ascii=False) + '\n')
    print(f"  speakerless.jsonl: {len(speakerless_entries)} entries")

# Excluded IP (Fate collab voice lines)
if excluded_ip_entries:
    ip_path = os.path.join(CORPUS, 'excluded_ip.jsonl')
    with open(ip_path, 'w', encoding='utf-8') as f:
        for e in excluded_ip_entries:
            f.write(json.dumps(e, ensure_ascii=False) + '\n')
    print(f"  excluded_ip.jsonl: {len(excluded_ip_entries)} entries")

# ── Hard assertion: cite_id uniqueness ─────────────────────────
# cite_id 的每一个组成部分必须来自数据内容本身，
# 不得依赖行号、遍历顺序、时间戳或任何运行时状态。
print("\nChecking cite_id uniqueness...")
all_entries = []
for vol in ['lore', 'books', 'characters', 'narrative', 'dialogue', 'artifacts', 'rogue']:
    vol_path = os.path.join(CORPUS, f'{vol}.jsonl')
    if os.path.exists(vol_path):
        with open(vol_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    all_entries.append(json.loads(line))

from collections import Counter
cite_ids = [e['cite_id'] for e in all_entries]
dupes = {k: v for k, v in Counter(cite_ids).items() if v > 1}
if dupes:
    print(f"FATAL: {len(dupes)} duplicate cite_ids found!")
    for cid, cnt in sorted(dupes.items(), key=lambda x: -x[1])[:10]:
        print(f"  {cid}: {cnt}")
    raise SystemExit(f"cite_id uniqueness check FAILED: {len(dupes)} duplicates")
print(f"  All {len(cite_ids)} cite_ids unique ✓")

# ── Index ──────────────────────────────────────────────────────
print("\nWriting index...")
index = {}
total_chars = 0
total_entries = 0
for vol in ['lore', 'books', 'characters', 'narrative', 'dialogue', 'artifacts', 'rogue']:
    index[vol] = {
        'entries': volume_counts.get(vol, 0),
        'chars': volume_chars.get(vol, 0),
        'estimated_tokens': int(volume_chars.get(vol, 0) * 0.75),
    }
    total_entries += index[vol]['entries']
    total_chars += index[vol]['chars']

# Add isolation volumes to index (separate line, not in main total)
index['speakerless'] = {
    'entries': len(speakerless_entries),
    'chars': sum(len(e['clean']) for e in speakerless_entries),
    'estimated_tokens': int(sum(len(e['clean']) for e in speakerless_entries) * 0.75),
    'note': 'Isolated: TalkSentenceConfig entries without speaker name (player options, narration, system text)'
}
index['excluded_ip'] = {
    'entries': len(excluded_ip_entries),
    'chars': sum(len(e['clean']) for e in excluded_ip_entries),
    'estimated_tokens': int(sum(len(e['clean']) for e in excluded_ip_entries) * 0.75),
    'note': 'Isolated: VoiceAtlas entries for AvatarIDs not in AvatarConfig (Fate collab IP)'
}

index['total'] = {
    'entries': total_entries,
    'chars': total_chars,
    'estimated_tokens': int(total_chars * 0.75),
}

with open(os.path.join(CORPUS, 'index.json'), 'w', encoding='utf-8') as f:
    json.dump(index, f, ensure_ascii=False, indent=2)

print(f"\n{'='*60}")
print(f"EXTRACTION COMPLETE")
print(f"Total entries: {total_entries:,}")
print(f"Total chars: {total_chars:,}")
print(f"Estimated tokens: {int(total_chars * 0.75):,}")

# ── Save stats for report ─────────────────────────────────────
stats = {
    'cleaning': cleaning_stats,
    'unresolved_textids': sorted(unresolved_textids),
    'voice_excluded_samples': voice_excluded_samples,
    'talks_without_speaker': talks_without_speaker,
    'talks_without_speaker_samples': talks_without_speaker_samples,
    'fate_avatar_names': fate_avatar_names,
    'voice_filtered_out': voice_filtered_out,
    'voice_kept': voice_kept,
}

with open(r'D:\Office\claudecode\star\hsr-lore\work\extraction_stats.json', 'w', encoding='utf-8') as f:
    json.dump(stats, f, ensure_ascii=False, indent=2)

print("\nStats saved to work/extraction_stats.json")
print("Done!")