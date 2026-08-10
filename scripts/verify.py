"""
星铁语料抽取器验证脚本 v2
三项测试：反查测试（按 cite_id 组合键）、残留标记检查、幂等测试
"""
import json, os, sys, io, random, hashlib, re, glob

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = r'D:\Office\claudecode\star\hsr-lore\vendor\StarRailData'
EXCEL = os.path.join(BASE, 'ExcelOutput')
TEXTMAP_PATH = os.path.join(BASE, 'TextMap', 'TextMapCHS.json')
CORPUS = r'D:\Office\claudecode\star\hsr-lore\corpus'

print("Loading TextMapCHS...")
with open(TEXTMAP_PATH, 'r', encoding='utf-8') as f:
    textmap = json.load(f)

# ── cite_id → record lookup strategy ──────────────────────────
# Each strategy: (table_name, match_fn(record, cite_parts) -> bool, resolve_fn(record, source_field) -> str)
# cite_parts = cite_id.split('-')

def load_table(name):
    path = os.path.join(EXCEL, name)
    if not os.path.exists(path):
        path = os.path.join(EXCEL, name + '.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def resolve_text(record, field):
    """Resolve a field to its text value, handling Hash references."""
    parts = field.split('.')
    val = record
    for p in parts:
        if isinstance(val, dict) and p in val:
            val = val[p]
        else:
            return ''
    if isinstance(val, dict) and 'Hash' in val:
        return textmap.get(str(val['Hash']), '')
    return str(val) if val else ''

def find_record(data, match_fn):
    """Find a record in a list by match function."""
    if isinstance(data, list):
        for r in data:
            if isinstance(r, dict) and match_fn(r):
                return r
    return None

# Lookup strategies keyed by TYPE prefix
LOOKUP = {
    'NOUN': lambda parts: ('NounAtlas.json', load_table('NounAtlas.json'),
        lambda r: str(r.get('NounTitle', {}).get('Hash', '')) == parts[1]),
    'TITN': lambda parts: ('TitanAtlasGroup.json' if parts[1].startswith('G') else 'TitanAtlas.json',
        load_table('TitanAtlas.json' if not parts[1].startswith('G') else 'TitanAtlasGroup.json'),
        lambda r: (r.get('TitanGroupID') == int(parts[1][1:]) if parts[1].startswith('G')
                   else r.get('TitanID') == int(parts[1]))),
    'AEON': lambda parts: ('RogueAeonDisplay.json' if parts[1].startswith('D') else 'RogueAeonStoryConfig.json',
        load_table('RogueAeonDisplay.json' if parts[1].startswith('D') else 'RogueAeonStoryConfig.json'),
        lambda r: (r.get('DisplayID') == int(parts[1][1:]) if parts[1].startswith('D')
                   else r.get('RogueAeonID') == int(parts[1]) and r.get('AeonStoryID') == int(parts[2]))),
    'WRLD': lambda parts: ('BookSeriesWorld.json', load_table('BookSeriesWorld.json'),
        lambda r: r.get('BookSeriesWorld') == int(parts[1])),
    'LOAD': lambda parts: ('LoadingDesc.json', load_table('LoadingDesc.json'),
        lambda r: r.get('ID') == int(parts[1])),
    'BOOK': lambda parts: ('LocalbookConfig.json', load_table('LocalbookConfig.json'),
        lambda r: r.get('BookID') == int(parts[1])),
    'BSER': lambda parts: ('BookSeriesConfig.json', load_table('BookSeriesConfig.json'),
        lambda r: r.get('BookSeriesID') == int(parts[1])),
    'STRY': lambda parts: ('StoryAtlas.json', load_table('StoryAtlas.json'),
        lambda r: r.get('AvatarID') == int(parts[1]) and r.get('StoryID') == int(parts[2])),
    'VOIC': lambda parts: ('VoiceAtlas.json', load_table('VoiceAtlas.json'),
        lambda r: r.get('AvatarID') == int(parts[1]) and r.get('VoiceID') == int(parts[2])),
    'AVTR': lambda parts: ('AvatarConfig.json', load_table('AvatarConfig.json'),
        lambda r: r.get('AvatarID') == int(parts[2])),
    'CHRN': lambda parts: ('ChronicleConclusion.json', load_table('ChronicleConclusion.json'),
        lambda r: r.get('MissionID') == int(parts[1])),
    'SKIP': lambda parts: ('PerformanceSkipOverride.json', load_table('PerformanceSkipOverride.json'),
        lambda r: r.get('PerformanceType') == parts[1] and r.get('PerformanceID') == int(parts[2])),
    'MAIN': lambda parts: ('MainMission.json', load_table('MainMission.json'),
        lambda r: r.get('MainMissionID') == int(parts[1])),
    'SUBM': lambda parts: ('SubMission.json', load_table('SubMission.json'),
        lambda r: r.get('SubMissionID') == int(parts[2])),
    'TALK': lambda parts: ('TalkSentenceConfig.json', load_table('TalkSentenceConfig.json'),
        lambda r: r.get('TalkSentenceID') == int(parts[1])),
    'MSG':  lambda parts: ('MessageItemConfig.json', load_table('MessageItemConfig.json'),
        lambda r: r.get('ID') == int(parts[1])),
    'CTAC': lambda parts: ('MessageContactsConfig.json', load_table('MessageContactsConfig.json'),
        lambda r: r.get('ID') == int(parts[2])),
    'MONS': lambda parts: ('MonsterConfig.json', load_table('MonsterConfig.json'),
        lambda r: r.get('MonsterID') == int(parts[1])),
    'ITEM': lambda parts: ('ItemConfig.json', load_table('ItemConfig.json'),
        lambda r: r.get('ID') == int(parts[1])),
    'EQUP': lambda parts: ('ItemConfigEquipment.json', load_table('ItemConfigEquipment.json'),
        lambda r: r.get('ID') == int(parts[2])),
    'RELC': lambda parts: ('ItemConfigRelic.json', load_table('ItemConfigRelic.json'),
        lambda r: r.get('ID') == int(parts[1])),
    'DISK': lambda parts: ('ItemConfigDisk.json', load_table('ItemConfigDisk.json'),
        lambda r: r.get('ID') == int(parts[1])),
    'MIRC': lambda parts: (_mirc_table(parts[1]), _mirc_data(parts[1]), _mirc_match(parts)),
    'FRML': lambda parts: ('RogueTournFormulaDisplay.json', load_table('RogueTournFormulaDisplay.json'),
        lambda r: r.get('FormulaDisplayID') == int(parts[1])),
}

def _mirc_table(part1):
    if part1.startswith('T'): return 'RogueTournMiracleDisplay.json'
    if part1.startswith('S'): return 'RogueMagicScepterDisplay.json'
    if part1.startswith('H'): return 'RogueTournHexDisplay.json'
    return 'RogueMiracleDisplay.json'

def _mirc_data(part1):
    return load_table(_mirc_table(part1))

def _mirc_match(parts):
    p1 = parts[1]
    if p1.startswith('T'):
        return lambda r: r.get('MiracleDisplayID') == int(p1[1:])
    if p1.startswith('S'):
        return lambda r: r.get('ScepterID') == int(p1[1:])
    if p1.startswith('H'):
        return lambda r: r.get('HexDisplayID') == int(p1[1:])
    return lambda r: r.get('MiracleDisplayID') == int(p1)

# Table cache
_table_cache = {}

def get_table(name):
    if name not in _table_cache:
        _table_cache[name] = load_table(name)
    return _table_cache[name]

# ── Test 1: Cite-back verification ──────────────────────────────
print("\n" + "=" * 60)
print("TEST 1: Cite-back verification (compound key)")
print("=" * 60)

# Load all main corpus entries (exclude isolation volumes for cite-back)
all_entries = []
for vol_file in sorted(glob.glob(os.path.join(CORPUS, '*.jsonl'))):
    bn = os.path.basename(vol_file)
    if bn in ('speakerless.jsonl', 'excluded_ip.jsonl'):
        continue
    with open(vol_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                all_entries.append(json.loads(line))

print(f"Total main entries: {len(all_entries)}")

# Stratified sample: at least 2 per TYPE, total 100
from collections import defaultdict
by_type = defaultdict(list)
for e in all_entries:
    typ = e['cite_id'].split('-')[0]
    by_type[typ].append(e)

sample = []
random.seed(42)
for typ, entries in sorted(by_type.items()):
    n = min(2, len(entries))
    sample.extend(random.sample(entries, n))

# Fill to 100
remaining = [e for e in all_entries if e not in sample]
random.shuffle(remaining)
sample.extend(remaining[:100 - len(sample)])
random.shuffle(sample)
sample = sample[:100]

print(f"Sample: {len(sample)} entries, covering {len(by_type)} types")

results = []
passed = 0
failed = 0

for e in sample:
    cite_id = e['cite_id']
    source_table = e['source_table']
    source_field = e['source_field']
    raw = e['raw']
    parts = cite_id.split('-')
    typ = parts[0]

    if typ not in LOOKUP:
        results.append({'cite_id': cite_id, 'status': 'FAIL', 'reason': f'Unknown TYPE: {typ}'})
        failed += 1
        continue

    try:
        table_name, data, match_fn = LOOKUP[typ](parts)
        record = find_record(data, match_fn)

        if record is None:
            results.append({'cite_id': cite_id, 'status': 'FAIL', 'reason': 'Record not found'})
            failed += 1
            continue

        expected_raw = resolve_text(record, source_field)
        if expected_raw == raw:
            results.append({'cite_id': cite_id, 'status': 'PASS'})
            passed += 1
        else:
            results.append({'cite_id': cite_id, 'status': 'FAIL',
                           'reason': f'Raw mismatch (len: {len(raw)} vs {len(expected_raw)})'})
            failed += 1
    except Exception as ex:
        results.append({'cite_id': cite_id, 'status': 'FAIL', 'reason': str(ex)[:80]})
        failed += 1

print(f"\nPassed: {passed}/{len(sample)}, Failed: {failed}/{len(sample)}")
for r in results:
    status = '✓' if r['status'] == 'PASS' else '✗'
    reason = r.get('reason', '')
    if reason:
        print(f"  {status} {r['cite_id']}: {r['status']} ({reason})")
    else:
        print(f"  {status} {r['cite_id']}: {r['status']}")

# ── Test 2: Residual marker check ──────────────────────────────
print("\n" + "=" * 60)
print("TEST 2: Residual marker check")
print("=" * 60)

# Check main volumes only
main_entries = []
for e in all_entries:
    main_entries.append(e)

residual_patterns = {}
residual_count = 0

for e in main_entries:
    clean = e['clean']
    tags = re.findall(r'<[^>]*>', clean)
    braces = re.findall(r'\{[^}]*}', clean)
    hashes = re.findall(r'#\d+\[[^\]]*\]', clean)

    for t in tags:
        residual_patterns[t] = residual_patterns.get(t, 0) + 1
    for b in braces:
        residual_patterns[b] = residual_patterns.get(b, 0) + 1
    for h in hashes:
        residual_patterns[h] = residual_patterns.get(h, 0) + 1

    if tags or braces or hashes:
        residual_count += 1

print(f"Main volumes: entries with residual markers: {residual_count}/{len(main_entries)} ({residual_count/len(main_entries)*100:.2f}%)")
print(f"Unique patterns: {len(residual_patterns)}")
print(f"Top patterns:")
for p, c in sorted(residual_patterns.items(), key=lambda x: -x[1])[:20]:
    print(f"  {p}: {c}")

# Also check isolation volumes
iso_residual = 0
iso_patterns = {}
for iso_file in ['speakerless.jsonl', 'excluded_ip.jsonl']:
    iso_path = os.path.join(CORPUS, iso_file)
    if os.path.exists(iso_path):
        iso_entries = []
        with open(iso_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    iso_entries.append(json.loads(line))
        for e in iso_entries:
            clean = e['clean']
            tags = re.findall(r'<[^>]*>', clean)
            braces = re.findall(r'\{[^}]*}', clean)
            hashes = re.findall(r'#\d+\[[^\]]*\]', clean)
            for t in tags:
                iso_patterns[t] = iso_patterns.get(t, 0) + 1
            for b in braces:
                iso_patterns[b] = iso_patterns.get(b, 0) + 1
            for h in hashes:
                iso_patterns[h] = iso_patterns.get(h, 0) + 1
            if tags or braces or hashes:
                iso_residual += 1

print(f"\nIsolation volumes: {iso_residual} entries with residual markers")
print(f"Unique patterns in isolation: {len(iso_patterns)}")
print(f"Top patterns:")
for p, c in sorted(iso_patterns.items(), key=lambda x: -x[1])[:10]:
    print(f"  {p}: {c}")

# ── Test 3: Idempotency ────────────────────────────────────────
print("\n" + "=" * 60)
print("TEST 3: Idempotency check")
print("=" * 60)

file_hashes = {}
for vol_file in sorted(glob.glob(os.path.join(CORPUS, '*.jsonl'))):
    with open(vol_file, 'rb') as f:
        content = f.read()
    h = hashlib.md5(content).hexdigest()
    file_hashes[os.path.basename(vol_file)] = h
    print(f"  {os.path.basename(vol_file)}: {h}")

index_path = os.path.join(CORPUS, 'index.json')
with open(index_path, 'rb') as f:
    index_content = f.read()
index_hash = hashlib.md5(index_content).hexdigest()
file_hashes['index.json'] = index_hash
print(f"  index.json: {index_hash}")

hash_path = r'D:\Office\claudecode\star\hsr-lore\work\corpus_hashes.json'
with open(hash_path, 'w') as f:
    json.dump(file_hashes, f, indent=2)
print(f"\nHashes saved to: {hash_path}")

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)
print(f"Test 1 (cite-back): {passed}/{len(sample)} passed")
print(f"Test 2 (main residual): {residual_count} entries, {len(residual_patterns)} patterns")
print(f"Test 2 (iso residual): {iso_residual} entries, {len(iso_patterns)} patterns")
print(f"Test 3 (idempotency): hashes saved, run extractor again to verify")