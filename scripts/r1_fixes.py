"""
R1: 三项修正
1. 提取 61 条关键词排除的完整原文
2. 贴出 ItemConfig 2 + ItemConfigEquipment 1 的完整内容
3. 对账 1,377+61+23=1,461 vs 1,465，找到缺失的 4 条
输出 work/r1_fixes.json
"""
import json, sys, io, os
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(BASE, 'work')
CORPUS = os.path.join(BASE, 'corpus')

def main():
    entries = []
    with open(os.path.join(CORPUS, 'excluded_ip.jsonl'), 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))

    print(f"Total excluded_ip entries: {len(entries)}")

    # ── Fix 1: 61 keyword-based exclusions ──
    keyword_excluded = []
    for e in entries:
        reason = e.get('meta', {}).get('exclusion_reason', '')
        if 'text contains Fate-specific keywords' in reason:
            keyword_excluded.append(e)

    print(f"\n=== Fix 1: Keyword-based exclusions ({len(keyword_excluded)} entries) ===")
    # Print full text of all 61 entries
    fix1_report = []
    for e in keyword_excluded:
        fix1_report.append({
            'cite_id': e['cite_id'],
            'source_table': e['source_table'],
            'source_pk': e['source_pk'],
            'title': e.get('title', ''),
            'raw_full_text': e.get('raw', ''),
            'clean_full_text': e.get('clean', ''),
            'meta': e.get('meta', {}),
        })

    for i, item in enumerate(fix1_report):
        print(f"\n[{i+1}] {item['cite_id']}")
        print(f"    table={item['source_table']} pk={item['source_pk']}")
        print(f"    title={item['title']}")
        print(f"    meta={json.dumps(item['meta'], ensure_ascii=False)}")
        print(f"    clean: {item['clean_full_text'][:200]}")
        if len(item['clean_full_text']) > 200:
            print(f"    ... (+{len(item['clean_full_text'])-200} chars)")

    # Also check: do any of these 61 also match speaker or mission criteria?
    keyword_only = []
    keyword_also_speaker = []
    keyword_also_mission = []
    for e in keyword_excluded:
        meta = e.get('meta', {})
        has_speaker = 'speaker' in meta and meta.get('speaker') not in (None, '')
        has_mission = 'mission_id' in meta and meta.get('mission_id') not in (None, '')
        if has_mission:
            keyword_also_mission.append(e)
        elif has_speaker:
            keyword_also_speaker.append(e)
        else:
            keyword_only.append(e)

    print(f"\n  (Have speaker criterion too): {len(keyword_also_speaker)}")
    print(f"  (Have mission criterion too): {len(keyword_also_mission)}")
    print(f"  (Keyword-only, no other criterion): {len(keyword_only)}")
    # Print the keyword-only ones' text separately
    for e in keyword_only:
        print(f"  KEYWORD-ONLY: {e['cite_id']} — {e.get('clean','')[:150]}")

    # ── Fix 2: ItemConfig + ItemConfigEquipment exclusions ──
    item_excluded = [e for e in entries if e['source_table'] in ('ItemConfig', 'ItemConfigEquipment')]
    print(f"\n=== Fix 2: Artifact exclusions ({len(item_excluded)} entries) ===")
    for e in item_excluded:
        print(f"\n  cite_id={e['cite_id']}")
        print(f"  table={e['source_table']} pk={e['source_pk']}")
        print(f"  title={e.get('title', '')}")
        print(f"  raw={e.get('raw', '')}")
        print(f"  clean={e.get('clean', '')}")
        print(f"  meta={json.dumps(e.get('meta', {}), ensure_ascii=False)}")

    # ── Fix 3: Count reconciliation ──
    print(f"\n=== Fix 3: Count reconciliation ===")
    # Categorize every entry by exclusion basis
    speaker_count = 0
    mission_count = 0
    keyword_count = 0
    avatar_count = 0
    composite_count = 0
    other_count = 0
    uncategorized = []

    for e in entries:
        meta = e.get('meta', {})
        reason = meta.get('exclusion_reason', '')
        has_speaker = 'speaker' in meta and meta.get('speaker') not in (None, '')
        has_mission = 'mission_id' in meta
        has_keyword = 'Fate-specific keywords' in reason
        has_avatar = 'AvatarID not in AvatarConfig' in reason
        has_composite = 'composite speaker' in reason

        if has_composite:
            composite_count += 1
        elif has_avatar:
            avatar_count += 1
        elif has_mission and not has_speaker:
            mission_count += 1
        elif has_speaker and not has_mission:
            speaker_count += 1
        elif has_keyword:
            keyword_count += 1
        else:
            other_count += 1
            uncategorized.append(e)

    print(f"  VoiceAtlas (AvatarID): {avatar_count}")
    print(f"  TalkSentence (speaker): {speaker_count}")
    print(f"  TalkSentence (keyword): {keyword_count}")
    print(f"  TalkSentence (mission): {mission_count}")
    print(f"  Composite speaker: {composite_count}")
    print(f"  Other: {other_count}")
    print(f"  Sum: {avatar_count + speaker_count + keyword_count + mission_count + composite_count + other_count}")
    print(f"  Expected: {len(entries)}")

    if uncategorized:
        print(f"\n  Uncategorized entries ({len(uncategorized)}):")
        for e in uncategorized:
            print(f"    {e['cite_id']}: meta={json.dumps(e.get('meta',{}), ensure_ascii=False)[:200]}")

    # ── Fix 3 part 2: count by actual speaker field values ──
    speaker_field_counts = Counter()
    for e in entries:
        sp = e.get('meta', {}).get('speaker', '')
        if sp:
            speaker_field_counts[sp] += 1

    print(f"\n  Speaker field distribution in excluded_ip:")
    for sp, cnt in speaker_field_counts.most_common(20):
        print(f"    {sp}: {cnt}")

    # ── Fix 3 part 3: check composite speaker labels ──
    composite_entries = [e for e in entries if 'composite' in e.get('meta', {}).get('exclusion_reason', '')]
    print(f"\n  Composite speaker entries ({len(composite_entries)}):")
    for e in composite_entries:
        sp = e.get('meta', {}).get('speaker', '')
        print(f"    {e['cite_id']}: speaker='{sp}' reason={e.get('meta',{}).get('exclusion_reason','')}")

    # Save report
    report = {
        'fix1_keyword_excluded': {
            'count': len(keyword_excluded),
            'full_entries': fix1_report,
            'keyword_only_no_other_criteria': len(keyword_only),
        },
        'fix2_artifact_exclusions': {
            'count': len(item_excluded),
            'entries': [{
                'cite_id': e['cite_id'],
                'source_table': e['source_table'],
                'source_pk': e['source_pk'],
                'title': e.get('title', ''),
                'raw': e.get('raw', ''),
                'clean': e.get('clean', ''),
                'meta': e.get('meta', {}),
            } for e in item_excluded],
        },
        'fix3_count_reconciliation': {
            'avatar_not_in_config': avatar_count,
            'speaker_based': speaker_count,
            'keyword_based': keyword_count,
            'mission_based': mission_count,
            'composite': composite_count,
            'other': other_count,
            'total': avatar_count + speaker_count + keyword_count + mission_count + composite_count + other_count,
            'expected': len(entries),
            'speaker_distribution': dict(speaker_field_counts.most_common()),
        },
    }

    outpath = os.path.join(WORK, 'r1_fixes.json')
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nOutput: {outpath}")

if __name__ == '__main__':
    main()
