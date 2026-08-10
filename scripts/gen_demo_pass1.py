"""
重新生成 demo_pass1（多卷分布）+ demo_pass2（归并与跨卷矛盾）
跨卷实体、跨卷矛盾、pass2 merges 全部手写，标注为示例数据。
"""
import json, os, shutil
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / 'tests' / 'fixtures'
CITE_INDEX_PATH = Path(__file__).parent.parent / 'work' / 'cite_index.jsonl'

cite_index = {}
with open(CITE_INDEX_PATH, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            r = json.loads(line)
            cite_index[r['cite_id']] = r

def q(cid, max_len=80):
    rec = cite_index.get(cid)
    if not rec: return {'cite_id': cid, 'quote': ''}
    return {'cite_id': cid, 'quote': rec['clean'][:max_len]}

# ── Entities by volume ────────────────────────────────────────────

LORE_ENTITIES = [
    # AEONs (7)
    ('AEON:纳努克', 'AEON', '纳努克', '毁灭星神，反物质军团的统帅。诞生于熵的深渊，以终结文明为信条。',
     [('命途','毁灭'),('称号','毁灭星神'),('关联','反物质军团')], ['AEON-1-1','AEON-5-1']),
    ('AEON:克里珀', 'AEON', '克里珀', '存护星神，被称为琥珀王的古老存在。以筑墙守护文明，琥珀纪的划分即以其诞生为原点。',
     [('命途','存护'),('称号','琥珀王'),('已知','最古老星神之一')], ['AEON-1-1','LOAD-10076']),
    ('AEON:阿哈', 'AEON', '阿哈', '欢愉星神，行为难以预测。曾伪装成无名客登上星穹列车，在抵达终点时将列车炸毁。',
     [('命途','欢愉'),('称号','常乐天君')], ['AEON-7-1','LOAD-10162']),
    ('AEON:药师', 'AEON', '药师', '丰饶星神，被称为长生主。其恩赐使仙舟先民获得长生，却导致魔阴身的蔓延。',
     [('命途','丰饶'),('称号','长生主'),('关联','仙舟联盟')], ['LOAD-10162']),
    ('AEON:岚', 'AEON', '岚', '巡猎星神，帝弓司命，仙舟联盟所追随的星神。以光矢净化丰饶孽物为使命。',
     [('命途','巡猎'),('称号','帝弓司命'),('对手','药师')], ['AEON-5-1']),
    ('AEON:IX', 'AEON', 'IX', '虚无星神，一个无限扩张的黑洞形态。不对外界作任何回应。',
     [('命途','虚无'),('形态','黑洞')], ['AEON-1-1']),
    ('AEON:希佩', 'AEON', '希佩', '同谐星神，由众多生命意志融合而成。匹诺康尼家族即受其庇护。',
     [('命途','同谐'),('关联','匹诺康尼')], ['AEON-1-1','LOAD-10076']),
    # PATHs (5)
    ('PATH:毁灭', 'PATH', '毁灭', '纳努克所行的命途。追随者视文明为熵增的必然归宿。',
     [('星神','纳努克'),('派系','反物质军团')], ['AEON-1-1']),
    ('PATH:存护', 'PATH', '存护', '克里珀所行的命途，以筑墙守护为信条。星际和平公司即在此命途下运作。',
     [('星神','克里珀'),('派系','星际和平公司'),('派系','筑城者')], ['AEON-1-1','LOAD-10076']),
    ('PATH:欢愉', 'PATH', '欢愉', '阿哈所行的命途，以笑谑和戏弄为教义。假面愚人是此命途最著名的践行者。',
     [('星神','阿哈'),('派系','假面愚人')], ['AEON-7-1']),
    ('PATH:巡猎', 'PATH', '巡猎', '岚所行的命途，以光速和正义为信条。仙舟联盟与巡海游侠均在此命途下行进。',
     [('星神','岚'),('派系','仙舟联盟'),('派系','巡海游侠')], ['AEON-5-1']),
    ('PATH:丰饶', 'PATH', '丰饶', '药师所行的命途，追求永恒的生命。然而无节制的"祝福"往往带来灾难性的后果。',
     [('星神','药师'),('关联','丰饶之民'),('关联','魔阴身')], ['AEON-1-1','LOAD-10162']),
    # Concepts (3)
    ('CONC:星核', 'CONC', '星核', '灾厄的种子，世界的癌。能扭曲空间、催生裂界——其本质可能是某位星神的"恩赐"或"诅咒"。',
     [('本质','不明·推测星神之力'),('效果','裂界·寒潮·空间扭曲')], ['AEON-1-1','LOAD-10076','LOAD-10162']),
    ('CONC:裂界', 'CONC', '裂界', '自星核落点向外蔓延的异常空间。被裂界吞噬的区域会产生碎片化记忆的裂界造物。',
     [('来源','星核'),('产物','裂界造物')], ['LOAD-10076','LOAD-10162']),
    ('CONC:魔阴身', 'CONC', '魔阴身', '仙舟长生种到达一定年龄后必然遭遇的精神与肉体异变。药师赐予永生的代价。',
     [('原因','丰饶长生之力的代价'),('影响','仙舟长生种')], ['AEON-1-1','LOAD-10162']),
    # ORGNs in lore context
    ('ORGN:反物质军团', 'ORGN', '反物质军团', '追随纳努克的军事力量，由绝灭大君统领。以虚空和反物质为武器。',
     [('星神','纳努克'),('统领','绝灭大君')], ['AEON-5-1']),
    ('ORGN:星际和平公司', 'ORGN', '星际和平公司', '存护命途下的跨星系商业组织，以契约、贸易与筑城为手段推进文明。',
     [('命途','存护'),('特点','跨星系商业')], ['AEON-1-1','LOAD-10076']),
]

CHAR_ENTITIES = [
    ('CHAR:开拓者', 'CHAR', '开拓者', '星穹列车的无名客。体内被植入星核却无所畏惧，以开拓的姿态探索未知银河。',
     [('身份','星穹列车成员'),('特质','星核载体')], ['LOAD-10162']),
    ('CHAR:三月七', 'CHAR', '三月七', '星穹列车的少女，从漂流于太空的六相冰中被救出。性格活泼开朗，对过去全然失忆。',
     [('身份','星穹列车成员'),('特质','失忆')], ['LOAD-10162']),
    ('CHAR:丹恒', 'CHAR', '丹恒', '星穹列车护卫，冷静寡言。真实身份为持明龙尊，因故被放逐后加入列车。',
     [('身份','星穹列车护卫'),('种族','持明族'),('前世','丹枫·饮月君')], ['LOAD-10162']),
    ('CHAR:姬子', 'CHAR', '姬子', '星穹列车的领航员，天文学家出身。以优雅从容的姿态引导开拓者驶向未知星域。',
     [('身份','列车领航员'),('特长','天文导航')], ['LOAD-10162']),
    ('CHAR:瓦尔特', 'CHAR', '瓦尔特', '星穹列车成员，来自另一个世界的智者。善于分析局势，是列车上最可靠的旅者。',
     [('身份','星穹列车成员'),('特点','异世界来客')], ['LOAD-10162']),
    ('CHAR:卡芙卡', 'CHAR', '卡芙卡', '星核猎手的核心成员，优雅而危险。以言灵操控他人意识，自称命运的安排者。',
     [('身份','星核猎手成员'),('能力','言灵'),('关联','命运奴隶')], ['AEON-1-1']),
    ('CHAR:银狼', 'CHAR', '银狼', '星核猎手成员，天才黑客少女。擅长以太编辑，将现实当作代码随意修改。',
     [('身份','星核猎手成员'),('能力','以太编辑'),('关联','朋克洛德')], ['AEON-1-1']),
    ('CHAR:刃', 'CHAR', '刃', '星核猎手成员，由于诅咒无法死去。云骑军出身，曾是仙舟著名的工匠，后堕入黑暗。',
     [('身份','星核猎手成员'),('特质','不死'),('过往','云骑军工匠')], ['AEON-1-1']),
    ('CHAR:流萤', 'CHAR', '流萤', '星核猎手成员，沉默寡言但行动果决。体内寄宿大量纳米机械，以肉身换取战力。',
     [('身份','星核猎手成员'),('特质','纳米改造体')], ['AEON-1-1']),
    ('ORGN:星穹列车', 'ORGN', '星穹列车', '由阿基维利创造、穿梭银河的星间列车。无名客世代在此旅行，以开拓精神连接诸界。',
     [('创始人','阿基维利'),('使命','开拓'),('成员','无名客')], ['LOAD-10162']),
    ('ORGN:星核猎手', 'ORGN', '星核猎手', '以命运奴隶艾利欧的剧本为行动指南的神秘组织。成员各怀绝技，以收集星核为表面目标。',
     [('领袖','艾利欧'),('目标','收集星核'),('特点','各有所图')], ['AEON-1-1','LOAD-10162']),
]

NARR_ENTITIES = [
    # Places & worlds
    ('WRLD:雅利洛-VI', 'WRLD', '雅利洛-Ⅵ', '一颗被永冬覆盖的星球。贝洛伯格是地表仅存的人类聚居地，在星核影响下与裂界和寒潮抗争。',
     [('首都','贝洛伯格'),('威胁','星核·裂界·寒潮'),('守护者','筑城者')], ['LOAD-10076']),
    ('WRLD:仙舟罗浮', 'WRLD', '仙舟罗浮', '仙舟联盟的旗舰之一，为追寻丰饶之神而启航的星船。建木曾在此失控生长。',
     [('隶属','仙舟联盟'),('将军','景元'),('威胁','建木·魔阴身')], ['AEON-5-1','LOAD-10162']),
    ('WRLD:匹诺康尼', 'WRLD', '匹诺康尼', '曾经的星际监狱，现为同谐命途下家族所守护的和平世界。梦境与现实在此交织。',
     [('守护者','家族'),('命途','同谐'),('特点','梦境与现实交融')], ['AEON-1-1','LOAD-10076']),
    ('WRLD:翁法罗斯', 'WRLD', '翁法罗斯', '被遗忘的星球，地表遍布远古机械遗骸。推测与已陨落的繁育星神塔伊兹育罗斯有关。',
     [('特点','远古机械遗骸'),('关联','繁育星神')], ['AEON-5-1']),
    ('PLAC:贝洛伯格', 'PLAC', '贝洛伯格', '雅利洛-Ⅵ上人类最后的堡垒。以厚重城墙抵御裂界侵蚀与极寒，上层区与下层区分化严重。',
     [('位置','雅利洛-Ⅵ'),('分区','上层区·下层区'),('守护者','大守护者')], ['LOAD-10076']),
    # ORGN in narrative context
    ('ORGN:黑塔空间站', 'ORGN', '黑塔空间站', '天才俱乐部#83号黑塔女士的私人研究设施。位于近地轨道，是开拓者旅程的起点。',
     [('所有者','黑塔'),('位置','近地轨道')], ['LOAD-10162']),
    # Cross-volume CHAR duplicate (same name, different summary in narrative context)
    ('CHAR:三月七', 'CHAR', '三月七', '在贝洛伯格的行动中，三月七展现出了远超其开朗外表下的冷静判断力，帮助团队化解了数次危机。',
     [('身份','星穹列车成员'),('表现','贝洛伯格行动中的关键作用')], ['LOAD-10076']),
    # Cross-volume entity: 星穹列车 in narrative
    ('ORGN:星穹列车', 'ORGN', '星穹列车', '星穹列车驶入雅利洛-Ⅵ的轨道时，暴风雪笼罩了整个星球表面。无名客们已经习惯了这样的景象——每到一个新世界，都是一场未知。',
     [('当前状态','驶向雅利洛-Ⅵ'),('任务','调查星核')], ['LOAD-10162','LOAD-10076']),
]

BOOKS_ENTITIES = [
    # Extra narrative entities from "book" style texts
    ('CHAR:景元', 'CHAR', '景元', '仙舟罗浮的云骑将军，外表慵懒实则智计过人。以不对称战略思维守护罗浮千年的和平。',
     [('身份','云骑将军'),('所属','仙舟罗浮'),('特点','智将')], ['AEON-5-1']),
    ('AEON:塔伊兹育罗斯', 'AEON', '塔伊兹育罗斯', '已陨落的繁育星神，虫皇。其陨落导致了宇宙生态的巨大变迁。关于其陨落的记载在古籍中只有寥寥数语。',
     [('命途','繁育'),('状态','已陨落'),('称号','虫皇')], ['AEON-5-1']),
    ('CONC:琥珀纪', 'CONC', '琥珀纪', '以存护星神克里珀的诞生为纪元起点的宇宙历法。每一条琥珀纪的推进都意味着克里珀又完成了一锤筑墙。',
     [('起点','克里珀诞生'),('意义','存护之墙的进度')], ['AEON-1-1','LOAD-10076']),
]

# ── Relations by volume ──────────────────────────────────────────

LORE_RELATIONS = [
    ('AEON:纳努克', 'EMBODIES', 'PATH:毁灭', 'AEON-1-1'),
    ('AEON:克里珀', 'EMBODIES', 'PATH:存护', 'AEON-1-1'),
    ('AEON:阿哈', 'EMBODIES', 'PATH:欢愉', 'AEON-7-1'),
    ('AEON:岚', 'EMBODIES', 'PATH:巡猎', 'AEON-5-1'),
    ('AEON:药师', 'EMBODIES', 'PATH:丰饶', 'LOAD-10162'),
    ('AEON:纳努克', 'OPPOSES', 'AEON:克里珀', 'AEON-1-1'),
    ('AEON:岚', 'OPPOSES', 'AEON:药师', 'AEON-5-1'),
    ('AEON:纳努克', 'RELATED_TO', 'ORGN:反物质军团', 'AEON-5-1'),
]

CHAR_RELATIONS = [
    ('CHAR:开拓者', 'MEMBER_OF', 'ORGN:星穹列车', 'LOAD-10162'),
    ('CHAR:三月七', 'MEMBER_OF', 'ORGN:星穹列车', 'LOAD-10162'),
    ('CHAR:丹恒', 'MEMBER_OF', 'ORGN:星穹列车', 'LOAD-10162'),
    ('CHAR:姬子', 'MEMBER_OF', 'ORGN:星穹列车', 'LOAD-10162'),
    ('CHAR:瓦尔特', 'MEMBER_OF', 'ORGN:星穹列车', 'LOAD-10162'),
    ('CHAR:卡芙卡', 'MEMBER_OF', 'ORGN:星核猎手', 'AEON-1-1'),
    ('CHAR:银狼', 'MEMBER_OF', 'ORGN:星核猎手', 'AEON-1-1'),
    ('CHAR:刃', 'MEMBER_OF', 'ORGN:星核猎手', 'AEON-1-1'),
    ('CHAR:流萤', 'MEMBER_OF', 'ORGN:星核猎手', 'AEON-1-1'),
    ('CHAR:卡芙卡', 'ALLY_OF', 'CHAR:银狼', 'AEON-1-1'),
]

NARR_RELATIONS = [
    ('ORGN:星穹列车', 'LOCATED_IN', 'PLAC:贝洛伯格', 'LOAD-10076'),
    ('AEON:岚', 'RELATED_TO', 'WRLD:仙舟罗浮', 'AEON-5-1'),
]

BOOKS_RELATIONS = [
    ('CHAR:景元', 'RELATED_TO', 'WRLD:仙舟罗浮', 'AEON-5-1'),
]

# ── Events by volume ─────────────────────────────────────────────

LORE_EVENTS = [
    ('阿哈伪装无名客炸毁列车', '欢愉星神阿哈曾伪装成无名客，一路旅行至终点后将星穹列车炸毁，以此向开拓星神阿基维利"问好"。',
     ['阿哈','阿基维利'], ['星穹列车'], '未知（叙事层传说）', 0, ['AEON-7-1','LOAD-10162']),
    ('开拓星神阿基维利的陨落', '开拓星神阿基维利曾行走于银河之间铺设星轨。某一天阿基维利突然消失了，无名客们继承列车延续开拓使命。',
     ['阿基维利'], ['银河'], '远古', -1, ['AEON-1-1','LOAD-10162']),
]

CHAR_EVENTS = [
    ('反物质军团入侵黑塔空间站', '毁灭军团突然袭击空间站，守卫力量猝不及防。开拓者在此与军团初交锋，并在黑塔指引下击退敌军。',
     ['开拓者','三月七','丹恒','反物质军团'], ['黑塔空间站'], '琥珀纪 2157 年', 2, ['AEON-5-1']),
]

NARR_EVENTS = [
    ('星穹列车的启程', '开拓者在黑塔空间站被卡芙卡植入星核，随后与三月七、丹恒一起登上星穹列车，开启了银河之旅。',
     ['开拓者','三月七','丹恒','姬子','卡芙卡'], ['黑塔空间站','星穹列车'], '琥珀纪 2157 年', 1, ['LOAD-10162']),
    ('贝洛伯格星核危机', '列车降落在被永冬笼罩的雅利洛-Ⅵ。贝洛伯格面临寒潮与裂界双重威胁，大守护者可可利亚以星核之力维系城墙——却不知星核正是灾难源头。',
     ['开拓者','三月七','丹恒','可可利亚','布洛妮娅'], ['雅利洛-Ⅵ','贝洛伯格'], '琥珀纪 2157 年', 3, ['LOAD-10076']),
    ('建木失控与药王秘传的阴谋', '仙舟罗浮的建木突然失控生长，药王秘传在暗处推动。开拓者与云骑将军景元联手揭露背后真相。',
     ['开拓者','丹恒','景元','药王秘传'], ['仙舟罗浮'], '琥珀纪 2157 年', 4, ['AEON-5-1','LOAD-10162']),
    ('仙舟罗浮围剿药王秘传', '景元指挥云骑军对药王秘传巢穴发动围剿。开拓者深入丹鼎司与秘传首领对决，最终斩断建木失控生长。',
     ['开拓者','景元','云骑军','药王秘传'], ['仙舟罗浮','丹鼎司'], '琥珀纪 2157 年', 5, ['AEON-5-1']),
    ('星际和平公司的筑城行动', '星际和平公司在存护命途下发起筑城行动，以贸易与契约为"城墙"在银河中建立秩序。',
     ['星际和平公司'], ['银河各星域'], '持续', 10, ['AEON-1-1','LOAD-10076']),
]

BOOKS_EVENTS = [
    ('塔伊兹育罗斯的陨落记录', '古籍《诸界虫灾纪》以隐晦笔触提及繁育星神的陨落：群虫在某一刻突然失去了方向，整个虫巢开始自我吞噬——这意味着虫皇已从宇宙中消失。然而，谁杀了塔伊兹育罗斯，至今没有任何文献给出答案。',
     ['塔伊兹育罗斯'], ['银河·虫巢遗迹'], '远古', -2, ['AEON-5-1']),
]

# ── Discrepancies by volume ─────────────────────────────────────

LORE_DISC = [
    ('contradiction', '克里珀的登神时间',
     '公司宣称黄昏战争因琥珀王的诞生而终结。',
     '考古发现显示，在0至180琥珀纪期间古兽依然活跃于银河各处。',
     '公司的官宣与考古证据之间存在至少180个琥珀纪的时间差。',
     ['克里珀','黄昏战争','星际和平公司'], 'high', 'AEON-1-1', 'LOAD-10076'),
    ('ambiguity', '纳努克的动机',
     '军团宣传品称纳努克的毁灭是对宇宙熵增的"慈悲终结"。',
     '另一来源暗示纳努克之所以毁灭是因为其生前文明遭到彻底毁灭——这是一种复仇。',
     '两种叙事对理解纳努克的本性有截然不同的暗示。',
     ['纳努克','反物质军团'], 'high', 'AEON-5-1', 'AEON-1-1'),
]

CHAR_DISC = [
    ('gap', '阿基维利的消失',
     '阿基维利的消失是银河最大的未解之谜之一。无名客继承了列车，但没有任何人知道阿基维利去了哪里。',
     None,
     '游戏中多处提及阿基维利消失或陨落，但从没有任何文本正面解释发生了什么。这是有意为之的叙事留白。',
     ['阿基维利','星穹列车','无名客'], 'high', 'AEON-1-1', None),
]

NARR_DISC = [
    ('gap', '星核的本质',
     '星核猎手以收集星核为目标行动，开拓者体内被植入了星核——但星核到底是什么？其来源是统一的吗？与星神有什么关联？',
     None,
     '星核是贯穿全作的核心谜题。游戏文本提供了大量线索——与裂界的因果关系、被植入人体的可能性——但根本层面上，星核的本质尚未揭晓。',
     ['星核','星核猎手','开拓者'], 'high', 'AEON-1-1', None),
]

# ═══ CROSS-VOLUME DISCREPANCY (books vs narrative) ═══
# This will be placed in books volume with _cross_volume = True by pass2 builder
# But for demo, we just add it in books as a normal discrepancy for now
# The pass2 builder will handle the rest
BOOKS_DISC = [
    ('contradiction', '塔伊兹育罗斯的陨落原因',
     '《诸界虫灾纪》记载虫皇的陨落是"群虫突然失去方向，整个虫巢开始自我吞噬"（暗示内部崩溃或自然陨落）。',
     '而在仙舟罗浮的行动记录中，巡猎星神岚的光矢被描述为曾经"洞穿虫皇的甲胄"（暗示外部干预是陨落原因）。',
     '古籍与军事记录之间的矛盾为繁育星神的陨落提供了两种互不相容的叙事。究竟是何方力量终结了塔伊兹育罗斯，至今是银河史学界争议最大的问题之一。',
     ['塔伊兹育罗斯','岚','虫巢'], 'high', 'AEON-5-1', 'AEON-5-1'),
]

# ═══ Cross-volume entity mapping (for pass2 merges) ═══
# These are the cross-volume entities that appear in multiple volumes with the same entity_id
CROSS_VOLUME_ENTITIES = {
    'CHAR:三月七': {'volumes': ['characters', 'narrative'], 'canonical_name': '三月七'},
    'ORGN:星穹列车': {'volumes': ['characters', 'narrative'], 'canonical_name': '星穹列车'},
}

# ── Write functions ──────────────────────────────────────────────

def make_entity(eid, etype, name, summary, attrs, cites, vol):
    return {
        'entity_id': eid, 'type': etype, 'canonical_name': name, 'aliases': [],
        'summary': {'text': summary, 'claim_type': 'fact', 'confidence': 'attested',
                     'citations': [q(c) for c in cites]},
        'attributes': [{'key': k, 'value': v, 'claim_type': 'fact', 'confidence': 'attested',
                         'citations': [q(cites[0])]} for k, v in attrs],
        'source_volume': vol,
    }

def make_relation(subj, pred, obj, cid, vol):
    return {
        'relation_id': f'REL:demo-{vol}-{subj}-{pred}-{obj}'.replace(':','-'),
        'subject_name': subj, 'predicate': pred, 'object_name': obj, 'qualifiers': {},
        'claim_type': 'fact', 'confidence': 'attested',
        'citations': [q(cid)], 'source_volume': vol,
    }

def make_event(name, summary, participants, locations, stated_time, order, cites, vol):
    return {
        'event_id': f'EVT:demo-{vol}-{name}',
        'name': name, 'summary': {'text': summary, 'claim_type': 'fact', 'confidence': 'attested',
                                    'citations': [q(c) for c in cites]},
        'participants': participants, 'locations': locations, 'stated_time': stated_time,
        'relative_to': [], 'order_hint': order, 'confidence': 'attested',
        'citations': [q(cites[0])], 'source_volume': vol,
    }

def make_discrepancy(kind, topic, stmt_a, stmt_b, analysis, entities, impact, cid_a, cid_b, vol):
    stmts = [{'text': stmt_a, 'citation': q(cid_a)}]
    if stmt_b:
        stmts.append({'text': stmt_b, 'citation': q(cid_b)})
    return {
        'discrepancy_id': f'DSC:demo-{vol}-{topic}',
        'kind': kind, 'topic': topic, 'statements': stmts,
        'analysis': {'text': analysis, 'claim_type': 'interpretation', 'confidence': 'inferred',
                      'citations': [q(cid_a)]},
        'related_entities': entities, 'impact': impact,
    }

def write_jsonl(path, items):
    with open(path, 'w', encoding='utf-8') as f:
        for item in items: f.write(json.dumps(item, ensure_ascii=False) + '\n')

# ── Generate pass1 ───────────────────────────────────────────────

PASS1 = FIXTURES / 'demo_pass1'
if PASS1.exists(): shutil.rmtree(PASS1)

volumes = {
    'lore': (LORE_ENTITIES, LORE_RELATIONS, LORE_EVENTS, LORE_DISC),
    'characters': (CHAR_ENTITIES, CHAR_RELATIONS, CHAR_EVENTS, CHAR_DISC),
    'narrative': (NARR_ENTITIES, NARR_RELATIONS, NARR_EVENTS, NARR_DISC),
    'books': (BOOKS_ENTITIES, BOOKS_RELATIONS, BOOKS_EVENTS, BOOKS_DISC),
}

tots = {'entities':0,'relations':0,'events':0,'discrepancies':0}
for vol, (ents, rels, evts, discs) in volumes.items():
    vdir = PASS1 / vol
    vdir.mkdir(parents=True, exist_ok=True)

    e_out = [make_entity(*e, vol) for e in ents]
    r_out = [make_relation(*r, vol) for r in rels]
    ev_out = [make_event(*e, vol) for e in evts]
    d_out = [make_discrepancy(*d, vol) for d in discs]

    write_jsonl(vdir / 'entities.jsonl', e_out)
    write_jsonl(vdir / 'relations.jsonl', r_out)
    write_jsonl(vdir / 'events.jsonl', ev_out)
    write_jsonl(vdir / 'discrepancies.jsonl', d_out)

    print(f'{vol:>12s}: {len(e_out):>3d} entities, {len(r_out):>2d} relations, {len(ev_out):>2d} events, {len(d_out)} disc')
    for k,v in zip(tots.keys(), [len(e_out),len(r_out),len(ev_out),len(d_out)]):
        tots[k] += v

print(f'  TOTAL:    {tots["entities"]} entities, {tots["relations"]} relations, {tots["events"]} events, {tots["discrepancies"]} disc')

# ── Generate pass2 ───────────────────────────────────────────────

PASS2 = FIXTURES / 'demo_pass2'
if PASS2.exists(): shutil.rmtree(PASS2)
PASS2.mkdir(parents=True, exist_ok=True)

# Merges: merge cross-volume entities
merges = []
for eid, info in CROSS_VOLUME_ENTITIES.items():
    merges.append({
        'merge_id': f'MERGE:demo-{eid}',
        'merged_entity_id': eid,
        'source_entity_ids': [eid] * len(info['volumes']),  # same entity_id across volumes
        'method': 'exact_name',
        'rationale': {
            'text': f'实体「{info["canonical_name"]}」在 {", ".join(info["volumes"])} 卷中各出现一次，同名确认为同一实体。归并后以 characters 卷的完整描述为准。',
            'claim_type': 'fact', 'confidence': 'attested',
            'citations': [q('LOAD-10162')],
        },
        'confidence': 'attested',
    })

write_jsonl(PASS2 / 'merges.jsonl', merges)
print(f'\nPass2 merges: {len(merges)}')

# Cross-volume discrepancies
cross_disc = [{
    'discrepancy_id': 'DSC:demo-cross-塔伊兹育罗斯陨落',
    'kind': 'contradiction',
    'topic': '塔伊兹育罗斯的陨落原因（跨卷）',
    'statements': [
        {'text': '古籍《诸界虫灾纪》：虫皇陨落是"群虫突然失去方向，虫巢开始自我吞噬"（暗示内部崩溃）。', 'citation': q('AEON-5-1')},
        {'text': '仙舟行动记录：巡猎星神岚的光矢曾"洞穿虫皇甲胄"（暗示外部干预）。', 'citation': q('AEON-5-1')},
    ],
    'analysis': {
        'text': 'books 卷的古籍记载指向内部崩溃叙事，narrative 卷的军事记录指向外部干预叙事。两种叙事来自不同类型的文本源（学术文献 vs 军事记录），互不相容。这是跨卷矛盾的典型案例——同一条星神陨落的史实在不同文本体裁中的呈现方式截然不同。',
        'claim_type': 'interpretation', 'confidence': 'inferred',
        'citations': [q('AEON-5-1')],
    },
    'related_entities': ['塔伊兹育罗斯', '岚', '虫巢'],
    'impact': 'high',
}]
write_jsonl(PASS2 / 'discrepancies.jsonl', cross_disc)
print(f'Pass2 cross-volume discrepancies: {len(cross_disc)}')
print(f'\nOutput:\n  pass1: {PASS1}\n  pass2: {PASS2}')
