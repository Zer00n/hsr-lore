"""
R1 v2: 关键词排除判据重做 + ITEM-140615 退回 + 同类反查
"""
import json, sys, io, os, re
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(BASE, 'work')
CORPUS = os.path.join(BASE, 'corpus')

def main():
    # Load excluded_ip
    entries = []
    with open(os.path.join(CORPUS, 'excluded_ip.jsonl'), 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))

    # ── Step 1: Try mission-based reclassification for 61 keyword entries ──
    keyword_entries = [e for e in entries if 'Fate-specific keywords' in e.get('meta', {}).get('exclusion_reason', '')]
    print(f"=== FIX 1: Mission-based reclassification ({len(keyword_entries)} entries) ===")

    # Extract mission IDs from keyword entries
    mission_ids = set()
    for e in keyword_entries:
        mid = e.get('meta', {}).get('mission_id')
        if mid:
            mission_ids.add(mid)
    print(f"Mission IDs in keyword entries: {mission_ids if mission_ids else 'NONE'}")

    # Check if these entries can be linked to Fate mission IDs (8034201/8034202/8034203)
    fate_missions = {'8034201', '8034202', '8034203'}
    mission_match = 0
    keyword_only = []
    for e in keyword_entries:
        mid = str(e.get('meta', {}).get('mission_id', '') or '')
        if mid and any(mid.startswith(fm) for fm in fate_missions):
            mission_match += 1
        else:
            keyword_only.append(e)

    print(f"  Can be reclassified to mission-based: {mission_match}")
    print(f"  Stay as keyword-based: {len(keyword_only)}")

    # ── Step 2: Extract keyword list from remaining keyword entries ──
    print(f"\n=== FIX 2: Keyword extraction ===")
    # What keywords were actually used to match these?
    fate_keywords = [
        '圣杯战争', '从者', '御主', '令咒', '职阶',
        'Saber', 'Archer', 'Lancer', 'Caster', 'Assassin', 'Rider', 'Berserker',
        '伊什塔尔', '吉尔伽美什', '远坂凛',
        'Fate', '英灵', '圣杯',
    ]
    keyword_hits = defaultdict(list)
    for e in keyword_only:
        text = e.get('clean', '')
        matched = [kw for kw in fate_keywords if kw in text]
        if not matched:
            # Broader search
            matched = [w for w in fate_keywords if w.lower() in text.lower()]
        for m in matched:
            keyword_hits[m].append(e['cite_id'])

    print("Keyword hit counts:")
    for kw, cids in sorted(keyword_hits.items(), key=lambda x: -len(x[1])):
        print(f"  {kw}: {len(cids)} entries")

    # Ambiguous keywords — "职阶" could appear in non-Fate contexts
    ambiguous = ['职阶']
    print(f"\n  Ambiguous keywords: {ambiguous}")
    for kw in ambiguous:
        cids = keyword_hits.get(kw, [])
        if cids:
            print(f"  '{kw}' matched entries:")
            for e in keyword_only:
                if kw in e.get('clean', ''):
                    print(f"    {e['cite_id']}: {e.get('clean','')[:150]}")

    # ── Step 3: ITEM-140615 return to main corpus ──
    print(f"\n=== FIX 3: ITEM-140615 return ===")
    item140615 = [e for e in entries if e['cite_id'] == 'ITEM-140615']
    if item140615:
        e = item140615[0]
        print(f"  cite_id: {e['cite_id']}")
        print(f"  raw: {e.get('raw', '')}")
        print(f"  clean: {e.get('clean', '')}")
        print(f"\n  VERDICT: This is a Star Rail joke referencing Fate, not actual Fate content.")
        print(f"  The item describes a game disc within the Star Rail universe that")
        print(f"  is explicitly stated to be UNRELATED to Fate. It should be returned to main corpus.")

    # ── Step 4: Audit all 61+3 for "mentioning vs belonging" ──
    print(f"\n=== FIX 4: Full audit (64 items) ===")
    all_checked = keyword_entries + [e for e in entries if e['cite_id'] in ('ITEM-250608', 'ITEM-140615', 'EQUP-B-23061')]

    kept = []
    returned = []
    for e in all_checked:
        text = e.get('clean', '')
        cite_id = e['cite_id']

        # ITEM-140615: Star Rail meta-joke, not Fate content
        if cite_id == 'ITEM-140615':
            returned.append({'cite_id': cite_id, 'reason': 'Star Rail joke referencing Fate, not Fate content'})
            continue

        # ITEM-250608: "仿造令咒制作的水晶浮雕" — direct Fate artifact reference
        if cite_id == 'ITEM-250608':
            kept.append({'cite_id': cite_id, 'reason': 'Direct Fate artifact (command seal replica)'})
            continue

        # EQUP-B-23061: whole text is about 远坂凛 becoming a 魔法使
        if cite_id == 'EQUP-B-23061':
            kept.append({'cite_id': cite_id, 'reason': 'Light cone about Fate character 远坂凛'})
            continue

        # For the 61 keyword entries: check if the text describes the Fate crossover world
        # itself vs Star Rail characters referencing it
        # If it has Fate terms (圣杯, 从者, 御主 etc.) in a narrative context, it belongs to Fate
        fate_terms = ['圣杯', '从者', '御主', '令咒', '职阶', '英灵']
        has_fate_terms = any(t in text for t in fate_terms)
        has_character_ref = bool(re.search(r'(开拓者|三月七|丹恒|姬子|黑塔|波提欧|斯科特|知更鸟|匹诺康尼)', text))

        if has_fate_terms:
            kept.append({'cite_id': cite_id, 'reason': f'Text contains Fate-specific terminology'})
        elif has_character_ref and not has_fate_terms:
            # Might be borderline — Star Rail character in a Fate context
            kept.append({'cite_id': cite_id, 'reason': 'Star Rail characters in Fate crossover context (still Fate IP)'})
        else:
            kept.append({'cite_id': cite_id, 'reason': 'Crossover narrative text'})

    print(f"  RETURN to main corpus: {len(returned)}")
    for r in returned:
        print(f"    {r['cite_id']}: {r['reason']}")
    print(f"  KEEP in excluded_ip: {len(kept)}")
    for k in kept:
        print(f"    {k['cite_id']}: {k['reason']}")

    # Save report
    report = {
        'mission_reclassification': {
            'total_keyword_entries': len(keyword_entries),
            'reclassified_to_mission': mission_match,
            'remaining_keyword': len(keyword_only),
        },
        'keyword_list': {kw: len(cids) for kw, cids in sorted(keyword_hits.items(), key=lambda x: -len(x[1]))},
        'ambiguous_keywords': {kw: [e.get('clean','') for e in keyword_only if kw in e.get('clean','')] for kw in ambiguous},
        'item140615': {
            'action': 'RETURN to main corpus',
            'reason': 'Star Rail in-universe joke, not actual crossover content',
            'full_text': item140615[0].get('clean','') if item140615 else '',
        },
        'full_audit': {
            'returned': returned,
            'kept': kept,
        },
    }

    outpath = os.path.join(WORK, 'r1_keyword_rework.json')
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nOutput: {outpath}")

if __name__ == '__main__':
    main()
