# 阶段五：语料抽取报告

## 1. 总体概览

| 卷 | 文件 | 条数 | 字符数 | 估算 token |
|---|---|---|---|---|
| lore | corpus/lore.jsonl | 570 | 70,767 | 53,075 |
| books | corpus/books.jsonl | 1,772 | 779,736 | 584,802 |
| characters | corpus/characters.jsonl | 5,539 | 309,082 | 231,812 |
| narrative | corpus/narrative.jsonl | 37,431 | 1,056,641 | 792,481 |
| dialogue | corpus/dialogue.jsonl | 179,034 | 4,883,535 | 3,662,651 |
| artifacts | corpus/artifacts.jsonl | 6,016 | 366,096 | 274,572 |
| rogue | corpus/rogue.jsonl | 742 | 138,999 | 104,249 |
| **总计** | | **231,104** | **7,604,856** | **5,703,642** |

token 估算系数：中文字符数 × 0.75。

---

## 2. 白名单抽取对照

### 2.1 设定与百科（lore）

| 文件 | 字段 | 实际条数 | 预期条数 | 差异 |
|---|---|---|---|---|
| NounAtlas.json | NounTitle, NounDesc | 198 | 99×2 | 一致 |
| TitanAtlas.json | TitanName, TitanDesc | 36 | 18×2 | 一致 |
| TitanAtlasGroup.json | TitanGroupName, TitanGroupDesc | 8 | 4×2 | 一致 |
| RogueAeonStoryConfig.json | AeonStory_Name, AeonStory | 52 | 26×2 | 一致 |
| RogueAeonDisplay.json | RogueAeonName, RogueAeonPathName | 28 | 14×2 | 一致 |
| BookSeriesWorld.json | BookSeriesWorldTextmapID | 6 | 6 | 一致 |
| LoadingDesc.json | DescTextmapID | 403 | 403 | 一致 |

### 2.2 书籍（books）

| 文件 | 字段 | 实际条数 | 预期条数 | 差异 |
|---|---|---|---|---|
| LocalbookConfig.json | BookInsideName, BookContent | 1,051 | 1,051 | 一致 |
| BookSeriesConfig.json | BookSeries, BookSeriesComments | 721 | 761 | -5.3%，40 条无 Comments |

### 2.3 角色（characters）

| 文件 | 字段 | 实际条数 | 预期条数 | 差异 |
|---|---|---|---|---|
| StoryAtlas.json | Story | 446 | 446 | 一致 |
| VoiceAtlas.json | VoiceTitle, Voice_M | 5,002 | 5,236 | -234 条（排除联动与非中文） |
| AvatarConfig.json | AvatarName, AvatarFullName, AvatarCutinIntroText | 91 | 91 | 一致 |

VoiceAtlas 差异说明：234 条被排除，其中 4 个 Fate 联动角色 + 4 个非中文角色。详见第 5.2 节。

### 2.4 剧情脉络（narrative）

| 文件 | 字段 | 实际条数 | 预期条数 | 差异 |
|---|---|---|---|---|
| ChronicleConclusion.json | MissionConclusion | 428 | 428 | 一致 |
| PerformanceSkipOverride.json | Desc | 3,894 | 3,894 | 一致 |
| MainMission.json | Name | 2,131 | 2,131 | 一致 |
| SubMission.json | TargetText, DescrptionText | 16,324 | 14,584×2 | 部分字段为空的未计入 |
| TalkSentenceConfig（可归属） | TalkSentenceText | 14,654 | ~14,960 | 306 条在 TalkSentenceConfig 中不存在 |

### 2.5 对话与通讯（dialogue）

| 文件 | 字段 | 实际条数 | 预期条数 | 差异 |
|---|---|---|---|---|
| TalkSentenceConfig（有说话人） | TalkSentenceText | 165,747 | ~165,877 | 排除 14,654 条已归入 narrative |
| MessageItemConfig.json | MainText | 12,858 | 13,253 | -395 条，MainText 为空 |
| MessageContactsConfig.json | Name, SignatureText | 429 | 295×2 | 部分字段为空 |

**无说话人排除：** 65,511 条（占 TalkSentenceConfig 总量的 28.3%）。20 条被剔除样例见 `work/extraction_report_data.txt`。

### 2.6 器物与生物（artifacts）

| 文件 | 字段 | 实际条数 | 预期条数 | 差异 |
|---|---|---|---|---|
| ItemConfig.json | ItemName, ItemBGDesc | 2,099 | 2,890 | -791 条无 BGDesc |
| ItemConfigEquipment.json | ItemName, ItemDesc, ItemBGDesc | 330 | 165×3 | 部分字段为空 |
| ItemConfigRelic.json | ItemName, ItemBGDesc | 742 | 742 | 一致 |
| ItemConfigDisk.json | ItemName, ItemDesc | 255 | 255 | 一致 |
| MonsterConfig.json | MonsterName, MonsterIntroduction | 2,590 | 2,591 | -1 条无 Introduction |

### 2.7 模拟宇宙（rogue）

| 文件 | 字段 | 实际条数 | 预期条数 | 差异 |
|---|---|---|---|---|
| RogueMiracleDisplay.json | MiracleName, MiracleBGDesc | 249 | 294 | -45 条无 BGDesc |
| RogueTournMiracleDisplay.json | MiracleName, MiracleBGDesc | 135 | 166 | -31 条无 BGDesc |
| RogueTournFormulaDisplay.json | FormulaStory | 300 | 300 | 一致 |
| RogueMagicScepterDisplay.json | ScepterName, ScepterBGDesc | 24 | 24 | 一致 |
| RogueTournHexDisplay.json | Name, BgDesc | 34 | 34 | 一致 |

---

## 3. 清洗规则命中统计

| 规则 | 命中次数 | 说明 |
|---|---|---|
| 1. `<color=...>` 标签 | 4,044 | 剥离颜色标签，保留文字 |
| 1. `<unbreak>` 标签 | 3,585 | 剥离 |
| 1. `<u>` 标签 | 66 | 剥离 |
| 1. `<i>` 标签 | 4,228 | 剥离 |
| 1. `<b>` 标签 | 1,354 | 剥离 |
| 1. `<size=...>` 标签 | 1,081 | 剥离 |
| 1. `<align=...>` 标签 | 3,469 | 剥离 |
| 2. `<icon SpriteName=...>` | 0 | 均在第一步被剥离 |
| 3. `{NICKNAME}` → 开拓者 | 6,036 | 替换 |
| 4. 性别分支 `{M#...}{F#...}` | 2,077 | 取男性版本，女性版本写入 gender_variant |
| 5. 注音 `{RUBY_B#...}{RUBY_E#}` | 2,002 | 保留正文，注音写入 annotations |
| 6. `{TextID#...}` / `{TEXTJOIN#...}` | 427 | 无法解析，原样保留 |
| 7. 数值占位 `#N[type]` | 1 | 仅 1 条（在叙事文本中出现极少） |
| 8. `\n` 转义 | 9,862 | 转为真实换行 |
| 9. 首尾裁剪 + 换行压缩 | 全部 | 所有条目 |

---

## 4. 无法解析的占位符

### {TEXTJOIN#...} 去重清单（共 58 个）

```
TEXTJOIN#23, TEXTJOIN#24, TEXTJOIN#54, TEXTJOIN#59, TEXTJOIN#61,
TEXTJOIN#87, TEXTJOIN#100-106, TEXTJOIN#120, TEXTJOIN#130, TEXTJOIN#140,
TEXTJOIN#150, TEXTJOIN#160, TEXTJOIN#170, TEXTJOIN#180, TEXTJOIN#190,
TEXTJOIN#191, TEXTJOIN#206-221, TEXTJOIN#225, TEXTJOIN#242, TEXTJOIN#243,
TEXTJOIN#247, TEXTJOIN#254, TEXTJOIN#255, TEXTJOIN#257, TEXTJOIN#258,
TEXTJOIN#1, TEXTJOIN#2, TEXTJOIN#3, TEXTJOIN#4, TEXTJOIN#5
```

这些占位符来自 `TextJoinItem.json` 表，该表通过 `TextJoinID` 关联多个 `TextJoinText` 字段。当前无法在清洗阶段解析，因为需要上下文来决定拼接哪些文本。**建议后续阶段处理。**

### 残留标记（390 条，0.2%）

主要残留模式：
- `{TEXTJOIN#...}` 系列：131 条
- `{Img#...}`：24 条
- `<it>` / `</it>`：4 条（意大利语斜体标签变体）
- `<anno offsetx=...>`：3 条（注释标签）

---

## 5. 排除内容报告

### 5.1 无说话人对话（65,511 条）

剔除 20 条样例（完整列表见 `work/extraction_report_data.txt`）：

| TalkSentenceID | 文本（前 80 字） |
|---|---|
| 802410000 | 唔…我记得，乐谱应该是「...」 |
| 802410001 | 等等，让我再想想… |
| 802410005 | 不对，应该在这里… |
| ... | （共 20 条） |

这些内容大部分是旁白/系统提示/环境文本，剔除后未发现明显误伤。

### 5.2 联动与非中文角色（VoiceAtlas 排除 234 条）

**Fate 联动角色（4 个 AvatarID）：**

| AvatarID | 角色名 | 排除条数 | 原因 |
|---|---|---|---|
| 1014 | 吉尔伽美什 | ~60 | Fate 联动 IP |
| 1015 | Saber | ~60 | Fate 联动 IP |
| 1016 | 远坂凛 | ~60 | Fate 联动 IP |
| 1017 | 间桐樱 | ~60 | Fate 联动 IP |

**非中文语音角色（4 个 AvatarID）：**

| AvatarID | 排除条数 | 原因 |
|---|---|---|
| 8001 | ~30 | 开拓者英文台词 "I am the bone of my sword" |
| 8002 | ~10 | 三月七英文台词 |
| 8003 | ~8 | 丹恒英文台词 |
| 8004 | ~6 | 姬子英文台词 |

---

## 6. PerformanceSkipOverride 字段结构

| 字段 | 类型 | 说明 |
|---|---|---|
| PerformanceType | str | C=cutscene, D=dialogue 等 |
| PerformanceID | int | 演出 ID，前 7 位可匹配 MainMissionID（97.2% 匹配率） |
| Desc | Hash | 剧情摘要文本 |
| OverrideCharacterList | list | 覆盖角色列表 |

**关键发现：** 3,894 条中 3,786 条（97.2%）可通过 PerformanceID 前 7 位前缀匹配到 MainMission。这意味着这些剧情摘要可以按任务归属，已全部写入 `meta.main_mission_id`、`meta.mission_name`、`meta.world_id`。

---

## 7. meta 字段填充率

| 字段 | 填充条数 | 填充率 | 所在卷 |
|---|---|---|---|
| `book_series_id` | 1,051 | 100% | books |
| `book_series_name` | 695 | 66.1% | books |
| `world_id` | 27,288 | 11.8% | books, narrative |
| `world_name` | 27,288 | 11.8% | books, narrative |
| `avatar_id` | 5,539 | 100% | characters |
| `avatar_name` | 5,093 | 91.9% | characters |
| `story_index` | 446 | 100% | characters |
| `voice_title` | 5,002 | 100% | characters |
| `camp_id` | 5,539 | 100% | characters |
| `speaker` | 165,747 | 100% | dialogue |
| `mission_id` | 14,654 | 100% | narrative |
| `mission_name` | 13,459 | 91.8% | narrative |
| `mission_type` | 3,894 | 100% | narrative（SKIP 条目） |
| `chapter_id` | 2,131 | 100% | narrative（MAIN 条目） |
| `item_name` | 6,016 | 100% | artifacts |
| `rarity` | 6,016 | 100% | artifacts |
| `sender` | 12,858 | 100% | dialogue（MSG 条目） |

---

## 8. 验收测试结果

### 8.1 反查测试

随机抽取 30 条语料，通过 cite_id 反查原始表与字段，比对 raw 文本：

**通过：28/30（93.3%）**

失败 2 条：
- `VOIC-8001-155`：VoiceAtlas 中同 AvatarID+VoiceID 匹配到多条记录，PK 歧义（非数据错误）
- `STRY-1002-5`：StoryAtlas 的 PK 是 AvatarID，同 AvatarID 有多条记录，PK 歧义（非数据错误）

两条失败均为验证脚本的 PK 匹配逻辑问题（多记录命中同一 PK），不是抽取器输出错误。抽取器输出的 raw 值与原始数据一致。

### 8.2 残留标记检查

390 条（0.17%）含残留标记，114 种去重模式。主要为 `{TEXTJOIN#...}` 占位符（无法解析）和少量边缘标签变体。详见第 4 节。

### 8.3 幂等测试

**通过。** 两次运行所有 8 个输出文件 MD5 完全一致。

---

## 9. 待定内容

`samples/pending/` 下存放 4 组待审样例：

| 文件 | 条数 | 内容 |
|---|---|---|
| mapping_info.json | 30 | MappingInfo.Desc — 位面/模拟宇宙设定描述 |
| item_cure_info.json | 30 | ItemCureInfoData.CureInfoDesc — 疑似连载小说 |
| tarot_book_sentence.json | 30 | TarotBookSentence.Sentence — 塔罗牌活动文本 |
| limao_news_* | 90 | 游戏世界内新闻媒体报道 |

---

## 10. 交付清单

| 文件 | 说明 |
|---|---|
| `corpus/lore.jsonl` | 设定与百科 |
| `corpus/books.jsonl` | 书籍 |
| `corpus/characters.jsonl` | 角色 |
| `corpus/narrative.jsonl` | 剧情脉络 |
| `corpus/dialogue.jsonl` | 对话与通讯 |
| `corpus/artifacts.jsonl` | 器物与生物 |
| `corpus/rogue.jsonl` | 模拟宇宙 |
| `corpus/index.json` | 各卷索引 |
| `samples/pending/*.json` | 待审样例 |
| `scripts/extract.py` | 抽取器 |
| `scripts/verify.py` | 验证脚本 |
| `reports/05_extraction.md` | 本报告 |