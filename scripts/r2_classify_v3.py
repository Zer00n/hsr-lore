"""
R2 v3: speakerless 新分类规则
基于句式特征区分对话、旁白、占位、界面。
输出 work/speakerless_classified_v2.json，每类 50 条完整原文。
不迁移语料。
"""
import json, sys, io, os, re
from collections import defaultdict, Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(BASE, 'work')
CORPUS = os.path.join(BASE, 'corpus')

# ── 对白特征 ─────────────────────────────────────────────────────
SENTENCE_FINAL_PARTICLES = re.compile(r'[呢吗吧啊哦嘛呀嗯]$')
QUESTION_MARK = re.compile(r'[？?！!]$')
FIRST_PERSON = re.compile(r'(我[^们]|我们|咱[^们]|咱们|俺)')
HONORIFIC_SUFFIX = re.compile(r'(师父|大人|先生|小姐|女士|君|殿下|阁下|博士|老师|前辈|学长|学姐|师兄|师姐|队长|医生|护士|老板|老板娘)')

def has_dialogue_features(text):
    """Return True if text has clear dialogue markers."""
    # Sentence-final particles or question/exclamation marks
    if SENTENCE_FINAL_PARTICLES.search(text):
        return True
    if QUESTION_MARK.search(text):
        return True
    # First-person pronouns (but not in narration context like "你觉得")
    # "我" at start or not preceded by "你"/"他"/"她"
    if re.search(r'^我|。我|，我|！我|？我|、我|：我', text):
        return True
    if re.search(r'(我们|咱们|俺)', text):
        return True
    # Direct address with honorific
    if HONORIFIC_SUFFIX.search(text):
        return True
    return False

# ── 旁白特征 ─────────────────────────────────────────────────────
COMPLETION_MARKER = re.compile(r'[了着过]')
# Action/narrative verbs in Chinese — simple substring check
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

def has_action_verb(text):
    return any(v in text for v in ACTION_VERBS)

def is_narration(text):
    """True if text looks like narration (description of action/scene)."""
    if has_dialogue_features(text):
        return False
    # Must have completion/progressive markers AND action verbs
    has_completion = bool(COMPLETION_MARKER.search(text))
    has_action = has_action_verb(text)
    if has_completion and has_action:
        return True
    # Also: starts with "你" + longer descriptive text (not a question/command)
    if re.match(r'^你[^？！。，]{8,}', text) and not QUESTION_MARK.search(text):
        if '了' in text or '着' in text:
            return True
    return False

# ── 占位符 ───────────────────────────────────────────────────────
def is_placeholder(text):
    if len(text) <= 4:
        return True
    if re.match(r'^[.…\s]+$', text):
        return True
    if re.match(r'^（[^）]*）$', text) and len(text) <= 10:
        return True
    return False

# ── UI/系统 ─────────────────────────────────────────────────────
UI_START = re.compile(
    r'^(请选择|点击|按下|返回|确认|取消|跳过|前往|返回|探索|调查|'
    r'对话|进入|退出|使用|装备|丢弃|购买|出售|打开|关闭|'
    r'前进|后退|上一步|下一步|挑战|战斗|逃跑|防御|攻击|'
    r'离开|离开这里)'
)
def is_ui(text):
    return bool(UI_START.match(text))

# ── 主分类 ───────────────────────────────────────────────────────
def classify(text):
    text = text.strip()
    if is_placeholder(text):
        return 'placeholder'
    if is_ui(text):
        return 'ui_system'
    # Check dialogue features first (takes priority over narration)
    if has_dialogue_features(text):
        return 'dialogue'
    if is_narration(text):
        return 'narration'
    return 'unclassified'

def main():
    entries = []
    with open(os.path.join(CORPUS, 'speakerless.jsonl'), 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))

    print(f"Total: {len(entries)}")

    classified = defaultdict(list)
    for e in entries:
        cat = classify(e.get('clean', ''))
        classified[cat].append(e)

    stats = {cat: len(items) for cat, items in sorted(classified.items())}
    total = sum(stats.values())

    print(f"\nClassification:")
    for cat in ['placeholder', 'ui_system', 'dialogue', 'narration', 'unclassified']:
        count = stats.get(cat, 0)
        print(f"  {cat:15s}: {count:6d} ({count/total*100:5.1f}%)")

    # 50 full samples per category
    samples = {}
    for cat in ['placeholder', 'ui_system', 'dialogue', 'narration', 'unclassified']:
        items = classified.get(cat, [])
        samples[cat] = []
        for e in items[:50]:
            samples[cat].append({
                'cite_id': e['cite_id'],
                'source_pk': e['source_pk'],
                'clean_text': e.get('clean', ''),
            })

    # Prefix overlay analysis for narration
    narration_pks = [str(e['source_pk']) for e in classified.get('narration', [])]
    narration_prefixes = Counter()
    for pk in narration_pks:
        narration_prefixes[pk[:4]] += 1

    print(f"\nTop narration-heavy prefixes (4-digit):")
    for prefix, count in narration_prefixes.most_common(15):
        pct = count / len(narration_pks) * 100
        print(f"  {prefix}: {count} ({pct:.1f}%)")

    # Save
    report = {
        'total_entries': total,
        'classification_stats': stats,
        'samples': samples,
        'narration_prefix_top15': [{'prefix': p, 'count': c} for p, c in narration_prefixes.most_common(15)],
        'rules': {
            'placeholder': 'len <= 4 OR all ellipsis OR short parenthetical',
            'ui_system': 'starts with imperative command',
            'dialogue': 'sentence-final particle (呢吗吧啊哦嘛呀嗯) OR ?! ending OR first-person (我/我们/咱) OR honorific address',
            'narration': 'NO dialogue features AND has aspect markers (了/着/过) AND action verb',
            'unclassified': 'none of above',
        },
    }

    outpath = os.path.join(WORK, 'speakerless_classified_v2.json')
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\nOutput: {outpath}")

    # Print 50 samples per category
    for cat in ['placeholder', 'ui_system', 'dialogue', 'narration', 'unclassified']:
        print(f"\n{'='*60}")
        print(f"FULL SAMPLES: {cat} ({stats.get(cat,0)} total, showing 50)")
        print(f"{'='*60}")
        for s in samples[cat]:
            print(f"[{s['cite_id']}] {s['clean_text']}")

if __name__ == '__main__':
    main()
