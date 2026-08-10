"""
分块方案生成器 v2
v2 changes: dialogue aggregated to ~500K per chunk, books split to 3-4 chunks
"""
import json, sys, io, os, re
from collections import defaultdict, OrderedDict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = Path(__file__).parent.parent
WORK = BASE / 'work'
CORPUS = BASE / 'corpus'
CONFIG = BASE / 'config'

sys.path.insert(0, str(BASE / 'scripts'))
from token_utils import TOKEN_COEFFICIENT, MAX_TOKENS_PER_CHUNK, PROMPT_OVERHEAD, PER_ENTRY_OVERHEAD, estimate_chunk_tokens, estimate_entry_tokens

MAX_TOKENS = MAX_TOKENS_PER_CHUNK  # 55万 token per chunk
SPEAKER_TO_WORLD = {
    # 仙舟罗浮 (301)
    '景元': 301, '彦卿': 301, '符玄': 301, '白露': 301, '停云': 301,
    '青雀': 301, '素裳': 301, '桂乃芬': 301, '藿藿': 301, '尾巴': 301,
    '驭空': 301, '椒丘': 301, '飞霄': 301, '灵砂': 301, '镜流': 301,
    '罗刹': 301, '雪衣': 301, '寒鸦': 301, '公输师傅': 301, '铖杰': 301,
    '明曦': 301, '净砚': 301, '夕葵': 301, '大毫': 301, '燕翠': 301,
    '丹枢': 301, '晴霓': 301, '梓桥': 301, '西衍先生': 301,
    '浮烟': 301, '呼雷': 301, '斯科特': 301, '斯科特专员': 301,
    # 匹诺康尼 (401)
    '星期日': 401, '知更鸟': 401, '砂金': 401, '黑天鹅': 401, '黄泉': 401,
    '花火': 401, '米沙': 401, '加拉赫': 401, '波提欧': 401, '舒翁': 401,
    '乔瓦尼': 401, '钟表小子': 401, '爱德华医生': 401, '老奥帝': 401,
    '皮斯': 401, '猎犬家系成员': 401, '铁皮人': 401, '满愿': 401,
    '希拉': 401, '伍尔西': 401, '玛丽小姐': 401, '愚致思': 401,
    '掘掘博士': 401, '妃色夫人': 401, '伦纳德': 401,
    # 空间站 (101)
    '黑塔': 101, '艾丝妲': 101, '阿兰': 101, '螺丝咕姆': 101, '阮•梅': 101,
    '科员': 101, '维修工程师': 101, '教育部官员': 101,
    # 雅利洛-VI (201)
    '布洛妮娅': 201, '希儿': 201, '娜塔莎': 201, '杰帕德': 201, '希露瓦': 201,
    '佩拉': 201, '桑博': 201, '卢卡': 201, '玲可': 201, '虎克': 201,
    '克拉拉': 201, '史瓦罗': 201, '奥列格': 201, '可可利亚': 201, '邓恩': 201,
    # 翁法罗斯 (501)
    '白厄': 501, '遐蝶': 501, '万敌': 501, '缇宝': 501, '阿格莱雅': 501,
    '刻律德菈': 501, '那刻夏': 501, '风堇': 501, '赛飞儿': 501, '海瑟音': 501,
    '昔涟': 501, '爻光': 501, '虚照': 501, '格奈乌斯': 501, '暗布雷拉': 501,
    '瑟希斯': 501, '缇宁': 501, '缇安': 501, '迷迷': 501, '卡厄斯兰那': 501,
    # 星穹列车 (core cast)
    '三月七': 100, '丹恒': 100, '姬子': 100, '瓦尔特': 100, '帕姆': 100,
    '{NICKNAME}': 100, 'Player': 100,
    # Other major factions
    '流萤': 401, '银狼': 401, '卡芙卡': 401, '刃': 401, '火花': 401,  # 星核猎手
    '托帕': 0, '翡翠': 0, '砂金': 401,  # 公司 (scattered)
    '真理医生': 0, '阮梅': 101, '阮•梅': 101,  # 天才俱乐部 (scattered)
    '乱破': 0, '云璃': 0, '貊泽': 0, '飞霄': 301, '椒丘': 301,  # scattered
    '大黑塔': 0, '忘归人': 0, '银枝': 0, '长夜月': 0,
}

def world_for_speaker(sp):
    """Return a world affinity number for a speaker."""
    return SPEAKER_TO_WORLD.get(sp, -1)

def chunk_dialogue(entries):
    """Aggregate dialogue speakers to ~500K token blocks."""
    by_speaker = defaultdict(list)
    for e in entries:
        sp = e.get('meta', {}).get('speaker', '') or e.get('meta', {}).get('sender', 'system')
        by_speaker[sp].append(e)

    # Sort speakers: major (≥100 entries) first, by world affinity, then by size
    major = {sp: ents for sp, ents in by_speaker.items() if len(ents) >= 100}
    minor = {sp: ents for sp, ents in by_speaker.items() if len(ents) < 100}

    # Sort major by world affinity then by size
    def sort_key(item):
        sp, ents = item
        w = world_for_speaker(sp)
        return (w, -len(ents))

    sorted_major = sorted(major.items(), key=sort_key)

    chunks = []
    current_ents = []
    current_tokens = 0
    current_world = None

    for sp, ents in sorted_major:
        stokens = estimate_chunk_tokens(ents)
        w = world_for_speaker(sp)

        # Start new chunk if adding would exceed budget, or world changes and current is large enough
        if current_ents and current_tokens + stokens > MAX_TOKENS:
            cids = [e['cite_id'] for e in current_ents]
            chunks.append({'cite_ids': cids, 'token_est': current_tokens,
                          'description': f'{len(current_ents)} entries from {len(set(e.get("meta",{}).get("speaker","") or e.get("meta",{}).get("sender","") for e in current_ents))} speakers'})
            current_ents = []
            current_tokens = 0
            current_world = None

        current_ents.extend(ents)
        current_tokens += stokens
        current_world = w

    # Add remaining major speakers
    if current_ents:
        cids = [e['cite_id'] for e in current_ents]
        chunks.append({'cite_ids': cids, 'token_est': current_tokens,
                      'description': f'{len(current_ents)} entries from major speakers'})

    # Minor speakers: aggregate to ~500K
    minor_all = []
    minor_tokens = 0
    for sp in sorted(minor, key=lambda x: -len(minor[x])):
        for e in sorted(minor[sp], key=lambda x: x.get('meta', {}).get('speaker', '')):
            t = estimate_entry_tokens(e)
            if minor_all and minor_tokens + t > MAX_TOKENS:
                cids = [e['cite_id'] for e in minor_all]
                chunks.append({'cite_ids': cids, 'token_est': minor_tokens,
                              'description': f'{len(minor_all)} entries from minor speakers'})
                minor_all = []
                minor_tokens = 0
            minor_all.append(e)
            minor_tokens += t

    if minor_all:
        cids = [e['cite_id'] for e in minor_all]
        chunks.append({'cite_ids': cids, 'token_est': minor_tokens,
                      'description': f'{len(minor_all)} entries from minor speakers'})

    return chunks

def chunk_books(entries):
    """Split books into 3-4 chunks by series grouping."""
    by_series = defaultdict(list)
    for e in entries:
        sid = e.get('meta', {}).get('book_series_id', 0) or 0
        by_series[sid].append(e)

    # Sort by total chars descending
    sorted_series = sorted(by_series.items(), key=lambda x: -sum(len(e.get('clean','')) for e in x[1]))

    TARGET = MAX_TOKENS  # use same limit as everything else
    chunks = []
    current_ents = []
    current_tokens = 0

    for sid, ents in sorted_series:
        stokens = estimate_chunk_tokens(ents)
        if current_ents and current_tokens + stokens > TARGET:
            cids = [e['cite_id'] for e in current_ents]
            chunks.append({'cite_ids': cids, 'token_est': current_tokens,
                          'description': f'{len(current_ents)} entries, {len(set(e.get("meta",{}).get("book_series_id",0) for e in current_ents))} series'})
            current_ents = []
            current_tokens = 0
        current_ents.extend(ents)
        current_tokens += stokens

    if current_ents:
        cids = [e['cite_id'] for e in current_ents]
        chunks.append({'cite_ids': cids, 'token_est': current_tokens,
                      'description': f'{len(current_ents)} entries, {len(set(e.get("meta",{}).get("book_series_id",0) for e in current_ents))} series'})

    return chunks

def chunk_by_world(entries):
    """Chunk narrative by world_id (unchanged)."""
    by_world = defaultdict(list)
    for e in entries:
        wid = e.get('meta', {}).get('world_id', 0) or 0
        by_world[wid].append(e)
    chunks = []
    for wid in sorted(by_world):
        wentries = by_world[wid]
        tokens = estimate_chunk_tokens(wentries)
        world_name = wentries[0].get('meta', {}).get('world_name', f'world-{wid}')
        cids = [e['cite_id'] for e in wentries]
        chunks.append({'cite_ids': cids, 'token_est': tokens,
                      'description': f'world {wid} ({world_name}), {len(wentries)} entries'})
    return chunks

def chunk_by_prefix(entries, prefix_len=5):
    """Chunk unattributed by prefix (unchanged)."""
    by_prefix = defaultdict(list)
    for e in entries:
        pk = str(e.get('source_pk', ''))
        p = pk[:prefix_len] if len(pk) >= prefix_len else pk
        by_prefix[p].append(e)
    chunks = []
    current_ents = []
    current_tokens = 0
    for p in sorted(by_prefix):
        pentries = by_prefix[p]
        ptokens = estimate_chunk_tokens(pentries)
        if current_ents and current_tokens + ptokens > MAX_TOKENS:
            cids = [e['cite_id'] for e in current_ents]
            chunks.append({'cite_ids': cids, 'token_est': current_tokens,
                          'description': f'prefix groups, {len(current_ents)} entries'})
            current_ents = []
            current_tokens = 0
        current_ents.extend(pentries)
        current_tokens += ptokens
    if current_ents:
        cids = [e['cite_id'] for e in current_ents]
        chunks.append({'cite_ids': cids, 'token_est': current_tokens,
                      'description': f'prefix groups, {len(current_ents)} entries'})
    return chunks

def main():
    CONFIG.mkdir(exist_ok=True)
    volumes = {}
    for vol in ['lore','books','characters','narrative','dialogue','artifacts','rogue','unattributed']:
        entries = []
        with open(CORPUS / f'{vol}.jsonl','r',encoding='utf-8') as f:
            for line in f:
                if line.strip(): entries.append(json.loads(line))
        volumes[vol] = entries

    token_ests = {vol: estimate_chunk_tokens(entries) for vol, entries in volumes.items()}
    for vol, t in token_ests.items():
        print(f'{vol}: {len(volumes[vol])} entries, ~{t:,} tokens')

    chunk_plan = {}
    for vol in ['lore','characters','rogue','artifacts']:
        cids = [e['cite_id'] for e in volumes[vol]]
        chunk_plan[vol] = [{'cite_ids': cids, 'token_est': token_ests[vol], 'description': f'full volume'}]
    chunk_plan['narrative'] = chunk_by_world(volumes['narrative'])
    chunk_plan['unattributed'] = chunk_by_prefix(volumes['unattributed'])
    chunk_plan['books'] = chunk_books(volumes['books'])
    chunk_plan['dialogue'] = chunk_dialogue(volumes['dialogue'])

    all_chunks = []
    chunk_id = 0
    for vol in ['lore','books','characters','narrative','dialogue','artifacts','rogue','unattributed']:
        for c in chunk_plan[vol]:
            chunk_id += 1
            all_chunks.append({
                'chunk_id': f'C{chunk_id:03d}',
                'volume': vol, 'token_est': c['token_est'],
                'entry_count': len(c['cite_ids']), 'cite_ids': c['cite_ids'],
                'description': c['description'],
            })

    print(f'\n=== Chunk Plan: {len(all_chunks)} chunks ===')
    total_tokens = 0
    for c in all_chunks:
        total_tokens += c['token_est']
        print(f"{c['chunk_id']:>5s} {c['volume']:>15s} {c['entry_count']:>8,d} {c['token_est']:>12,} {c['description'][:60]}")

    pass1_tokens = sum(c['token_est'] for c in all_chunks)
    print(f'\nPass 1 input: {pass1_tokens:,} tokens across {len(all_chunks)} chunks')
    print(f'Pass 2 cost: 待 pass1 完成后根据实际产出量计算')

    task_matrix = {
        'T1_entity_relation': {'task_id':'T1','name':'实体与关系','pass':1,'applies_to':['lore','books','characters','narrative','dialogue','artifacts','rogue','unattributed']},
        'T2_event': {'task_id':'T2','name':'事件','pass':1,'applies_to':['lore','books','characters','narrative','unattributed']},
        'T3_discrepancy_intra': {'task_id':'T3','name':'卷内矛盾','pass':1,'applies_to':['lore','books','characters','narrative','artifacts','rogue']},
        'T4_entity_merge': {'task_id':'T4','name':'实体归并','pass':2,'applies_to':['*']},
        'T5_relation_cross': {'task_id':'T5','name':'跨卷关系','pass':2,'applies_to':['*']},
        'T6_discrepancy_cross': {'task_id':'T6','name':'跨卷矛盾','pass':2,'applies_to':['*']},
        'T7_event_timeline': {'task_id':'T7','name':'跨块事件时序','pass':2,'applies_to':['*']},
    }

    pass1_input = sum(c['token_est'] for c in all_chunks for tname, t in task_matrix.items() if t['pass']==1 and c['volume'] in t['applies_to'])

    chunk_data = {
        'chunks': all_chunks, 'task_matrix': task_matrix, 'token_estimates': token_ests,
        'cost_estimate': {
            'pass1_input': pass1_input,
            'pass2_input': '待 pass1 完成后根据实际产出量计算（pass2 的输入是 pass1 的输出）',
            'pass2_calculation_method': 'pass1 完成后统计 output/pass1/*/entities.jsonl 等文件的总条目数 × 平均字符数 × 0.75',
        },
        'max_tokens_per_chunk': MAX_TOKENS,
    }
    with open(CONFIG / 'task_chunks.json', 'w', encoding='utf-8') as f:
        json.dump(chunk_data, f, ensure_ascii=False, indent=2)
    print(f'\nOutput: config/task_chunks.json')

if __name__ == '__main__':
    main()
