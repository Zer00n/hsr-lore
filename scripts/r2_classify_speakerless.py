"""
R2: speakerless 重新分类 v2
按内容规则分类全部 65,450 条 speakerless 条目。
输出 work/speakerless_classified.json + 各类统计与样例。

v2 修正：
- 完整加载角色名（从 AvatarConfig title + StoryAtlas/VoiceAtlas meta）
- placeholder 移除括号包裹模式（括号是叙述文体，不是占位）
- ui_system 收紧为祈使句开头，避免误伤第三人物描写
- 增加更多第三人称叙述检测句式
"""
import json, sys, io, os, re
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(BASE, 'work')
CORPUS = os.path.join(BASE, 'corpus')

# ── Load character names ──────────────────────────────────────────

def load_char_names():
    """Extract all character names from characters.jsonl.
    Uses: AvatarConfig.title, StoryAtlas.meta.avatar_name, VoiceAtlas.meta.avatar_name
    Also adds known NPC names from the game world.
    """
    names = set()
    path = os.path.join(CORPUS, 'characters.jsonl')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip(): continue
                e = json.loads(line)
                # From title field (AvatarConfig has clean name in title)
                title = e.get('title', '')
                if title and title not in ('{NICKNAME}', '') and len(title) >= 1:
                    # Filter out non-name titles (descriptions)
                    if not title.startswith('{') and not title.startswith('Voice'):
                        names.add(title)
                # From meta.avatar_name
                aname = e.get('meta', {}).get('avatar_name', '')
                if aname and aname not in ('{NICKNAME}', '') and len(aname) >= 1:
                    names.add(aname)

    # Remove non-name entries
    non_names = {'{NICKNAME}', '', 'NICKNAME'}
    names -= non_names

    # Add known game NPCs and factions
    extras = {
        '史瓦罗', '克拉拉', '可可利亚', '布洛妮娅', '希儿', '虎克',
        '杰帕德', '希露瓦', '佩拉', '桑博', '卢卡', '玲可',
        '娜塔莎', '米伊尔', '加拉赫', '浮烟', '藿藿', '斯科特',
        '黑塔', '艾丝妲', '阿兰', '螺丝咕姆', '阮梅',
        '素裳', '桂乃芬', '梦茗', '三月七', '符玄', '景元',
        '银狼', '椒丘', '寒鸦', '雪衣', '彦卿', '白露',
        '卡芙卡', '刃', '银枝', '罗刹', '镜流',
        '砂金', '真理医生', '托帕', '翡翠',
        '知更鸟', '星期日', '花火', '黑天鹅', '黄泉', '波提欧', '米沙',
        '流萤', '白厄', '遐蝶', '万敌', '缇宝', '阿格莱雅',
        '刻律德菈', '那刻夏', '风堇', '赛飞儿', '海瑟音', '昔涟',
        '大黑塔', '忘归人', '乱破', '云璃', '貊泽',
        '钟表小子', '左轮队长', '镜子公主',
    }
    names.update(extras)
    return names

CHAR_NAMES = load_char_names()
print(f"Loaded {len(CHAR_NAMES)} character names")

# ── Classification rules ────────────────────────────────────────

# 1. Placeholder: very short, or explicit placeholder text
def is_placeholder(text):
    if len(text) < 4:
        return True
    if re.match(r'^[.…\s]+$', text):
        return True
    if re.match(r'^（[^）]*）$', text) and len(text) <= 10:
        return True
    return False

# 2. UI/System: imperative mood at start of text, OR explicit UI keywords at start
UI_IMPERATIVE_START = re.compile(
    r'^(请选择|点击|按下|返回|确认|取消|跳过|离开这里|离开此处|'
    r'前往|返回|探索|调查|对话|进入|退出|'
    r'使用|装备|丢弃|购买|出售|打开|关闭|'
    r'前进|后退|上一步|下一步|'
    r'挑战|战斗|逃跑|防御|攻击)'
)
def is_ui_system(text):
    return bool(UI_IMPERATIVE_START.match(text))

# 3. Narration — second person
SECOND_PERSON = re.compile(r'^[（(]?(你|你们|您|诸位)')

# 4. Narration — third person: descriptive prose
def is_third_person_narration(text):
    # Character name + action context
    for name in CHAR_NAMES:
        if name in text and len(name) >= 2:
            # Check for descriptive prose features
            has_punct = '。' in text or '，' in text
            has_verb = any(v in text for v in ['了', '着', '道', '说', '看', '去', '来', '走', '站', '坐', '笑', '叹', '点', '摇', '挥', '伸', '拿', '放', '递', '推', '拉'])
            if has_punct and has_verb:
                return True

    # Descriptive markers (start of sentence)
    narration_start = re.compile(
        r'^(此时|这时|忽然|突然|不一会儿|片刻之后|不久之后|'
        r'在|从|到|沿着|顺着|'
        r'一阵|一股|一道|一抹|'
        r'眼前|耳边|周围|远处|前方|身后|脚下|头顶|'
        r'让时间|时间回到|画面一转|镜头一转|'
        r'那是|这是|那是|只见|但见)'
    )
    if narration_start.match(text):
        return True

    # Contains narrative markers
    narrative_phrases = ['就这样', '与此同时', '另一边', '镜头', '画面']
    if any(text.startswith(p) for p in narrative_phrases):
        return True

    return False


def classify(text):
    """Classify a single text."""
    text = text.strip()

    if is_placeholder(text):
        return 'placeholder'

    if is_ui_system(text):
        return 'ui_system'

    if SECOND_PERSON.match(text):
        return 'narration'

    if is_third_person_narration(text):
        return 'narration'

    return 'unclassified'


def main():
    entries = []
    with open(os.path.join(CORPUS, 'speakerless.jsonl'), 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))

    print(f"Total speakerless entries: {len(entries)}")

    classified = defaultdict(list)
    for e in entries:
        cat = classify(e.get('clean', ''))
        classified[cat].append(e)

    stats = {cat: len(items) for cat, items in sorted(classified.items())}
    total = sum(stats.values())

    print(f"\nClassification results ({total} total):")
    for cat in ['placeholder', 'narration', 'ui_system', 'unclassified']:
        count = stats.get(cat, 0)
        pct = count / total * 100 if total > 0 else 0
        print(f"  {cat:15s}: {count:6d} ({pct:5.1f}%)")

    samples = {}
    for cat in ['placeholder', 'narration', 'ui_system', 'unclassified']:
        items = classified.get(cat, [])
        samples[cat] = []
        for e in items[:30]:
            samples[cat].append({
                'cite_id': e['cite_id'],
                'title': e.get('title', ''),
                'clean_text': e.get('clean', ''),
            })

    report = {
        'total_entries': total,
        'classification_stats': stats,
        'samples': samples,
        'character_names_count': len(CHAR_NAMES),
        'rules': {
            'placeholder': 'len < 4 OR all ellipsis OR short parenthetical (<=10 chars)',
            'narration_second_person': 'starts with 你/你们/您/诸位 (optional leading paren)',
            'narration_third_person': 'character_name + punctuation + action_verb, OR narrative_marker_at_start',
            'ui_system': 'starts with imperative command (请选择/点击/返回/etc.)',
            'unclassified': 'none of the above',
        },
    }

    outpath = os.path.join(WORK, 'speakerless_classified.json')
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\nOutput: {outpath}")
    print(f"\n{'='*60}")
    print("SAMPLES (10 per category)")
    print(f"{'='*60}")
    for cat in ['placeholder', 'narration', 'ui_system', 'unclassified']:
        print(f"\n--- {cat} ({stats.get(cat, 0)} total) ---")
        for s in samples[cat][:10]:
            print(f"  [{s['cite_id']}] {s['clean_text'][:120]}")

if __name__ == '__main__':
    main()
