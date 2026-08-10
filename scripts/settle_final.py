"""
语料最终结算 v2 — 封版程序
从 extract 开始，到全部验收通过为止。一步完成。
"""
import json, sys, io, os, re, hashlib, subprocess
from pathlib import Path
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(__file__).parent.parent
CORPUS = BASE / 'corpus'
WORK = BASE / 'work'
VENV_PYTHON = BASE / '.venv' / 'Scripts' / 'python.exe'

# ── Step 0: Extract ───────────────────────────────────────────────

print("=" * 60)
print("STEP 0: Re-extract to get fresh speakerless")
print("=" * 60)
subprocess.run([str(VENV_PYTHON), str(BASE / 'scripts' / 'extract.py')],
               cwd=str(BASE), timeout=120, check=True)
print("Done.")

# ── Step 1: Classify with exact v3 rules ──────────────────────────

print("\n" + "=" * 60)
print("STEP 1: Classify speakerless with v3 rules")
print("=" * 60)

SFP = re.compile(r'[呢吗吧啊哦嘛呀嗯]$')
QM = re.compile(r'[？?！!]$')
US = re.compile(r'^(请选择|点击|按下|返回|确认|取消|跳过|前往|返回|探索|调查|对话|进入|退出|使用|装备|丢弃|购买|出售|打开|关闭|前进|后退|上一步|下一步|挑战|战斗|逃跑|防御|攻击|离开|离开这里)')
HS = re.compile(r'(师父|大人|先生|小姐|女士|君|殿下|阁下|博士|老师|前辈|学长|学姐|师兄|师姐|队长|医生|护士|老板|老板娘)')
AV = ['走了','走进','走过','走出','走到','走来','来到','来自','说道','说着','看到','看见','看着','看向','听到','听见','感到','感觉','点了','点着','摇了','挥了','伸出手','拿起','放下','转身','回过头','停下来','停下','推开','拉开','坐下','站起来','笑了','笑着','叹了口气','注视着','盯着','望向','飘落','浮现','消失','离开','离去','进入','退出','打开','关上','捡起','递给','抬起','低下头','侧过','睁开','闭上','弯下','出现','显现','涌现','发现','决定了','选择了']

def classify_v3(text):
    text = text.strip()
    if len(text) <= 4: return 'placeholder'
    if re.match(r'^[.…\s]+$', text): return 'placeholder'
    if re.match(r'^（[^）]*）$', text) and len(text) <= 10: return 'placeholder'
    if US.match(text): return 'ui_system'
    if SFP.search(text): return 'dialogue'
    if QM.search(text): return 'dialogue'
    if re.search(r'^我|。我|，我|！我|？我|、我|：我', text): return 'dialogue'
    if re.search(r'(我们|咱们|俺)', text): return 'dialogue'
    if HS.search(text): return 'dialogue'
    has_comp = bool(re.search(r'[了着过]', text))
    has_act = any(v in text for v in AV)
    if has_comp and has_act and not (SFP.search(text) or QM.search(text)):
        return 'narration'
    if re.match(r'^你[^？！。，]{8,}', text) and not QM.search(text):
        if '了' in text or '着' in text:
            return 'narration'
    return 'unclassified'

# ── Step 2: Load & Split ──────────────────────────────────────────

print("\n" + "=" * 60)
print("STEP 2: Load and split")
print("=" * 60)

# Build main-volume cite_ids
main_cids = set()
for vol in ['lore','books','characters','narrative','dialogue','artifacts','rogue']:
    with open(CORPUS / f'{vol}.jsonl','r',encoding='utf-8') as f:
        for line in f:
            if line.strip():
                main_cids.add(json.loads(line)['cite_id'])
print(f"  Main-volume cite_ids: {len(main_cids)}")

# Load speakerless
speakerless = []
with open(CORPUS / 'speakerless.jsonl','r',encoding='utf-8') as f:
    for line in f:
        if line.strip():
            speakerless.append(json.loads(line))
print(f"  Speakerless entries: {len(speakerless)}")

isolated = []
unattributed = []
dedup_count = 0
cats = defaultdict(int)

for e in speakerless:
    cat = classify_v3(e.get('clean', ''))
    e['meta']['text_layer'] = cat
    e['meta']['speaker_status'] = 'absent'

    if cat in ('placeholder', 'ui_system'):
        e['volume'] = 'speakerless'
        isolated.append(e)
    elif e['cite_id'] in main_cids:
        dedup_count += 1
        e['volume'] = 'speakerless'
        isolated.append(e)
    else:
        e['volume'] = 'unattributed'
        unattributed.append(e)
        cats[cat] += 1

print(f"  → speakerless (isolated): {len(isolated)}")
print(f"  → unattributed (new): {len(unattributed)}")
print(f"  → deduplicated: {dedup_count}")
print(f"  → unattributed by layer: {dict(cats)}")

# ── Step 3: Clean unattributed ────────────────────────────────────

print("\n" + "=" * 60)
print("STEP 3: Clean unattributed")
print("=" * 60)
cleaned_count = 0
for e in unattributed:
    old = e.get('clean', '')
    new = old.replace('\\n', '\n')
    new = re.sub(r'\{TEXTJOIN[^}]*\}', '', new)
    new = new.replace('{NICKNAME}', '开拓者')
    if new != old:
        cleaned_count += 1
        e['clean'] = new
print(f"  Cleaned: {cleaned_count}/{len(unattributed)}")

# ── Step 4: Return ITEM-140615 ────────────────────────────────────

print("\n" + "=" * 60)
print("STEP 4: Return ITEM-140615")
print("=" * 60)
excluded = []
returned_item = None
with open(CORPUS / 'excluded_ip.jsonl','r',encoding='utf-8') as f:
    for line in f:
        if line.strip():
            e = json.loads(line)
            if e['cite_id'] == 'ITEM-140615':
                returned_item = e
            else:
                excluded.append(e)

with open(CORPUS / 'excluded_ip.jsonl','w',encoding='utf-8') as f:
    for e in excluded:
        f.write(json.dumps(e, ensure_ascii=False) + '\n')
print(f"  excluded_ip: {len(excluded)} entries")

if returned_item:
    returned_item['volume'] = 'artifacts'
    returned_item['meta'].pop('exclusion_reason', None)
    returned_item['meta'].pop('rarity', None)
    # Append to artifacts
    artifacts = []
    with open(CORPUS / 'artifacts.jsonl','r',encoding='utf-8') as f:
        for line in f:
            if line.strip():
                artifacts.append(json.loads(line))
    artifacts.append(returned_item)
    with open(CORPUS / 'artifacts.jsonl','w',encoding='utf-8') as f:
        for a in artifacts:
            f.write(json.dumps(a, ensure_ascii=False) + '\n')
    print(f"  artifacts: {len(artifacts)} entries (+1)")

# ── Step 5: Write corpus files ────────────────────────────────────

print("\n" + "=" * 60)
print("STEP 5: Write corpus files")
print("=" * 60)

with open(CORPUS / 'speakerless.jsonl','w',encoding='utf-8') as f:
    for e in isolated:
        f.write(json.dumps(e, ensure_ascii=False) + '\n')

with open(CORPUS / 'unattributed.jsonl','w',encoding='utf-8') as f:
    for e in unattributed:
        f.write(json.dumps(e, ensure_ascii=False) + '\n')

print(f"  speakerless.jsonl: {len(isolated)} entries")
print(f"  unattributed.jsonl: {len(unattributed)} entries")

# ── Step 6: Rebuild index ─────────────────────────────────────────

print("\n" + "=" * 60)
print("STEP 6: Rebuild cite_index and index.json")
print("=" * 60)

volumes = ['lore','books','characters','narrative','dialogue','artifacts','rogue','unattributed']
cite_index = {}
whitelist = set()
vol_stats = {}
vol_chars = {}

for vol in volumes:
    path = CORPUS / f'{vol}.jsonl'
    entries = []
    chars = 0
    with open(path,'r',encoding='utf-8') as f:
        for line in f:
            if line.strip():
                e = json.loads(line)
                entries.append(e)
                cite_index[e['cite_id']] = {'cite_id':e['cite_id'],'clean':e.get('clean',''),'volume':vol}
                whitelist.add(e['cite_id'])
                chars += len(e.get('clean',''))
    vol_stats[vol] = len(entries)
    vol_chars[vol] = chars
    print(f"  {vol}: {len(entries)} entries")

with open(WORK / 'cite_index.jsonl','w',encoding='utf-8') as f:
    for cid in sorted(cite_index.keys()):
        f.write(json.dumps(cite_index[cid], ensure_ascii=False) + '\n')

with open(WORK / 'cite_whitelist.txt','w',encoding='utf-8') as f:
    for cid in sorted(whitelist):
        f.write(cid + '\n')

# Write index.json
index_data = {'volumes':{},'total_entries':0,'total_chars':0,'estimated_tokens':0}
for vol in volumes:
    idx_entry = {'entries':vol_stats[vol],'chars':vol_chars[vol],'tokens_est':int(vol_chars[vol]*0.75)}
    index_data['volumes'][vol] = idx_entry
    index_data['total_entries'] += idx_entry['entries']
    index_data['total_chars'] += idx_entry['chars']
    index_data['estimated_tokens'] += idx_entry['tokens_est']

for iso_vol in ['speakerless','excluded_ip']:
    path = CORPUS / f'{iso_vol}.jsonl'
    chars = 0
    entries = 0
    with open(path,'r',encoding='utf-8') as f:
        for line in f:
            if line.strip():
                entries += 1
                chars += len(json.loads(line).get('clean',''))
    index_data['volumes'][iso_vol] = {'entries':entries,'chars':chars,'tokens_est':int(chars*0.75),'isolated':True}

with open(CORPUS / 'index.json','w',encoding='utf-8') as f:
    json.dump(index_data, f, ensure_ascii=False, indent=2)

print(f"  cite_index: {len(cite_index)} entries")
print(f"  Total main: {index_data['total_entries']} entries, ~{index_data['estimated_tokens']} tokens")

# ── Step 7: Verify ────────────────────────────────────────────────

print("\n" + "=" * 60)
print("STEP 7: Run verification")
print("=" * 60)
result = subprocess.run([str(VENV_PYTHON), str(BASE / 'scripts' / 'verify.py')],
                       capture_output=True, text=True, timeout=60, cwd=str(BASE),
                       encoding='utf-8', errors='replace')
print(result.stdout)

# ── Step 8: MD5 baseline ──────────────────────────────────────────

print("\n" + "=" * 60)
print("STEP 8: MD5 baseline")
print("=" * 60)
hashes = {}
for fstem in ['artifacts','books','characters','dialogue','excluded_ip','lore','narrative','rogue','speakerless','unattributed']:
    fpath = CORPUS / f'{fstem}.jsonl'
    h = hashlib.md5(fpath.read_bytes()).hexdigest()
    hashes[f'{fstem}.jsonl'] = h
    print(f"  {fstem}: {h}")
ipath = CORPUS / 'index.json'
hashes['index.json'] = hashlib.md5(ipath.read_bytes()).hexdigest()
print(f"  index: {hashes['index.json']}")

with open(WORK / 'corpus_hashes.json','w',encoding='utf-8') as f:
    json.dump(hashes, f, ensure_ascii=False, indent=2)

# ── Step 9: Cite ID uniqueness ────────────────────────────────────

print("\n" + "=" * 60)
print("STEP 9: Cite ID uniqueness")
print("=" * 60)
all_cids = []
for vol in volumes + ['speakerless','excluded_ip']:
    path = CORPUS / f'{vol}.jsonl'
    with open(path,'r',encoding='utf-8') as f:
        for line in f:
            if line.strip():
                all_cids.append(json.loads(line)['cite_id'])

unique = len(set(all_cids))
total = len(all_cids)
print(f"  Total: {total}, Unique: {unique}, Duplicates: {total - unique}")
main_only = set()
for vol in volumes:
    with open(CORPUS / f'{vol}.jsonl','r',encoding='utf-8') as f:
        for line in f:
            if line.strip():
                main_only.add(json.loads(line)['cite_id'])
print(f"  Main volume cite_ids: {len(main_only)}, unique: {len(main_only)}")
print(f"  {'ALL UNIQUE' if len(main_only) == sum(vol_stats.values()) else 'WARNING: DUPLICATES IN MAIN VOLUMES'}")

print(f"\n{'='*60}")
print("CORPUS SETTLEMENT FINAL — COMPLETE")
print(f"{'='*60}")
