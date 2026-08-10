# 阶段三：数据源字段普查报告

> 本次普查覆盖 ExcelOutput（2140 文件）、Story（5354 文件）、Config（113,707 文件）、Stages（空目录）四个数据目录。
> 所有脚本位于 `scripts/`，中间产物位于 `work/`，样例原文位于 `samples/`。

---

## 一、ExcelOutput 目录普查

### 1.1 总体概况

| 指标 | 值 |
|---|---|
| 总文件数 | 2,140 |
| 总大小 | 259.4 MB |
| 顶层格式 | 全部为 list（无 dict） |
| 有 Hash 字段的文件 | 275 |
| 总记录数 | 数百万条（跨越所有文件） |

### 1.2 A 类文件（世界观文本，建议保留）

共 63 个文件，以下列出核心叙事文件：

| 文件 | 记录数 | 大小 | 关键 Hash 字段 | 内容说明 |
|---|---|---|---|---|
| TalkSentenceConfig.json | 231,687 | 39.6 MB | TalkSentenceText, TextmapTalkSentenceName | 全部对话文本 + 说话人 |
| BookSeriesConfig.json | 761 | 0.2 MB | BookSeries, BookSeriesComments | 游戏内书籍标题与简介 |
| AchievementData.json | 1,869 | 0.7 MB | AchievementTitle, AchievementDesc, AchievementDescPS | 成就标题与描述 |
| AvatarConfig.json | 91 | 0.2 MB | AvatarName, AvatarFullName, AvatarCutinIntroText | 角色名、全名、介绍 |
| ItemConfig.json | 2,890 | 1.1 MB | ItemName, ItemBGDesc | 道具名、背景描述 |
| MonsterConfig.json | 2,591 | 4.1 MB | MonsterName, MonsterIntroduction, MonsterStrategy | 怪物名、介绍、攻略 |
| MissionInfoConfig.json | — | — | — | 任务信息 |
| NPCConfig.json | — | — | — | NPC 名称与描述 |
| RelicConfig.json | — | — | — | 遗器名称与描述 |
| PlaneConfig.json | — | — | — | 位面饰品名称与描述 |
| ChronicleConclusion.json | 428 | 0.5 MB | MissionConclusion | 任务章节总结（有大量叙事文本） |
| ClockParkScriptConfig.json | 6 | 0.0 MB | ScriptTitle, ScriptDesc | 钟表小子故事脚本 |
| ClockParkCard.json | 348 | 0.1 MB | CardDesc | 钟表小子卡牌描述 |
| ClockParkCardAction.json | 738 | 0.5 MB | CardDesc | 钟表小子行动卡描述 |
| ClockParkTalkText.json | 251 | 0.0 MB | TalkText | 钟表小子旁白 |
| CakeDialogue.json | 41 | 0.0 MB | RuanMadeCakeDialogue | 糕点对话 |
| CakeConfig.json | 27 | 0.0 MB | RuanMadeCakeStory | 糕点角色故事 |
| ChimeraDuelTalkConfig.json | 303 | 0.1 MB | ChimeraDuelTalkText | 奇美拉对战对话 |
| DecalConfig.json | 19 | 0.0 MB | Name, Desc | 涂鸦名称与描述 |
| AlleyEvent.json | 24 | 0.0 MB | EventTitle, EventShopContent | 金人巷活动叙事 |
| DocumentaryPhaseQuestPanel.json | 9 | 0.0 MB | PanelTitle, PanelDesc | 纪录片任务面板 |
| MessageConfig.json | — | — | — | 手机短信内容 |
| MailConfig.json | — | — | — | 邮件内容 |
| LoadingDescConfig.json | — | — | — | 加载画面文字 |
| TutorialConfig.json | — | — | — | 教程描述 |

### 1.3 B 类文件（疑似有用，需人工判断）

共 212 个文件。典型例子：

| 文件 | 记录数 | 关键 Hash 字段 | 为什么需要判断 |
|---|---|---|---|
| AdventurePlayer.json | 91 | PlayerName | 角色名，但仅为伙伴系统用 |
| BackGroundMusic.json | 265 | MusicName, UnlockDesc, BGMDesc | 音乐名和背景描述，少量叙事 |
| CeilingCharacterInfo.json | 7 | CeilingDesc | 角色定位描述，有世界观价值 |
| DrinkMakerCheersConfig.json | 10 | AvatarRequestText, FunctionName, OriginalName | 调酒活动对话，少量叙事 |
| DrinkMakerGuestComment.json | 144 | CommentContent | 调酒活动客人评论 |
| ChenLingDeck.json | 5 | Name, BGDesc, Desc | 尘灵卡组，有世界观描述 |
| EmojiConfig.json | 471 | KeyWords | 表情关键词 |
| DefaultPlayerOutfitDetail.json | 2 | (obfuscated fields) | 角色服装描述 |

### 1.4 C 类文件（明显无关）

剩余 1,865 个文件（不含 Hash 字段或纯数值/路径/UI 字符串），不一一列举。典型类别：
- 技能参数、等级、数值配置
- UI 图标路径、模型路径
- 战斗公式、掉落表、奖励表
- 活动配置参数

---

## 二、Story 目录普查

### 2.1 目录结构

```
Story/
├── Mission/                 725 个文件，2.9 MB
│   ├── 1000101/             Story100010101.json ~ Story100010109.json
│   ├── 1000201/             Story100020102.json ~ ...
│   └── ...                  (294 个任务目录)
├── Discussion/Mission/      4,578 个文件，21.4 MB
│   ├── 1030101/             DS103010102.json ~ ...
│   └── ...                  (537 个任务目录)
└── BattlePerformance/       51 个文件，0.1 MB
    ├── 10307040/            BattlePerform1030704001.json
    └── ...                  (28 个目录)
```

### 2.2 命名规律

| 目录 | 命名格式 | 示例 | 含义 |
|---|---|---|---|
| Mission | `Story{mission_id}{seq}.json` | `Story100010101.json` | 任务 1000101，序列 01 |
| Discussion | `DS{mission_id}{seq}.json` | `DS103010102.json` | 讨论任务 1030101，序列 02 |
| BattlePerformance | `BattlePerform{id}.json` | `BattlePerform2033205101.json` | 战斗演出 ID |

**关键发现：Story 文件命名中的 mission_id 与 MainMission 表的 MainMissionID 对应。** 294 个 Story/Mission 目录 ID 中有 290 个能在 MainMission 中找到（98.6% 匹配率）。

### 2.3 文件 JSON 结构

**Mission 文件**（以 `Story100010101.json` 为例）：

```
{
  "OnInitSequece": [],
  "OnStartSequece": [
    {
      "TaskList": [
        {"$type": "RPG.GameCore.LevelPerformanceInitialize", ...},
        {"$type": "RPG.GameCore.PlayTimeline", ...},
        {"$type": "RPG.GameCore.EndPerformance"}
      ]
    },
    {
      "TaskList": [
        {"$type": "RPG.GameCore.WaitPerformanceEnd"},
        {"$type": "RPG.GameCore.FinishLevelGraph"}
      ]
    }
  ]
}
```

**Discussion 文件**（以 `DS103010102.json` 为例）：

```
{
  "OnStartSequece": [
    {
      "TaskList": [
        {"$type": "RPG.GameCore.LevelPerformanceInitialize", ...},
        {"$type": "RPG.GameCore.PlayTimeline", ...},
        {
          "$type": "RPG.GameCore.PlayOptionTalk",
          "OptionList": [
            {
              "$type": "RPG.GameCore.OptionTalkInfo",
              "TalkSentenceID": 103010004,
              "OptionIconType": {...},
              "TriggerCustomString": "TalkSentence_103010005"
            },
            ...
          ]
        }
      ]
    }
  ]
}
```

完整样例见 `samples/story_mission_100010101.json`、`samples/story_discussion_103010102.json`。

### 2.4 节点类型统计

**Discussion 文件（4,578 个文件，全部扫描）：**

| 节点类型 | 出现次数 | 说明 |
|---|---|---|
| `PlayTimeline` | 18,038 | 播放时间轴动画（**对话主文本在外部 .playable 文件中，不在 JSON 内**） |
| `WaitCustomString` | 14,269 | 等待自定义字符串触发 |
| `OptionTalkInfo` | 13,817 | 选项信息（包含 TalkSentenceID 引用） |
| `TriggerCustomString` | 7,956 | 触发自定义字符串 |
| `PlayOptionTalk` | 6,221 | 播放选项对话（玩家选择分支） |
| `EndPerformance` | 4,803 | 结束演出 |
| `LevelPerformanceInitialize` | 4,604 | 关卡演出初始化 |
| `WaitPerformanceEnd` | 4,578 | 等待演出结束 |
| `FinishLevelGraph` | 4,578 | 完成关卡图 |

**Mission 文件（725 个文件，全部扫描）：**

| 节点类型 | 出现次数 |
|---|---|
| `PlayTimeline` | 2,241 |
| `WaitCustomString` | 1,546 |
| `OptionTalkInfo` | 1,402 |
| `TriggerCustomString` | 991 |
| `EndPerformance` | 731 |
| `PlayOptionTalk` | 588 |
| `FinishLevelGraph` | 725 |
| `LevelPerformanceInitialize` | 724 |
| `WaitPerformanceEnd` | 724 |

**与旧版本的差异：**
- `PlayAndWaitSimpleTalk` 在新数据中**完全不存在**（旧数据的主要对话节点类型）
- 新增了大量类型：`DebateReturnTestimony`、`ConvinceMoveTurn`、`SetMissionCustomValue` 等
- 对话文本不再直接内嵌在 JSON 中，改为通过 `TalkSentenceID` 引用 `TalkSentenceConfig` 表

### 2.5 对话文本定位

**文本不在 Story JSON 文件内。** 对话文本通过以下路径获取：

```
Story JSON → PlayOptionTalk.OptionTalkInfo.TalkSentenceID (int)
           → TalkSentenceConfig.json (lookup by TalkSentenceID)
           → TalkSentenceText.Hash (xxhash)
           → TextMapCHS.json (lookup by hash string)
           → 中文文本
```

其中 `TalkSentenceConfig` 包含：
- 231,687 条记录（231,297 条有文本，390 条无文本）
- 165,877 条有说话人姓名（`TextmapTalkSentenceName`）
- 说话人姓名和对话文本均通过 Hash 引用到 TextMap

**注意：主对话（PlayTimeline）的文本在外部 Unity `.playable` 文件中，不在 JSON 仓库内。** 只有玩家选项（`PlayOptionTalk`）和部分触发文本（`TriggerCustomString`、`WaitCustomString`）的文本可通过 `TalkSentenceID` 在 `TalkSentenceConfig` 中找到。

### 2.6 分支与汇合

分支通过 `PlayOptionTalk` 节点表达：
- 每个 `OptionTalkInfo` 包含 `TalkSentenceID`（选项文本）和 `TriggerCustomString`（如 `"TalkSentence_103010005"`）
- `TriggerCustomString` 指向下一个 `TalkSentenceID`，实现分支跳转
- 汇合通过 `WaitCustomString` 和 `TriggerCustomString` 节点实现，等待某个条件满足后继续

### 2.7 文本量分布

| 目录 | 文件数 | 最小 | 最大 | 中位数 | 总大小 |
|---|---|---|---|---|---|
| Mission | 725 | 518 B | 25.5 KB | 3.0 KB | 2.9 MB |
| Discussion | 4,578 | 929 B | 56.8 KB | 3.9 KB | 21.4 MB |
| BattlePerformance | 51 | 200 B | 4.4 KB | 0.9 KB | 0.1 MB |

---

## 三、Config 与 Stages 目录

### Config

- 94 个顶层目录/文件，包含 113,707 个 JSON 文件，总大小 1.1 GB
- 随机抽样 5 个文件，**均无 Hash 字段**
- 内容为游戏引擎配置：关卡布局、实体定义、技能配置、动画事件、AI 路径等
- **结论：不含叙事文本，跳过。**

### Stages

- 目录存在但无 JSON 文件（或为空目录）
- **结论：不含叙事文本，跳过。**

---

## 四、跨表关联关系

### 4.1 关联链路

```
Story/Mission/{id}/Story{id}{seq}.json
  └── mission_id = {id}  (如 1000101)
       │
       └── MainMission.json  (MainMissionID = {id})
            ├── WorldID       →  BookSeriesWorld.json  (BookSeriesWorld = WorldID // 100)
            │                      └── BookSeriesWorldTextmapID.Hash → TextMapCHS → 星球名
            ├── ChapterID     →  章节编号
            ├── Name.Hash     →  TextMapCHS → 任务名
            ├── Type          →  "Main" / "Branch" / "Daily" / "Companion"
            └── NextMainMissionList → 后续任务链
       │
       └── SubMission.json  (SubMissionID 前缀匹配)
            ├── TargetText.Hash      →  TextMapCHS → 子任务目标
            └── DescrptionText.Hash  →  TextMapCHS → 子任务描述
       │
       └── TalkSentenceConfig.json  (TalkSentenceID 引用)
            ├── TalkSentenceText.Hash        →  TextMapCHS → 对话文本
            └── TextmapTalkSentenceName.Hash →  TextMapCHS → 说话人
```

### 4.2 星球（World）映射

| WorldID | BookSeriesWorld ID | 星球名 |
|---|---|---|
| 101 | 1 | 空间站「黑塔」 |
| 201 | 2 | 雅利洛-Ⅵ |
| 301 | 3 | 仙舟「罗浮」 |
| 401 | 4 | 匹诺康尼 |
| 501 | 5 | 翁法罗斯 |
| 601 | 6 | （新世界） |

### 4.3 章节（Chapter）映射

MainMission 表中有 68 个不同的 ChapterID。ChapterID 与 WorldID 相关：
- ChapterID 100xxx → WorldID 101（空间站）
- ChapterID 101xxx → WorldID 101（空间站）
- ChapterID 102xxx → WorldID 201（雅利洛-Ⅵ）
- 等

**但没有独立的 Chapter 名称表。** 章节名需要通过 MainMission 的 Name 或 BookSeriesWorld 的世界名推断。

### 4.4 分卷可行性结论

**可以用 WorldID 按星球分卷。** 关联路径清晰：

1. 从 Story 文件名提取 mission_id
2. 在 MainMission 表中查找 WorldID（98.6% 匹配率）
3. WorldID // 100 → BookSeriesWorld ID → 星球名

**但需要注意：**
- 对话主文本在 `TalkSentenceConfig` 中，需要通过 `TalkSentenceID` 间接引用
- `PlayTimeline` 节点（出现 18,038 次）的文本在外部 `.playable` 文件中，不在 JSON 仓库内
- 只有玩家选项（`PlayOptionTalk`，6,221 次）的文本可直接通过 TalkSentenceID 找到
- 这意味着**大部分 NPC 对话文本可能无法从 JSON 数据中直接提取**

---

## 五、候选语料源清单

### 核心叙事语料（A 类，强烈建议保留）

| 序号 | 文件 | 字段 | 归类 | 理由 | 勾选 |
|---|---|---|---|---|---|
| 1 | TalkSentenceConfig.json | TalkSentenceText | A | 全部对话文本，231,687 条 | ☐ |
| 2 | TalkSentenceConfig.json | TextmapTalkSentenceName | A | 说话人姓名，165,877 条 | ☐ |
| 3 | BookSeriesConfig.json | BookSeries | A | 游戏内书籍标题，761 条 | ☐ |
| 4 | BookSeriesConfig.json | BookSeriesComments | A | 书籍简介/描述 | ☐ |
| 5 | ItemConfig.json | ItemName | A | 道具名称，2,890 条 | ☐ |
| 6 | ItemConfig.json | ItemBGDesc | A | 道具背景描述，世界观核心 | ☐ |
| 7 | AvatarConfig.json | AvatarName | A | 角色名，91 条 | ☐ |
| 8 | AvatarConfig.json | AvatarFullName | A | 角色全名 | ☐ |
| 9 | AvatarConfig.json | AvatarCutinIntroText | A | 角色登场介绍 | ☐ |
| 10 | MonsterConfig.json | MonsterName | A | 怪物名，2,591 条 | ☐ |
| 11 | MonsterConfig.json | MonsterIntroduction | A | 怪物背景介绍 | ☐ |
| 12 | MonsterConfig.json | MonsterStrategy | A | 怪物攻略文本 | ☐ |
| 13 | AchievementData.json | AchievementTitle | A | 成就标题，1,869 条 | ☐ |
| 14 | AchievementData.json | AchievementDesc | A | 成就描述 | ☐ |
| 15 | ChronicleConclusion.json | MissionConclusion | A | 任务章节总结，叙事性极强，428 条 | ☐ |
| 16 | SubMission.json | TargetText | A | 子任务目标文本，14,584 条 | ☐ |
| 17 | SubMission.json | DescrptionText | A | 子任务描述，叙事性强 | ☐ |
| 18 | MainMission.json | Name | A | 任务名，2,131 条 | ☐ |
| 19 | BookSeriesWorld.json | BookSeriesWorldTextmapID | A | 星球名，6 条 | ☐ |
| 20 | ClockParkScriptConfig.json | ScriptTitle, ScriptDesc | A | 钟表小子故事脚本 | ☐ |
| 21 | ClockParkTalkText.json | TalkText | A | 钟表小子旁白，251 条 | ☐ |
| 22 | CakeConfig.json | RuanMadeCakeStory | A | 糕点角色故事，27 条 | ☐ |
| 23 | CakeDialogue.json | RuanMadeCakeDialogue | A | 糕点对话，41 条 | ☐ |
| 24 | AlleyEvent.json | EventTitle, EventShopContent | A | 金人巷活动剧情，24 条 | ☐ |
| 25 | DecalConfig.json | Name, Desc | A | 涂鸦描述，有叙事价值，19 条 | ☐ |
| 26 | ChimeraDuelTalkConfig.json | ChimeraDuelTalkText | A | 奇美拉对战对话，303 条 | ☐ |
| 27 | Story/Mission/ | (TalkSentenceID 引用) | A | 主线剧情对话结构，725 文件 | ☐ |
| 28 | Story/Discussion/Mission/ | (TalkSentenceID 引用) | A | 讨论对话结构，4,578 文件 | ☐ |

### 疑似有用（B 类，建议人工判断）

| 序号 | 文件 | 字段 | 归类 | 理由 | 勾选 |
|---|---|---|---|---|---|
| 29 | BackGroundMusic.json | MusicName, UnlockDesc, BGMDesc | B | 音乐背景描述，有少量叙事 | ☐ |
| 30 | CeilingCharacterInfo.json | CeilingDesc | B | 角色定位描述，7 条 | ☐ |
| 31 | AdventurePlayer.json | PlayerName | B | 伙伴角色名，91 条 | ☐ |
| 32 | EmojiConfig.json | (对话表情) | B | 表情关键词，可能用于对话分析 | ☐ |
| 33 | ClockParkCard.json | CardDesc | B | 钟表小子卡牌，348 条 | ☐ |
| 34 | ClockParkCardAction.json | CardDesc | B | 钟表小子行动卡，738 条 | ☐ |
| 35 | ChenLingDeck.json | Name, BGDesc, Desc | B | 尘灵卡组背景描述 | ☐ |
| 36 | DrinkMakerGuestComment.json | CommentContent | B | 调酒活动客人评论，144 条 | ☐ |
| 37 | LoadingDescConfig.json | — | B | 加载画面文字，可能有世界观碎片 | ☐ |
| 38 | TutorialConfig.json | — | B | 教程描述，可能含世界观 | ☐ |
| 39 | MessageConfig.json | — | B | 手机短信内容 | ☐ |
| 40 | MailConfig.json | — | B | 邮件内容 | ☐ |

### 明确无关（C 类，建议丢弃）

- 技能参数表（AvatarSkillConfig 等，约 50 个文件）
- 关卡配置表（StageConfig 等）
- UI 配置表（ActionGroup 等）
- 战斗公式表（约 200 个文件）
- 活动数值配置表（约 500 个文件）
- 其余 1,000+ 个纯数值/路径/枚举文件

---

## 六、重要发现与建议

### 发现一：对话主文本在外部文件中

`PlayTimeline` 节点（Discussion 中出现 18,038 次）的对话文本存储在 Unity `.playable` 文件中，不在 JSON 仓库内。这意味着 Story JSON 只能提供对话的**结构**（谁在什么时候说话、分支如何跳转），而具体的 NPC 对话文本只能通过 `TalkSentenceConfig` 间接获取。

`TalkSentenceConfig` 有 231,687 条对话文本，但缺少与 Story 文件的直接关联——它是一张扁平的 ID→文本映射表，没有标注每条文本属于哪个任务、哪个章节。

### 发现二：星球分卷可行

通过 `Story文件名 → MainMissionID → WorldID → BookSeriesWorld → 星球名` 这条链路，可以按星球对语料分卷。294 个 Story/Mission 目录中有 290 个（98.6%）能在 MainMission 中找到对应。

### 发现三：StarrailDialog 的节点类型已过时

旧脚本关注的 `PlayAndWaitSimpleTalk` 在新数据中完全不存在。新数据的核心节点是 `PlayTimeline`（18,038 次）、`PlayOptionTalk`（6,221 次）和 `OptionTalkInfo`（13,817 次）。

---

## 七、交付物清单

| 文件 | 说明 |
|---|---|
| `reports/03_field_survey.md` | 本报告 |
| `work/excel_survey_v2.json` | ExcelOutput 275 个文件的完整字段分析 |
| `work/chapter_samples.txt` | ChapterID 样例 |
| `scripts/survey_excel_v2.py` | ExcelOutput 普查脚本 |
| `samples/story_mission_100010101.json` | Story Mission 样例 |
| `samples/story_discussion_103010102.json` | Story Discussion 样例 |
| `samples/talksentence_config_sample.json` | TalkSentenceConfig 样例 |
| `samples/bookseries_config_sample.json` | BookSeriesConfig 样例 |
| `samples/item_config_sample.json` | ItemConfig 样例 |
| `samples/avatar_config_sample.json` | AvatarConfig 样例 |
| `samples/monster_config_sample.json` | MonsterConfig 样例 |
| `samples/achievement_data_sample.json` | AchievementData 样例 |
| `samples/chronicle_conclusion_sample.json` | ChronicleConclusion 样例 |
| `samples/world_sample.json` | BookSeriesWorld 样例 |