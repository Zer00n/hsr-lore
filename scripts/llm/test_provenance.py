"""
溯源链 mock 测试
验证 provenance.jsonl 的结构完整性和可读性。
不调用真实模型，使用假数据。
"""
import json, sys, io, os
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / 'scripts' / 'llm'))

from client import EvidenceLogger

def main():
    run_id = "prov_mock_001"

    # Clean up previous run
    import shutil
    prev_dir = Path("logs/runs") / run_id
    if prev_dir.exists():
        shutil.rmtree(prev_dir)

    logger = EvidenceLogger(run_id)

    # Simulate provenance chains for 5 scenarios
    scenarios = [
        {
            'query': '纳努克与毁灭命途的关系',
            'ov_hits': [
                {'uri': 'viking://resources/hsr/lore/aeons/纳努克.md', 'level': 2, 'score': 0.594, 'abstract': '纳努克是毁灭星神，执掌毁灭命途...'},
                {'uri': 'viking://resources/hsr/lore/nouns/毁灭命途.md', 'level': 2, 'score': 0.512, 'abstract': '毁灭命途是纳努克所执掌的命途...'},
                {'uri': 'viking://resources/hsr/lore/nouns/绝灭大君.md', 'level': 2, 'score': 0.481, 'abstract': '绝灭大君是纳努克麾下的令使...'},
            ],
            'fetched_cites': ['AEON-1', 'NOUN-5', 'NOUN-12'],
            'cited': ['AEON-1', 'NOUN-5'],
            'unused': ['NOUN-12'],
        },
        {
            'query': '匹诺康尼的家族势力',
            'ov_hits': [
                {'uri': 'viking://resources/hsr/lore/nouns/匹诺康尼家族.md', 'level': 2, 'score': 0.623, 'abstract': '匹诺康尼由多个家族势力共同统治...'},
                {'uri': 'viking://resources/hsr/lore/worlds/匹诺康尼.md', 'level': 2, 'score': 0.587, 'abstract': '匹诺康尼是盛会之星...'},
                {'uri': 'viking://resources/hsr/lore/nouns/橡木家系.md', 'level': 2, 'score': 0.551, 'abstract': '橡木家系是匹诺康尼的统治家族...'},
                {'uri': 'viking://resources/hsr/lore/nouns/猎犬家系.md', 'level': 2, 'score': 0.498, 'abstract': '猎犬家系掌管匹诺康尼的安保...'},
                {'uri': 'viking://resources/hsr/lore/nouns/鸢尾花家系.md', 'level': 2, 'score': 0.445, 'abstract': '鸢尾花家系负责匹诺康尼的文化事务...'},
            ],
            'fetched_cites': ['NOUN-8', 'WRLD-401', 'NOUN-15', 'NOUN-16', 'NOUN-20'],
            'cited': ['NOUN-8', 'WRLD-401', 'NOUN-15'],
            'unused': ['NOUN-16', 'NOUN-20'],
        },
        {
            'query': '雅利洛-VI的寒潮起源',
            'ov_hits': [
                {'uri': 'viking://resources/hsr/lore/worlds/雅利洛-VI.md', 'level': 2, 'score': 0.671, 'abstract': '雅利洛-VI因星核影响陷入永恒寒潮...'},
                {'uri': 'viking://resources/hsr/books/雅利洛-VI/春神和战争之神雅利洛.md', 'level': 2, 'score': 0.523, 'abstract': '讲述雅利洛星球的历史神话...'},
            ],
            'fetched_cites': ['WRLD-201', 'BOOK-190572-1'],
            'cited': ['WRLD-201'],
            'unused': ['BOOK-190572-1'],
        },
        # Edge case 1: low hit_utilization — 5 hits but only 1 URI contributes citations
        {
            'query': '某势力A是否与某势力B结盟',
            'ov_hits': [
                {'uri': 'viking://resources/hsr/lore/nouns/A势力.md', 'level': 2, 'score': 0.600, 'abstract': 'A势力简介...'},
                {'uri': 'viking://resources/hsr/lore/nouns/B势力.md', 'level': 2, 'score': 0.580, 'abstract': 'B势力简介...'},
                {'uri': 'viking://resources/hsr/artifacts/items/A相关道具.md', 'level': 2, 'score': 0.400, 'abstract': 'A势力相关道具...'},
                {'uri': 'viking://resources/hsr/dialogue/by-speaker/无名NPC.md', 'level': 2, 'score': 0.350, 'abstract': 'NPC提及A和B...'},
                {'uri': 'viking://resources/hsr/books/A势力野史.md', 'level': 2, 'score': 0.300, 'abstract': 'A势力野史...'},
            ],
            'fetched_cites': ['NOUN-100', 'NOUN-200', 'ITEM-50', 'TALK-9999', 'BOOK-888'],
            'cited': ['NOUN-100'],  # Only one cite from the first URI
            'unused': ['NOUN-200', 'ITEM-50', 'TALK-9999', 'BOOK-888'],
        },
        # Edge case 2: citation_yield = 0 — all fetched, none cited
        {
            'query': '关于某个不存在于语料中的概念',
            'ov_hits': [
                {'uri': 'viking://resources/hsr/lore/nouns/类似概念A.md', 'level': 2, 'score': 0.300, 'abstract': '类似概念A...'},
                {'uri': 'viking://resources/hsr/lore/nouns/类似概念B.md', 'level': 2, 'score': 0.250, 'abstract': '类似概念B...'},
            ],
            'fetched_cites': ['NOUN-999', 'NOUN-998'],
            'cited': [],
            'unused': ['NOUN-999', 'NOUN-998'],
        },
    ]

    for i, s in enumerate(scenarios):
        step_id = logger.log_provenance(
            query=s['query'],
            ov_hits=s['ov_hits'],
            fetched_cites=s['fetched_cites'],
            cited=s['cited'],
            unused=s['unused'],
            step_id=f"step-{i+1:03d}",
        )
        print(f"  [{step_id}] query='{s['query'][:30]}...' → {len(s['cited'])}/{len(s['fetched_cites'])} cited, {len(s['unused'])} unused")

    # Read back and verify
    prov_path = Path("logs/runs") / run_id / "provenance.jsonl"
    print(f"\nProvenance file: {prov_path}")

    with open(prov_path, 'r', encoding='utf-8') as f:
        records = [json.loads(line) for line in f if line.strip()]

    print(f"\nVerification:")
    print(f"  Total records: {len(records)}")
    for r in records:
        cited_pct = r.get('citation_yield', 0) * 100
        hit_pct = r.get('hit_utilization', 0) * 100
        print(f"  [{r['step_id']}] query='{r['query'][:40]}...' citation_yield={cited_pct:.0f}% hit_util={hit_pct:.0f}%")

    # Verify structure completeness
    required_fields = ['step_id', 'timestamp', 'query', 'ov_hits', 'fetched_cite_count',
                       'cited_count', 'unused_count', 'cited_cite_ids', 'unused_cite_ids',
                       'citation_yield', 'hit_utilization']
    all_ok = True
    for r in records:
        for field in required_fields:
            if field not in r:
                print(f"  MISSING: {field} in {r['step_id']}")
                all_ok = False

    if all_ok:
        print(f"\nAll {len(records)} records pass structure check.")
        print(f"Provenance chain is operational.")

    # Output one full record as sample
    print(f"\nSample record:")
    print(json.dumps(records[0], ensure_ascii=False, indent=2)[:1000])

if __name__ == '__main__':
    main()
