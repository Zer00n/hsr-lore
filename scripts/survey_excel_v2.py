"""
ExcelOutput 字段普查 v2 — 只关注有叙事潜力的文件
"""
import json, os, glob, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = r'D:\Office\claudecode\star\hsr-lore\vendor\StarRailData'
EXCEL = os.path.join(BASE, 'ExcelOutput')
TEXTMAP_PATH = os.path.join(BASE, 'TextMap', 'TextMapCHS.json')

print("Loading TextMapCHS...")
with open(TEXTMAP_PATH, 'r', encoding='utf-8') as f:
    textmap = json.load(f)
print(f"  {len(textmap)} entries loaded\n")

# Narrative keywords for field names
NARRATIVE_FIELDS = {
    'desc', 'description', 'story', 'text', 'name', 'title', 'intro',
    'introduction', 'strategy', 'content', 'biography', 'narrative',
    'summary', 'overview', 'detail', 'info', 'note', 'tip', 'hint',
    'message', 'sentence', 'dialog', 'dialogue', 'voice', 'line',
    'monologue', 'remark', 'comment', 'explain', 'background',
    'bgdesc', 'bg_desc', 'itemdesc', 'item_desc', 'fullname',
    'avatarname', 'avatardesc', 'monstername', 'monsterintro',
    'npcname', 'questtitle', 'questdesc', 'missiontitle', 'missiondesc',
    'achievementtitle', 'achievementdesc', 'tutorialdesc',
    'loadingtext', 'booktitle', 'bookcontent', 'bookseries',
    'relicname', 'relicdesc', 'planename', 'planeDesc',
}

# Category keywords for filenames
A_KEYWORDS = [
    'book', 'story', 'dialog', 'talk', 'mission', 'quest',
    'avatar', 'voice', 'npc', 'monster', 'item', 'relic', 'plane',
    'achievement', 'tutorial', 'loading', 'message', 'mail', 'phone',
    'rogue', 'dice', 'chronicle', 'archive', 'readable', 'note',
    'introduction', 'discussion', 'sentence',
]

# Files to skip (no narrative value)
SKIP_PATTERNS = [
    'Audio', 'BGM', 'Camera', 'Effect', 'Damage', 'Drop',
    'Formation', 'Formula', 'Gameplay', 'Global', 'Guide',
    'Level', 'Map', 'Material', 'Path', 'Pool', 'Price',
    'Property', 'Raid', 'Rate', 'Shop', 'Skill', 'Speed',
    'Test', 'UI', 'Video', 'Volume', 'Anchor', 'Attack',
    'AvatarDemo', 'AvatarExp', 'AvatarProperty', 'AvatarSkill',
    'AvatarTest', 'AvatarCutin', 'AvatarSkin', 'AvatarUse',
    'AvatarPromotion', 'AvatarRank', 'AvatarLevel',
    'AvatarDefaultMaze', 'AvatarDeliver', 'AvatarEquip',
    'AvatarRelic', 'AvatarSource', 'AvatarStatus',
    'Rogue', 'Challenge', 'Battle', 'Combat', 'Fight',
    'Grid', 'Maze', 'Relic', 'Equipment', 'Buff',
    'AvatarBreak', 'AvatarLink', 'AvatarBase',
    'AvatarAtlas', 'AvatarCamp', 'AvatarCobrand',
    'AvatarComefrom', 'AvatarGlobal', 'AvatarMaze',
    'AvatarPath', 'AvatarPlayer', 'AvatarServant',
    'AvatarSpecial', 'AvatarTeam', 'AvatarUltra',
    'AvatarAbility', 'AvatarEnhanced',
    'Activity', 'Monster', 'Plane', 'Stage',
    'ItemConfigAvatar', 'ItemConfigRelic', 'ItemConfigWeapon',
    'ItemConfigBook', 'ItemConfigDisc', 'ItemConfigEquipment',
    'ItemConfigMission', 'ItemConfigQuest', 'ItemConfigRogue',
    'ItemConfigTrial', 'ItemConfigActivity',
    'Npc', 'Tutorial', 'Loading', 'Message',
    'MultiplePath', 'PreAvatar', 'UpgradeAvatar',
    'SpecialAvatar', 'StroyLine', 'Treasure',
    'IdleLive', 'FightFest', 'MatchThree', 'PhotoGraph',
    'PlanetFes', 'Elation', 'Fate', 'CakeRace',
    'Decide', 'ILBattle', 'CommonAvatar',
    'Roque', 'Rogue', 'Chess', 'Aether', 'Magic',
    'PunkLord', 'SilverWolf', 'FindTrotter',
    'FarmMultiple', 'FeverTime', 'GuessSilhouette',
    'Honor', 'Expedition', 'Constant',
    'AvatarConfigEnhanced', 'AvatarConfigTrial',
    'AvatarConfigLD', 'AvatarSkillTreeConfig',
    'AvatarSkillConfigLD', 'AvatarSkillConfigTrial',
    'AvatarSkillTreeConfigLD', 'AvatarSkillTreeConfigTrial',
    'AvatarSkillLink', 'AvatarSkillProperty',
    'AvatarConfigLD', 'AvatarConfigTrial',
]

# Detect if a value is a Hash reference
def is_hash_ref(val):
    return isinstance(val, dict) and 'Hash' in val and len(val) == 1

results = []

for i, fpath in enumerate(glob.glob(os.path.join(EXCEL, '*.json'))):
    fname = os.path.basename(fpath)
    fsize = os.path.getsize(fpath)

    # Check skip patterns
    fname_noext = fname.replace('.json', '')
    should_skip = any(p.lower() in fname_noext.lower() for p in SKIP_PATTERNS)
    if should_skip:
        continue

    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        continue

    # Handle empty/null
    if not isinstance(data, list) or len(data) == 0:
        continue
    data = [d for d in data if d is not None and isinstance(d, dict)]
    if len(data) == 0:
        continue

    n_records = len(data)
    first = data[0]

    # Extract fields with Hash references
    hash_fields = []
    all_fields = []

    for key, val in first.items():
        val_type = type(val).__name__
        nested = None
        if isinstance(val, dict) and not is_hash_ref(val):
            nested = list(val.keys())
        elif isinstance(val, list) and len(val) > 0:
            if isinstance(val[0], dict):
                nested = list(val[0].keys())

        all_fields.append({
            'name': key,
            'type': val_type,
            'nested': nested,
        })

        if is_hash_ref(val):
            # Resolve samples
            seen = set()
            samples = []
            for record in data:
                if key in record:
                    rv = record[key]
                    if is_hash_ref(rv):
                        h = str(rv['Hash'])
                        if h in textmap and h not in seen:
                            text = textmap[h]
                            if text and text != 'N/A':
                                samples.append(text)
                                seen.add(h)
                            if len(samples) >= 3:
                                break
            hash_fields.append({
                'field': key,
                'samples': samples,
            })
        elif isinstance(val, dict) and 'Hash' not in val:
            # Check nested hash fields
            for nk, nv in val.items():
                if is_hash_ref(nv):
                    seen = set()
                    samples = []
                    for record in data:
                        if key in record and isinstance(record[key], dict):
                            if nk in record[key] and is_hash_ref(record[key][nk]):
                                h = str(record[key][nk]['Hash'])
                                if h in textmap and h not in seen:
                                    text = textmap[h]
                                    if text and text != 'N/A':
                                        samples.append(text)
                                        seen.add(h)
                                    if len(samples) >= 3:
                                        break
                    hash_fields.append({
                        'field': f'{key}.{nk}',
                        'samples': samples,
                    })

    # Determine category
    narrative_field_count = sum(1 for hf in hash_fields if any(
        nf in hf['field'].lower() for nf in NARRATIVE_FIELDS))
    a_score = sum(1 for kw in A_KEYWORDS if kw in fname.lower())
    # Check if any hash fields have narrative names
    has_narrative = any(
        any(nf in hf['field'].lower() for nf in NARRATIVE_FIELDS)
        for hf in hash_fields
    )

    if a_score > 0 and has_narrative:
        category = 'A'
    elif has_narrative:
        category = 'B'
    elif hash_fields:
        category = 'B'
    else:
        category = 'C'

    if hash_fields:
        results.append({
            'file': fname,
            'size_mb': fsize / (1024 * 1024),
            'records': n_records,
            'hash_fields': hash_fields,
            'all_fields': all_fields,
            'category': category,
        })

    if (i + 1) % 300 == 0:
        print(f"  [{i+1}/2140] scanned...")

print(f"\n=== SURVEY COMPLETE ===")
print(f"Files with hash fields: {len(results)}")
a_count = sum(1 for r in results if r['category'] == 'A')
b_count = sum(1 for r in results if r['category'] == 'B')
c_count = sum(1 for r in results if r['category'] == 'C')
print(f"  A (worldview): {a_count}")
print(f"  B (suspicious): {b_count}")
print(f"  C (irrelevant): {c_count}")

# Print A and B results
print(f"\n{'='*80}")
print("A/B CLASS FILES WITH HASH FIELDS")
print(f"{'='*80}")
for r in results:
    if r['category'] in ('A', 'B'):
        print(f"\n### {r['file']} [{r['category']}] ({r['records']} records, {r['size_mb']:.1f} MB)")
        for hf in r['hash_fields']:
            print(f"  {hf['field']}:")
            for s in hf['samples']:
                print(f"    - {s}")

# Save results
output_path = r'D:\Office\claudecode\star\hsr-lore\work\excel_survey_v2.json'
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\nResults saved to: {output_path}")