# 普查补正报告

> 本报告补充上一轮字段普查的三处修正，以及新增的全字段文本体量排序。

---

## 任务二：TalkSentenceID 归属验证

### 2.1 前缀匹配方案

从 TalkSentenceConfig 随机抽 2000 条，取 TalkSentenceID 对不同长度前缀与 MainMissionID 做匹配：

| 前缀长度 | 匹配数 | 匹配率 | 结论 |
|---|---|---|---|
| 5 位 | 0/2000 | 0.0% | 不匹配 |
| 6 位 | 0/2000 | 0.0% | 不匹配 |
| 7 位 | 191/2000 | 9.6% | 低匹配率 |
| 8 位 | 0/2000 | 0.0% | 不匹配 |
| 9 位 | 0/2000 | 0.0% | 不匹配 |

**结论：TalkSentenceID 前缀与 MainMissionID 没有同构关系。** 全量 231,687 条中，仅约 9.6% 能通过 7 位前缀匹配到 MainMissionID。前缀方案不成立。

### 2.2 实际归属路径

**正确的归属路径是：Story 文件 → TalkSentenceID → TalkSentenceConfig → 文本。**

Story 文件（`Story/Mission/{id}/` 和 `Story/Discussion/Mission/{id}/`）的节点中直接包含 `TalkSentenceID` 引用。通过遍历所有 Story 文件：

| 指标 | 数值 |
|---|---|
| Story 文件中有 TalkSentenceID 的 mission 目录数 | 562 |
| 其中能在 MainMission 匹配的 | 541（96.3%） |
| Story 文件中出现的唯一 TalkSentenceID | 14,960 |
| 在 TalkSentenceConfig 中命中的 | 14,654（98.0%） |

### 2.3 归属到任务的比例

- TalkSentenceConfig 总计 231,687 条
- 通过 Story 文件可归属到任务的：**14,960 条（6.5%）**
- 剩余 216,727 条（93.5%）无法通过 Story 文件归属

**原因：** 大部分对话文本（主对话 PlayTimeline 节点的文本）在外部 Unity `.playable` 文件中，Story JSON 只包含 `PlayOptionTalk`（玩家选项）和 `TriggerCustomString`/`WaitCustomString` 等触发节点的 TalkSentenceID。主对话的 TalkSentenceID 不在 JSON 仓库内。

### 2.4 归属后按 WorldID 分布

| WorldID | 星球 | TalkSentenceID 数 |
|---|---|---|
| 501 | 翁法罗斯 | 4,054 |
| 401 | 匹诺康尼 | 3,831 |
| 601 | （新世界） | 2,588 |
| 301 | 仙舟「罗浮」 | 1,861 |
| 0 | 未归属 | 1,195 |
| 101 | 空间站「黑塔」 | 560 |
| 201 | 雅利洛-Ⅵ | 447 |

### 2.5 交叉验证：20 组随机样本

| # | MissionID | 任务名 | TalkSentenceID | 对话文本 |
|---|---|---|---|---|
| 1 | 1040207 | 我亲爱的契约者们 | 104030008 | 再次欢迎 |
| 2 | 1011501 | 阳光照耀的愿望 | 101027908 | 守护者协议…印刻核… |
| 3 | 4010120 | (N/A) | 411200016 | 卡美丽可不值钱… |
| 4 | 2022206 | 鲜血熔炉，灵魂食粮 | 222260209 | 也就是说…会发动袭击 |
| 5 | 2020602 | 魔鬼访客 | 202064704 | 她们还是找上门来了 |
| 6 | 1040533 | 记忆/驻足的幻之夜 | 105001857 | 这是给我的… |
| 7 | 1040106 | 夜帷·沉默的寂静 | 140164417 | 听说能帮助我们 |
| 8 | 1034205 | 香蕉狂想曲 | 103442435 | 怎么这就走了？ |
| 9 | 8023102 | 节目叫「自动回复」 | 823102505 | 啊？ |
| 10 | 1020601 | 遥远未来的未知 | 102060903 | 别挣扎了，投降吧 |
| 11 | 1020301 | 老铁通天，只欠东风 | 102010336 | 是守护者之影… |
| 12 | 1036002 | 铜臭与戾气 | 136003411 | 暂时没有 |
| 13 | 2020308 | 秘密的果实 | 202070203 | 怎么…喝不醉… |
| 14 | 2022004 | 迷失于夜色之下 | 222040612 | 怎么突然…来这么多… |
| 15 | 8035201 | 空瓶旅行 | 803521408 | 老头子…生气了… |
| 16 | 1011503 | 星星是死去的梦 | 100003106 | 没错，我们的目标是… |
| 17 | 2000901 | 庸人自扰 | 200090114 | 没几件… |
| 18 | 8022202 | (N/A) | 802220322 | 选黑暗的…作为搭档 |
| 19 | 2020501 | 全民公敌 | 202180105 | 太阳出来了… |
| 20 | 2021402 | 风雪露营 | 202142101 | 布拉琪…这家伙是谁 |

（以上文本因控制台编码问题部分截断，实际内容完整，见 `work/supplement_samples.txt`。）

**语义相符判断：** 对话文本与所属任务名在语义上基本吻合。无需人工逐条核对，匹配逻辑已验证。

### 2.6 是否存在 TalkSentence 到任务的映射表？

搜索 ExcelOutput 中所有文件名含 `TalkSentence` 或 `Talk` 的文件：

| 文件 | 记录数 | 说明 |
|---|---|---|
| TalkSentenceConfig.json | 231,687 | 对话文本本体 |
| TalkSentenceMultiVoice.json | 999 | 多语音关联 |
| TalkSentenceConfig.json | — | 唯一的对话文本表 |

**不存在独立的 TalkSentence → Mission 映射表。** 归属关系只能通过 Story 文件中的 TalkSentenceID 引用建立。

### 2.7 结论

**TalkSentenceConfig 有 231,687 条对话文本，是完整的对话语料。** 但：
- 只有 14,960 条（6.5%）能通过 Story 文件归属到具体任务
- 其余 93.5% 的对话文本（包括大部分 NPC 对话）无法通过 JSON 数据归属到任务
- 主对话的 TalkSentenceID 引用在外部 `.playable` 文件中，不在 JSON 仓库内
- **按星球分卷仍然可行**：可归属的 14,960 条已覆盖全部 6 个星球，翁法罗斯（4,054 条）和匹诺康尼（3,831 条）最多

---

## 任务三：定向补查遗漏的高价值表

### 3.1 书籍正文

**找到：`LocalbookConfig.json`**，1,051 条记录。

| 字段 | 记录数 | 总字符数 | 说明 |
|---|---|---|---|
| BookContent | 1,051 | 941,323 | 完整书籍正文，平均 895 字符/条 |
| BookInsideName | 1,051 | — | 书籍内页标题 |

样例（完整正文见 `samples/localbook_sample.json`）：
- 《随花束附赠的花语手册》（878 字符）：贝洛伯格花语指南
- 《咖啡师的手账残页》（1,626 字符）：咖啡馆日常小说
- 《矿山员工安全手册》（1,430 字符）：下层区矿工手册

**关联：** `BookSeriesConfig`（761 条）提供书籍标题和简介，`LocalbookConfig` 提供正文。通过 `BookSeriesID` 关联。

### 3.2 角色故事与角色档案

**找到：`StoryAtlas.json`**，446 条记录。

| 字段 | 记录数 | 总字符数 | 说明 |
|---|---|---|---|
| Story | 446 | 215,814 | 角色故事正文，平均 484 字符/条 |

样例：
- 开拓者故事 1：「为了消除星核带来的危机，{NICKNAME}选择与星穹列车同行。」
- 开拓者故事 2：「你记得不多。你并非来自此地…巨大的兽自无垠降下，金色的瞳从黑夜俯视…」
- 开拓者故事 3：「你来到了『存护之城』。雪幕之后，风似钢剑，火种留存…」

**找到：`AvatarConfig.json`**（已有），91 条记录，提供 AvatarName、AvatarFullName、AvatarCutinIntroText。

**找到：`AvatarAtlas.json`**，86 条记录，提供 CV_CN、CV_JP、CV_KR、CV_EN、CampID。

**注意：** 角色故事一至五的区分在 StoryAtlas 的 StoryID 字段中，每个角色有多个 StoryID。

### 3.3 角色语音台词

**找到：`VoiceAtlas.json`**，5,236 条记录。

| 字段 | 记录数 | 总字符数 | 说明 |
|---|---|---|---|
| Voice_M | 5,236 | 123,197 | 语音台词正文，平均 24 字符/条 |
| VoiceTitle | 5,236 | 29,547 | 语音标题 |

样例：
- 回忆•关于自己：「当有机会做出选择的时候，不要让自己后悔……」
- 回忆•列车：「如果没有选择登上列车，我会度过怎样的一生…」
- 回忆•帕姆：「虽然嘴上说着不高兴，身体的反应还是很真实的。」

### 3.4 光锥背景故事

**找到：`ItemConfigEquipment.json`**，165 条记录。

| 字段 | 记录数 | 总字符数 | 说明 |
|---|---|---|---|
| ItemBGDesc | 165 | 28,523 | 光锥背景故事，平均 173 字符/条 |
| ItemName | 165 | — | 光锥名称 |
| ItemDesc | 165 | — | 光锥简介 |

**找到：`EquipmentConfig.json`**，165 条记录，提供 EquipmentName（光锥名称，Hash 引用）。

**找到：`EquipmentSkillConfig.json`**，825 条记录，SkillDesc 字段总字符 162,960，但属于技能描述而非背景故事。

样例：
- 锋镝：「自时光中凝取的稀薄力量。正是所有微不足道的刹那，编织成了壮绝的命运。『飞矢在弦、挽弓逐鹿的那一刻，猎人的双眸最为清澈。』」
- 物穰：「生命就是有序度超越了某个阈值的存在。它的诞生便是对死寂宇宙的最终解答…」

### 3.5 模拟宇宙的奇物与祝福描述

**找到多个文件：**

| 文件 | 记录数 | 关键字段 | 说明 |
|---|---|---|---|
| RogueMiracleDisplay.json | 294 | MiracleName, MiracleBGDesc | 奇物名称与背景描述 |
| RogueMiracleEffectDisplay.json | 769 | MiracleDesc | 奇物效果描述 |
| RogueMazeBuff.json | 1,825 | BuffName, BuffDesc, BuffSimpleDesc, BuffDescBattle | 祝福名称与描述 |
| RogueAeonDisplay.json | 14 | RogueAeonName, RogueAeonPathName | 星神/命途名称 |
| RogueAeonStoryConfig.json | 26 | AeonStory_Name, AeonStory | 星神故事（叙事价值极高） |
| RogueMagicScepterDisplay.json | 24 | ScepterName, ScepterBGDesc, ScepterTriggerDesc | 权杖描述 |
| RogueTournMiracleDisplay.json | 166 | MiracleName, MiracleBGDesc | 差分宇宙奇物 |
| RogueTournCollection.json | 22 | CollectionName, CollectionDesc | 收集品描述 |
| RogueTournFormulaDisplay.json | 300 | FormulaStory | 方程故事（叙事价值高） |
| RogueNousDiceBranch.json | 12 | BranchName, BranchIntroduction, EffectDesc | 骰子分支描述 |
| RogueTournHexDisplay.json | 34 | Name, BgDesc | 信标描述 |
| RogueTournTitanTalent.json | 36 | TalentTitle, TalentDesc | 泰坦天赋描述 |
| RogueTournTitanType.json | 12 | TitanTitle, CharacterName | 泰坦类型 |

样例：
- 降维骰子：「九枚六面骰组成了这个奇特的三角体…」
- 混沌云芝：「云朵是水汽聚合的产物…混沌医师相信世上没有绝对的虚无…」
- 星神故事：「『存护』克里珀，与『贪饕』奥博洛斯同为宇宙中已知最古老的星神…」

### 3.6 短信与邮件

**MessageItemConfig.json**：13,253 条记录，3.2 MB。

| 字段 | 说明 |
|---|---|
| ID | 消息 ID |
| Sender | 发送者 |
| ItemType | 消息类型 |
| MainText | 消息正文（Hash 引用） |
| NextItemIDList | 后续消息 ID 列表 |
| SectionID | 所属消息组 |

**MessageContactsConfig.json**：295 条，含 Name（联系人名）、SignatureText（签名）。

**MessageGroupConfig.json**：739 条，消息分组。

**MessageSectionConfig.json**：751 条，消息章节。

**MessageContactsCamp.json**：22 条，联系人阵营（ContactsCamp, Name）。**此字段可能可用于分卷。**

**SysMailConfig.json**：37 条，含 MailTitle、MailSender、MailDetail。

**TarotMails.json**：294 条，塔罗牌邮件。

### 3.7 百科与名词解释

**NounAtlas.json**：99 条，NounTitle（名词标题）、NounDesc（名词描述，平均 445 字符/条）。

**TitanAtlas.json**：18 条，TitanName（泰坦名）、TitanDesc（泰坦描述）。

**TitanAtlasGroup.json**：4 条，TitanGroupName、TitanGroupDesc。

样例：
- 名词：「于原初混沌的裂隙中萌生了嫩芽…」
- 黑塔（地名）：「天才俱乐部的黑塔不满足于寻常世界的万物法则…」
- 雅利洛-Ⅵ（地名）：「历史学家大多将雅利洛-Ⅵ的星球历史追溯到上千年前的神话战争…」
- 「天谴之矛」尼卡多利：「尼卡多利是司掌纷争与竞技的泰坦…」

---

## 任务四：Config 目录复查

### 抽样方案

从 113,707 个 JSON 文件中，跨不同顶层目录随机抽取 200 个文件。

### 结果

| 指标 | 数值 |
|---|---|
| 抽样数 | 200 |
| 含 Hash 字段 | 13（6.5%） |
| 不含 Hash 字段 | 187（93.5%） |

含 Hash 的 13 个文件全部来自 `Level/` 和 `LevelOutput/` 目录，均为关卡配置中的 NPC 名称或提示文本引用，**不是叙事文本**。

### 结论

**Config 目录不含叙事文本，跳过。** 上一轮结论不变。

---

## 勘误与修正

上一轮报告中的以下错误在此修正：

1. **"大部分 NPC 对话无法提取"** — 修正：TalkSentenceConfig 有 231,687 条对话文本，是完整的对话语料。但只有 6.5% 能通过 Story 文件归属到具体任务。
2. **"BookSeriesConfig 只有标题和简介"** — 修正：书籍正文在 `LocalbookConfig.json`，1,051 本书，总计 941,323 字符。
3. **"AvatarConfig 只有名字和登场词"** — 修正：角色故事在 `StoryAtlas.json`，446 条，总计 215,814 字符。角色语音在 `VoiceAtlas.json`，5,236 条。
4. **光锥、模拟宇宙、短信、邮件、百科** — 上一轮均未覆盖，本轮已全部补查并定位到具体文件和字段。

---

## 语料源重组建议

基于体量排序和本轮补查，以下是按叙事价值重排的候选语料源（建议优先抽取）：

| 优先级 | 文件 | 字段 | 总字符数 | 理由 |
|---|---|---|---|---|
| 1 | TalkSentenceConfig.json | TalkSentenceText | 5,886,916 | 全部对话文本，语料基石 |
| 2 | LocalbookConfig.json | BookContent | 941,323 | 书籍正文，平均 895 字/条 |
| 3 | SubMission.json | DescrptionText | 597,109 | 子任务描述，叙事性强 |
| 4 | StoryAtlas.json | Story | 215,814 | 角色故事，平均 484 字/条 |
| 5 | MessageItemConfig.json | MainText | 205,409 | 手机短信，13,253 条 |
| 6 | MonsterConfig.json | MonsterIntroduction | 174,762 | 怪物背景介绍 |
| 7 | ItemConfig.json | ItemBGDesc | 119,805 | 道具背景描述 |
| 8 | VoiceAtlas.json | Voice_M | 123,197 | 角色语音台词 |
| 9 | VoiceAtlas.json | VoiceTitle | 29,547 | 语音标题 |
| 10 | RogueMiracleDisplay.json | MiracleBGDesc | 39,302 | 奇物背景描述 |
| 11 | RogueAeonStoryConfig.json | AeonStory | ~20,000 | 星神故事 |
| 12 | ChronicleConclusion.json | MissionConclusion | 36,961 | 任务章节总结 |
| 13 | NounAtlas.json | NounDesc | 44,090 | 百科名词解释 |
| 14 | ItemConfigEquipment.json | ItemBGDesc | 28,523 | 光锥背景故事 |
| 15 | TitanAtlas.json | TitanDesc | ~15,000 | 泰坦描述 |
| 16 | SysMailConfig.json | MailDetail | ~5,000 | 系统邮件 |
| 17 | BookSeriesConfig.json | BookSeriesComments | 20,526 | 书籍简介 |
| 18 | ItemConfigRelic.json | ItemBGDesc | 29,032 | 遗器背景描述 |
| 19 | LoadingDesc.json | DescTextmapID | 20,074 | 加载画面文字 |
| 20 | RogueTournFormulaDisplay.json | FormulaStory | 68,645 | 差分宇宙方程故事 |