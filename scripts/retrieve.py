"""
B4: retrieved_corpus 构造链路
完整管线：实体对 → OpenViking检索 → 解析URI → cite_id → cite_index取原文 → 格式化

开发阶段使用 mock OpenViking 响应，不真连库。
但链路每一环都真实执行：特别是 cite_index 取原文。

OpenViking L0/L1 摘要绝不可进入 retrieved_corpus——只能放 cite_index 原文。
"""
import json
import sys
import io
import hashlib
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(__file__).parent.parent
WORK = BASE / 'work'
CONFIG = BASE / 'config'

# ── Mock OpenViking responses for development ─────────────────────

# Mapping: entity_name → list of {uri, level, score, abstract}
# cite_id embedded in URI path for parsing
MOCK_OV_RESPONSES = {
    '三月七': [
        {'uri': 'viking://resources/hsr/characters/三月七/profile.md#cite=AVTR-N-1001',
         'level': 'L0', 'score': 0.95, 'abstract': '[L0] 三月七是星穹列车的成员之一...'},
        {'uri': 'viking://resources/hsr/narrative/雅利洛-VI/mission-001.md#cite=STRY-101-1',
         'level': 'L0', 'score': 0.72, 'abstract': '[L0] 三月七前往贝洛伯格调查星核...'},
    ],
    '丹恒': [
        {'uri': 'viking://resources/hsr/characters/丹恒/profile.md#cite=AVTR-N-1002',
         'level': 'L0', 'score': 0.93, 'abstract': '[L0] 丹恒是列车的护卫，沉默寡言...'},
        {'uri': 'viking://resources/hsr/characters/丹恒/stories.md#cite=STRY-1002-1',
         'level': 'L1', 'score': 0.81, 'abstract': '[L1] 丹恒的过去与仙舟龙尊有关...'},
    ],
    '景元': [
        {'uri': 'viking://resources/hsr/characters/景元/profile.md#cite=AVTR-N-1003',
         'level': 'L0', 'score': 0.91, 'abstract': '[L0] 景元是仙舟罗浮的将军...'},
        {'uri': 'viking://resources/hsr/lore/nouns/仙舟罗浮.md#cite=NOUN-301-1',
         'level': 'L1', 'score': 0.65, 'abstract': '[L1] 仙舟罗浮由景元统领...'},
    ],
    '星穹列车': [
        {'uri': 'viking://resources/hsr/lore/nouns/星穹列车.md#cite=NOUN-1001',
         'level': 'L0', 'score': 0.97, 'abstract': '[L0] 星穹列车穿梭于星辰之间...'},
    ],
    '星核猎手': [
        {'uri': 'viking://resources/hsr/lore/nouns/星核猎手.md#cite=NOUN-1002',
         'level': 'L0', 'score': 0.94, 'abstract': '[L0] 星核猎手是一群追踪星核的人...'},
    ],
    '贝洛伯格': [
        {'uri': 'viking://resources/hsr/lore/nouns/雅利洛-Ⅵ.md#cite=NOUN-201-1',
         'level': 'L0', 'score': 0.92, 'abstract': '[L0] 雅利洛-VI是冰封的星球...'},
    ],
}

# Fallback for unknown entities
_MOCK_FALLBACK_URIS = [
    {'uri': 'viking://resources/hsr/lore/general.md#cite=AEON-1-1',
     'level': 'L0', 'score': 0.55, 'abstract': '[L0] General lore entry...'},
    {'uri': 'viking://resources/hsr/books/series-1.md#cite=BOOK-1-1',
     'level': 'L1', 'score': 0.45, 'abstract': '[L1] Book reference...'},
]


# ── Cite index loader ────────────────────────────────────────────

def load_cite_index():
    """Load cite_index.jsonl → {cite_id: {cite_id, clean, volume}}."""
    idx = {}
    path = WORK / 'cite_index.jsonl'
    if not path.exists():
        print("WARNING: cite_index.jsonl not found")
        return idx
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            idx[rec['cite_id']] = rec
    return idx


# ── URI → cite_id parser ─────────────────────────────────────────

def parse_cite_ids_from_hits(hits: List[Dict]) -> List[str]:
    """Extract cite_ids from OpenViking hit URIs.

    Expected URI format: ...#cite=CITE_ID or .../cite=CITE_ID
    """
    cite_ids = []
    for hit in hits:
        uri = hit.get('uri', '')
        # Try #cite= pattern
        m = re.search(r'#cite=([A-Za-z0-9_-]+)', uri)
        if m:
            cite_ids.append(m.group(1))
            continue
        # Try /cite= pattern
        m = re.search(r'/cite=([A-Za-z0-9_-]+)', uri)
        if m:
            cite_ids.append(m.group(1))
    return sorted(set(cite_ids))


# ── Query OpenViking ─────────────────────────────────────────────

def query_openviking(entity_name: str, mock: bool = True) -> List[Dict]:
    """Query OpenViking for a given entity name.

    Args:
        entity_name: The entity canonical name to search for
        mock: If True, use mock responses for development

    Returns:
        List of {uri, level, score, abstract} hits
    """
    if mock:
        if entity_name in MOCK_OV_RESPONSES:
            return MOCK_OV_RESPONSES[entity_name]
        # Fuzzy match
        for known_name, hits in MOCK_OV_RESPONSES.items():
            if known_name in entity_name or entity_name in known_name:
                return hits
        return _MOCK_FALLBACK_URIS

    # TODO: Real OpenViking API call
    # import urllib.request
    # config = load_ov_config()
    # url = f"{config['endpoint']}/query?q={entity_name}&namespace={config['namespace']}"
    # ...
    raise NotImplementedError(
        "Real OpenViking API not yet implemented. Use mock=True for development."
    )


# ── Fetch from cite_index ────────────────────────────────────────

def fetch_from_cite_index(cite_ids: List[str], cite_index: Dict) -> List[Dict]:
    """Fetch clean text for cite_ids from cite_index.

    Returns list of {cite_id, clean, volume} dicts.
    Only the clean text (not L0/L1 abstracts) is returned.
    """
    entries = []
    for cid in cite_ids:
        rec = cite_index.get(cid)
        if rec and rec.get('clean'):
            entries.append({
                'cite_id': cid,
                'clean': rec['clean'],
                'volume': rec.get('volume', ''),
            })
    return entries


# ── Format retrieved corpus ──────────────────────────────────────

def format_retrieved_corpus(entries: List[Dict]) -> str:
    """Format fetched entries as [cite_id]\\n{clean}\\n\\n blocks.

    This is the same format as the pass1 corpus input, so models
    can use the same citation pattern.
    """
    blocks = []
    for entry in entries:
        blocks.append(f"[{entry['cite_id']}]\n{entry['clean']}\n")
    return '\n'.join(blocks)


# ── Full pipeline ────────────────────────────────────────────────

def retrieve_for_entity(entity_name: str, cite_index: Dict,
                        mock: bool = True) -> Dict:
    """Run the full retrieval pipeline for a single entity.

    Returns:
        {query, ov_hits, fetched_cites, corpus_text, unused_cites}
    """
    result = {
        'query': entity_name,
        'ov_hits': [],
        'fetched_cites': [],
        'corpus_text': '',
        'unused_cites': [],
    }

    # Step 1: Query OpenViking
    hits = query_openviking(entity_name, mock=mock)
    result['ov_hits'] = hits

    # Step 2: Parse cite_ids from hit URIs
    cite_ids = parse_cite_ids_from_hits(hits)
    if not cite_ids:
        return result

    # Step 3: Fetch from cite_index (only clean text, no L0/L1 abstracts)
    entries = fetch_from_cite_index(cite_ids, cite_index)
    result['fetched_cites'] = [e['cite_id'] for e in entries]

    # Step 4: Format as [cite_id]\n{clean}\n\n
    result['corpus_text'] = format_retrieved_corpus(entries)

    # Track unused (fetched but not yet cited — populated after model call)
    result['unused_cites'] = list(result['fetched_cites'])

    return result


def retrieve_for_entity_pair(entity1: str, entity2: str, cite_index: Dict,
                             mock: bool = True) -> Dict:
    """Run retrieval for a pair of entities (used by T5).

    Queries both entities independently, deduplicates results.
    """
    r1 = retrieve_for_entity(entity1, cite_index, mock=mock)
    r2 = retrieve_for_entity(entity2, cite_index, mock=mock)

    # Merge and deduplicate
    all_hits = r1['ov_hits'] + r2['ov_hits']
    all_fetched = sorted(set(r1['fetched_cites'] + r2['fetched_cites']))

    # Re-format merged corpus
    all_entries = fetch_from_cite_index(all_fetched, cite_index)
    merged_text = format_retrieved_corpus(all_entries)

    return {
        'query': f'{entity1} + {entity2}',
        'ov_hits': all_hits,
        'fetched_cites': all_fetched,
        'corpus_text': merged_text,
        'unused_cites': list(all_fetched),
        'sub_queries': [r1, r2],
    }


# ── CLI test ─────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Retrieval pipeline test')
    parser.add_argument('entity', nargs='*', help='Entity names to retrieve for')
    parser.add_argument('--mock', action='store_true', default=True,
                        help='Use mock OpenViking (default)')
    args = parser.parse_args()

    cite_index = load_cite_index()
    if not cite_index:
        print("ERROR: cite_index.jsonl not found")
        return 1

    test_entities = args.entity if args.entity else ['三月七', '丹恒', '景元']

    for entity_name in test_entities:
        print(f"\n{'=' * 60}")
        print(f"Retrieval for: {entity_name}")
        print(f"{'=' * 60}")

        result = retrieve_for_entity(entity_name, cite_index, mock=args.mock)

        print(f"  OpenViking hits: {len(result['ov_hits'])}")
        for hit in result['ov_hits']:
            print(f"    - {hit['level']} {hit['uri'][:80]}... (score={hit['score']})")
            print(f"      Abstract: {hit['abstract'][:80]}...")
            print(f"      ⚠ This abstract is for debugging only. It MUST NOT enter retrieved_corpus.")

        print(f"\n  Parsed cite_ids: {result['fetched_cites']}")

        print(f"\n  Corpus text first 300 chars:")
        print(f"  {result['corpus_text'][:300]}...")

        print(f"\n  Pipeline check:")
        checks = []
        checks.append(('OV query', len(result['ov_hits']) > 0))
        checks.append(('cite_id parsing', len(result['fetched_cites']) > 0))
        checks.append(('cite_index fetch', len(result['corpus_text']) > 0))
        checks.append(('No L0/L1 in corpus', '[L0]' not in result['corpus_text'] and '[L1]' not in result['corpus_text']))
        for check_name, passed in checks:
            status = '✓' if passed else '✗'
            print(f"    [{status}] {check_name}")


if __name__ == '__main__':
    main()
