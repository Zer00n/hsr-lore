"""
语料收口：建 unattributed 卷 + 退回 ITEM-140615 + 全部验收
"""
import json, sys, io, os, hashlib, shutil
from pathlib import Path
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(__file__).parent.parent
CORPUS = BASE / 'corpus'
WORK = BASE / 'work'

# ── Step 1: Load classification ──────────────────────────────────

print("=" * 60)
print("STEP 1: Load classification data")
print("=" * 60)

with open(WORK / 'speakerless_classified_v2.json', 'r', encoding='utf-8') as f:
    class_report = json.load(f)

# Build cite_id → category map
cite_to_cat = {}
for cat in ['narration', 'dialogue', 'unclassified', 'placeholder', 'ui_system']:
    for s in class_report['samples'][cat]:
        cite_to_cat[s['cite_id']] = cat

# Full classification map (not just samples) — need to re-run classifier output
# Since v2 only saved samples, rebuild the full map
print("Rebuilding full classification map...")
# Use the classify function inline
import re

SENTENCE_FINAL_PARTICLES = re.compile(r'[呢吗吧啊哦嘛呀嗯]$')
QUESTION_MARK = re.compile(r'[？?！!]$')
HONORIFIC_SUFFIX = re.compile(r'(师父|大人|先生|小姐|女士|君|殿下|阁下|博士|老师|前辈|学长|学姐|师兄|师姐|队长|医生|护士|老板|老板娘)')
UI_START = re.compile(
    r'^(请选择|点击|按下|返回|确认|取消|跳过|前往|返回|探索|调查|'
    r'对话|进入|退出|使用|装备|丢弃|购买|出售|打开|关闭|'
    r'前进|后退|上一步|下一步|挑战|战斗|逃跑|防御|攻击|'
    r'离开|离开这里)'
)
ACTION_VERBS = [
    '走了', '走进', '走过', '走出', '走到', '走来', '来到', '来自',
    '说道', '说着', '看到', '看见', '看着', '看向', '听到', '听见',
    '感到', '感觉', '点了', '点着', '摇了', '挥了', '伸出手', '拿起',
    '放下', '转身', '回过头', '停下来', '停下', '推开', '拉开',
    '坐下', '站起来', '笑了', '笑着', '叹了口气', '注视着', '盯着',
    '望向', '飘落', '浮现', '消失', '离开', '离去', '进入', '退出',
    '打开', '关上', '捡起', '递给', '抬起', '低下头', '侧过',
    '睁开', '闭上', '弯下', '出现', '显现', '涌现', '发现',
    '决定了', '选择了',
]

def classify(text):
    text = text.strip()
    if len(text) <= 4: return 'placeholder'
    if re.match(r'^[.…\s]+$', text): return 'placeholder'
    if re.match(r'^（[^）]*）$', text) and len(text) <= 10: return 'placeholder'
    if UI_START.match(text): return 'ui_system'
    if SENTENCE_FINAL_PARTICLES.search(text): return 'dialogue'
    if QUESTION_MARK.search(text): return 'dialogue'
    if re.search(r'^我|。我|，我|！我|？我|、我|：我', text): return 'dialogue'
    if re.search(r'(我们|咱们|俺)', text): return 'dialogue'
    if HONORIFIC_SUFFIX.search(text): return 'dialogue'
    has_comp = bool(re.search(r'[了着过]', text))
    has_act = any(v in text for v in ACTION_VERBS)
    if has_comp and has_act and not (SENTENCE_FINAL_PARTICLES.search(text) or QUESTION_MARK.search(text)):
        return 'narration'
    # v3 correct logic: must start with 你 AND have aspect marker
    if re.match(r'^你[^？！。，]{8,}', text) and not QUESTION_MARK.search(text):
        if '了' in text or '着' in text:
            return 'narration'
    return 'unclassified'

# ── Step 2: Process speakerless.jsonl ─────────────────────────────

print("\n" + "=" * 60)
print("STEP 2: Split speakerless.jsonl")
print("=" * 60)

# Build set of cite_ids already in main volumes (for dedup)
main_cids = set()
for vol in ['lore', 'books', 'characters', 'narrative', 'dialogue', 'artifacts', 'rogue']:
    path = CORPUS / f'{vol}.jsonl'
    if not path.exists(): continue
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                main_cids.add(json.loads(line)['cite_id'])
print(f"  Existing main-volume cite_ids: {len(main_cids)}")

speakerless = []
with open(CORPUS / 'speakerless.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            speakerless.append(json.loads(line))

isolated = []      # stay in speakerless (placeholder + ui_system)
unattributed = []   # new volume (narration + dialogue + unclassified)
dedup_skip = 0

for e in speakerless:
    cat = classify(e.get('clean', ''))
    # Add classification label to meta
    e['meta']['text_layer'] = cat
    e['meta']['speaker_status'] = 'absent'

    if cat in ('placeholder', 'ui_system'):
        e['volume'] = 'speakerless'
        isolated.append(e)
    else:
        # Dedup: skip if cite_id already exists in a main volume
        if e['cite_id'] in main_cids:
            dedup_skip += 1
            # Keep in speakerless since it's already represented in the main corpus
            e['volume'] = 'speakerless'
            isolated.append(e)
        else:
            e['volume'] = 'unattributed'
            unattributed.append(e)

print(f"  → speakerless.jsonl (isolated): {len(isolated)} entries")
print(f"  → unattributed.jsonl (new): {len(unattributed)} entries")
print(f"  → Deduplicated (already in main volumes): {dedup_skip}")

# Verify counts
cats = defaultdict(int)
for e in unattributed:
    cats[e['meta']['text_layer']] += 1
print(f"     narration: {cats.get('narration', 0)}")
print(f"     dialogue: {cats.get('dialogue', 0)}")
print(f"     unclassified: {cats.get('unclassified', 0)}")

# ── Step 2.5: Clean unattributed entries ──────────────────────────

print("\n" + "=" * 60)
print("STEP 2.5: Clean unattributed (same rules as main volumes)")
print("=" * 60)

cleaned_count = 0
for e in unattributed:
    old_clean = e.get('clean', '')
    new_clean = old_clean.replace('\\n', '\n')
    new_clean = re.sub(r'\{TEXTJOIN[^}]*\}', '', new_clean)
    new_clean = new_clean.replace('{NICKNAME}', '开拓者')
    if new_clean != old_clean:
        cleaned_count += 1
        e['clean'] = new_clean

print(f"  Entries cleaned: {cleaned_count}/{len(unattributed)}")

# Count residual markers before/after in unattributed
residual_patterns = [re.compile(r'<[^>]*>'), re.compile(r'\{[^}]*\}'), re.compile(r'#\d+\[[^\]]*\]'), re.compile(r'\\\\n')]
residual_before = sum(1 for e in unattributed if any(p.search(e.get('clean','')) for p in residual_patterns))
print(f"  Entries with residual markers: {residual_before}")

# Write speakerless.jsonl (isolated only)
with open(CORPUS / 'speakerless.jsonl', 'w', encoding='utf-8') as f:
    for e in isolated:
        f.write(json.dumps(e, ensure_ascii=False) + '\n')

# Write unattributed.jsonl
with open(CORPUS / 'unattributed.jsonl', 'w', encoding='utf-8') as f:
    for e in unattributed:
        f.write(json.dumps(e, ensure_ascii=False) + '\n')

print("  Files written.")

# ── Step 3: Return ITEM-140615 to artifacts ────────────────────────

print("\n" + "=" * 60)
print("STEP 3: Return ITEM-140615")
print("=" * 60)

# Remove from excluded_ip
excluded = []
returned_item = None
with open(CORPUS / 'excluded_ip.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            e = json.loads(line)
            if e['cite_id'] == 'ITEM-140615':
                returned_item = e
            else:
                excluded.append(e)

with open(CORPUS / 'excluded_ip.jsonl', 'w', encoding='utf-8') as f:
    for e in excluded:
        f.write(json.dumps(e, ensure_ascii=False) + '\n')

print(f"  excluded_ip.jsonl: {len(excluded)} entries (was {len(excluded)+1})")

# Add to artifacts
if returned_item:
    returned_item['volume'] = 'artifacts'
    returned_item['meta'].pop('exclusion_reason', None)
    with open(CORPUS / 'artifacts.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps(returned_item, ensure_ascii=False) + '\n')
    print(f"  ITEM-140615 returned to artifacts.jsonl")
    print(f"  Text: {returned_item.get('clean', '')[:100]}")

# ── Step 4: Rebuild index ─────────────────────────────────────────

print("\n" + "=" * 60)
print("STEP 4: Rebuild cite_index")
print("=" * 60)

volumes = ['lore', 'books', 'characters', 'narrative', 'dialogue', 'artifacts', 'rogue', 'unattributed']
cite_index = {}
whitelist = set()
vol_stats = {}

for vol in volumes:
    path = CORPUS / f'{vol}.jsonl'
    if not path.exists(): continue
    entries = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                e = json.loads(line)
                entries.append(e)
                cite_index[e['cite_id']] = {
                    'cite_id': e['cite_id'],
                    'clean': e.get('clean', ''),
                    'volume': vol,
                }
                whitelist.add(e['cite_id'])
    vol_stats[vol] = len(entries)
    print(f"  {vol}: {len(entries)} entries")

total = sum(vol_stats.values())
print(f"  TOTAL: {total} entries, {len(cite_index)} unique cite_ids")

# Write cite_index
with open(WORK / 'cite_index.jsonl', 'w', encoding='utf-8') as f:
    for cid in sorted(cite_index.keys()):
        f.write(json.dumps(cite_index[cid], ensure_ascii=False) + '\n')

with open(WORK / 'cite_whitelist.txt', 'w', encoding='utf-8') as f:
    for cid in sorted(whitelist):
        f.write(cid + '\n')

print(f"  cite_index.jsonl: {len(cite_index)} entries")
print(f"  cite_whitelist.txt: {len(whitelist)} IDs")

# ── Step 5: Write updated index.json ───────────────────────────────

chars_per_vol = {}
for vol in volumes:
    path = CORPUS / f'{vol}.jsonl'
    if not path.exists(): continue
    chars = 0
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                e = json.loads(line)
                chars += len(e.get('clean', ''))
    chars_per_vol[vol] = chars

index_data = {
    'volumes': {},
    'total_entries': 0,
    'total_chars': 0,
    'estimated_tokens': 0,
}
for vol in volumes:
    if vol in vol_stats:
        idx_entry = {
            'entries': vol_stats[vol],
            'chars': chars_per_vol.get(vol, 0),
            'tokens_est': int(chars_per_vol.get(vol, 0) * 0.75),
        }
        index_data['volumes'][vol] = idx_entry
        index_data['total_entries'] += idx_entry['entries']
        index_data['total_chars'] += idx_entry['chars']
        index_data['estimated_tokens'] += idx_entry['tokens_est']

# Also list isolation volumes
for iso_vol in ['speakerless', 'excluded_ip']:
    path = CORPUS / f'{iso_vol}.jsonl'
    if not path.exists(): continue
    entries = []
    chars = 0
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                e = json.loads(line)
                entries.append(e)
                chars += len(e.get('clean', ''))
    index_data['volumes'][iso_vol] = {
        'entries': len(entries),
        'chars': chars,
        'tokens_est': int(chars * 0.75),
        'isolated': True,
    }

with open(CORPUS / 'index.json', 'w', encoding='utf-8') as f:
    json.dump(index_data, f, ensure_ascii=False, indent=2)

print(f"\n  Index summary:")
for vol, info in index_data['volumes'].items():
    iso = ' (isolated)' if info.get('isolated') else ''
    print(f"    {vol}{iso}: {info['entries']:,} entries, {info['chars']:,} chars, ~{info['tokens_est']:,} tokens")
print(f"    TOTAL: {index_data['total_entries']:,} entries, {index_data['total_chars']:,} chars, ~{index_data['estimated_tokens']:,} tokens")

# ── Step 6: Run verify.py ─────────────────────────────────────────

print("\n" + "=" * 60)
print("STEP 6: Run verify.py")
print("=" * 60)

import subprocess
result = subprocess.run(
    [str(BASE / '.venv' / 'Scripts' / 'python.exe'), str(BASE / 'scripts' / 'verify.py')],
    capture_output=True, text=True, timeout=60, cwd=str(BASE),
    encoding='utf-8', errors='replace'
)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[:500])

# ── Step 7: Re-run extractor for idempotency baseline ──────────────

print("\n" + "=" * 60)
print("STEP 7: Idempotency (save new MD5 baseline)")
print("=" * 60)

corpus_files = ['artifacts', 'books', 'characters', 'dialogue', 'excluded_ip',
                'lore', 'narrative', 'rogue', 'speakerless', 'unattributed', 'index']
hashes = {}
for fname in corpus_files:
    fpath = CORPUS / f'{fname}.jsonl'
    if fname == 'index':
        fpath = CORPUS / 'index.json'
    if fpath.exists():
        with open(fpath, 'rb') as f:
            h = hashlib.md5(f.read()).hexdigest()
        hashes[f'{fname}.jsonl' if fname != 'index' else 'index.json'] = h
        print(f"  {fname}: {h}")

with open(WORK / 'corpus_hashes.json', 'w', encoding='utf-8') as f:
    json.dump(hashes, f, ensure_ascii=False, indent=2)

# ── Step 8: Cite_id uniqueness assertion ───────────────────────────

print("\n" + "=" * 60)
print("STEP 8: Cite ID uniqueness")
print("=" * 60)

all_cids = []
for vol in volumes + ['speakerless', 'excluded_ip']:
    path = CORPUS / f'{vol}.jsonl'
    if not path.exists(): continue
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                all_cids.append(json.loads(line)['cite_id'])

unique = len(set(all_cids))
total = len(all_cids)
dup = total - unique
print(f"  Total cite_ids: {total}")
print(f"  Unique: {unique}")
print(f"  Duplicates: {dup}")
if dup == 0:
    print("  All cite_ids unique ✓")
else:
    from collections import Counter
    for cid, count in Counter(all_cids).most_common(10):
        if count > 1:
            print(f"    DUPLICATE: {cid} x{count}")

# ── Step 9: Save migration report ─────────────────────────────────

report = {
    'speakerless_remaining': len(isolated),
    'unattributed_created': len(unattributed),
    'unattributed_by_layer': dict(cats),
    'excluded_ip_final': len(excluded),
    'item_140615_returned': True,
    'cite_index': len(cite_index),
    'cite_whitelist': len(whitelist),
    'vol_stats': vol_stats,
    'index_data': index_data,
    'md5_hashes': hashes,
    'cite_id_unique': dup == 0,
}
with open(WORK / 'corpus_settlement_report.json', 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"\n{'=' * 60}")
print(f"CORPUS SETTLEMENT COMPLETE")
print(f"{'=' * 60}")
print(f"Report: work/corpus_settlement_report.json")
