"""
TalkSentenceID 归属验证脚本
验证 TalkSentenceID 前缀是否与 MainMissionID 同构
"""
import json, os, sys, io, random

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = r'D:\Office\claudecode\star\hsr-lore\vendor\StarRailData'
EXCEL = os.path.join(BASE, 'ExcelOutput')

# Load data
print("Loading data...")
with open(os.path.join(BASE, 'TextMap', 'TextMapCHS.json'), 'r', encoding='utf-8') as f:
    textmap = json.load(f)

with open(os.path.join(EXCEL, 'TalkSentenceConfig.json'), 'r', encoding='utf-8') as f:
    talks = json.load(f)

with open(os.path.join(EXCEL, 'MainMission.json'), 'r', encoding='utf-8') as f:
    missions = json.load(f)

# Build MainMissionID set
main_mission_ids = set(m['MainMissionID'] for m in missions)
print(f"MainMission IDs: {len(main_mission_ids)}")
print(f"TalkSentenceConfig entries: {len(talks)}")

# Step 1: Random sample 2000, try prefix matching
print("\n" + "="*80)
print("STEP 1: Prefix matching on random 2000 samples")
print("="*80)

random.seed(42)
sample = random.sample(talks, min(2000, len(talks)))

for prefix_len in [7, 6, 8, 5, 9]:
    matched = 0
    for t in sample:
        tid_str = str(t['TalkSentenceID'])
        if len(tid_str) >= prefix_len:
            prefix = int(tid_str[:prefix_len])
            if prefix in main_mission_ids:
                matched += 1
    rate = matched / len(sample) * 100
    print(f"  Prefix length {prefix_len}: {matched}/{len(sample)} = {rate:.1f}%")

# Step 2: Full scan with best prefix length
print("\n" + "="*80)
print("STEP 2: Full scan with best prefix length")
print("="*80)

# Also check if TalkSentenceID matches without prefix truncation
# TalkSentenceID like 802410000 might not match MissionID like 1000101
# Let's check the actual ID ranges
talk_ids = [t['TalkSentenceID'] for t in talks]
print(f"TalkSentenceID range: {min(talk_ids)} - {max(talk_ids)}")
print(f"MainMissionID range: {min(main_mission_ids)} - {max(main_mission_ids)}")

# Check if there are different ID patterns
patterns = {}
for tid in talk_ids:
    tid_str = str(tid)
    length = len(tid_str)
    if length not in patterns:
        patterns[length] = 0
    patterns[length] += 1

print(f"TalkSentenceID lengths: {dict(sorted(patterns.items()))}")

# Let's check all prefix lengths
for prefix_len in range(4, 11):
    matched = 0
    total = 0
    for t in talks:
        tid_str = str(t['TalkSentenceID'])
        if len(tid_str) >= prefix_len:
            total += 1
            prefix = int(tid_str[:prefix_len])
            if prefix in main_mission_ids:
                matched += 1
    if total > 0:
        rate = matched / total * 100
        print(f"  Prefix {prefix_len}: {matched}/{total} = {rate:.1f}%")
    else:
        print(f"  Prefix {prefix_len}: 0/0")

# Step 3: Try alternative approach - look for mapping tables
print("\n" + "="*80)
print("STEP 3: Search for TalkSentenceID → Mission mapping tables")
print("="*80)

# Check all ExcelOutput files for fields containing 'TalkSentence' or 'Mission' in combinations
import glob
for fpath in sorted(glob.glob(os.path.join(EXCEL, '*.json'))):
    fname = os.path.basename(fpath)
    if 'talk' in fname.lower() or 'sentence' in fname.lower() or 'dialogue' in fname.lower() or 'dialog' in fname.lower():
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list) and len(data) > 0:
                first = data[0]
                print(f"  {fname}: {len(data)} records, fields: {list(first.keys())[:15]}")
            elif isinstance(data, dict):
                print(f"  {fname}: dict, {len(data)} keys")
        except:
            pass

# Step 4: Cross-validate with mission names
print("\n" + "="*80)
print("STEP 4: Cross-validation - 20 matched samples")
print("="*80)

# Build mission lookup
mission_lookup = {}
for m in missions:
    if 'Name' in m and 'Hash' in m['Name']:
        mission_lookup[m['MainMissionID']] = textmap.get(str(m['Name']['Hash']), 'N/A')

# Find matches with prefix=7
matched_pairs = []
for t in talks:
    if 'TalkSentenceText' not in t:
        continue
    tid_str = str(t['TalkSentenceID'])
    if len(tid_str) >= 7:
        prefix = int(tid_str[:7])
        if prefix in main_mission_ids:
            text = textmap.get(str(t['TalkSentenceText']['Hash']), '')
            if text and text != 'N/A':
                mission_name = mission_lookup.get(prefix, 'N/A')
                matched_pairs.append((tid_str, prefix, mission_name, text))

print(f"Total matched pairs: {len(matched_pairs)}")

# Random sample 20
random.seed(123)
cross_samples = random.sample(matched_pairs, min(20, len(matched_pairs)))
for i, (tid, mid, mname, text) in enumerate(cross_samples):
    print(f"\n  [{i+1}] TalkSentenceID={tid} → MissionID={mid}")
    print(f"      任务名: {mname}")
    print(f"      对话文本: {text[:200]}")

# Step 5: Statistical summary
print("\n" + "="*80)
print("STEP 5: Statistical summary")
print("="*80)

# Full scan with prefix=7
matched_total = 0
unmatched_total = 0
world_dist = {}
for t in talks:
    tid_str = str(t['TalkSentenceID'])
    if len(tid_str) >= 7:
        prefix = int(tid_str[:7])
        if prefix in main_mission_ids:
            matched_total += 1
            # Find the mission's WorldID
            for m in missions:
                if m['MainMissionID'] == prefix:
                    wid = m.get('WorldID', 0)
                    world_dist[wid] = world_dist.get(wid, 0) + 1
                    break
        else:
            unmatched_total += 1

total_with_text = sum(1 for t in talks if 'TalkSentenceText' in t)
print(f"Total TalkSentenceConfig entries: {len(talks)}")
print(f"Entries with text: {total_with_text}")
print(f"Matched (7-digit prefix → MainMissionID): {matched_total} ({matched_total/len(talks)*100:.1f}%)")
print(f"Unmatched: {unmatched_total} ({unmatched_total/len(talks)*100:.1f}%)")
print(f"\nWorldID distribution of matched entries:")
for wid in sorted(world_dist.keys()):
    print(f"  WorldID {wid}: {world_dist[wid]} entries")

# Check if WorldID matches BookSeriesWorld
books = json.load(open(os.path.join(EXCEL, 'BookSeriesWorld.json'), 'r', encoding='utf-8'))
world_names = {}
for b in books:
    h = b['BookSeriesWorldTextmapID']['Hash']
    world_names[b['BookSeriesWorld']] = textmap.get(str(h), '?')

print(f"\nWorldID → Planet mapping:")
for wid in sorted(world_dist.keys()):
    bsw_id = wid // 100
    planet = world_names.get(bsw_id, '?')
    print(f"  WorldID {wid} → {planet}: {world_dist[wid]} entries")

print("\nDone!")