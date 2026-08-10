# 阶段二补：数据源更新报告

> **注意：** 本报告取代 `reports/01_sources.md`。旧报告中的 StarRailData（GitLab 镜像，2024-06-17）和 StarrailDialog（2024-07-12）信息已过时，以本报告为准。

---

## 1. 新旧仓库对照

| 项目 | 旧 | 新 |
|---|---|---|
| 上游 | `Dimbreath/StarRailData` | `DimbreathBot/TurnBasedGameData` |
| 获取方式 | GitLab 镜像 `jianghanxia1/StarRailData` | GitHub SSH 直连 |
| 本地目录名 | `vendor/StarRailData` | `vendor/StarRailData`（不变） |
| commit | `df89dd11` | `648b08fb` |
| 日期 | 2024-06-17 | 2026-07-29 |
| 版本标记 | OSPRODWin2.3.0 | OSPRODWin4.4.0 |
| TextMap 体积 | 20 MB（清理后） | 48 MB |
| Story 体积 | 9.9 MB | 37 MB |
| ExcelOutput 体积 | 160 MB（980 文件） | 264 MB（2140 文件） |
| Config 体积 | 458 MB | 1.1 GB |
| 总计 | 648 MB | ~1.4 GB |

### StarrailDialog

| 项目 | 值 |
|---|---|
| commit | `149dd8e2`（未变化） |
| 日期 | 2024-07-12 |
| 状态 | 执行 `git pull` 后仍为 `Already up to date`，作者已两年未维护 |

---

## 2. 版本验证：三个信号

### 信号 1：commit 日期

```
648b08fbdb2e49739ebbf1210c9a189fcfc5e2d7 2026-07-29 09:22:06 +0200
OSPRODWin4.4.0_D15909703_A15802547_L15874300
```

- 最新 commit：**2026-07-29**（距执行日仅 8 天）
- 版本号：**4.4.0**

### 信号 2：3.x 关键词

| 关键词 | 出现次数 |
|---|---|
| 翁法罗斯 | 2,016 |
| 黄金裔 | 993 |

旧数据（2024-06）中这两个词出现次数为 0。确认是新数据。

### 信号 3：最后 15 个角色名单

按角色 ID 倒序排列（排除开拓者 {NICKNAME} 变体）：

| ID | 角色名 |
|---|---|
| 1510 | 姬子•启行 |
| 1507 | 千冶•刃 |
| 1506 | 银狼LV.<unbreak>999</unbreak> |
| 1505 | 绯英 |
| 1504 | 不死途 |
| 1502 | 爻光 |
| 1501 | 火花 |
| 1415 | 昔涟 |
| 1414 | 丹恒•腾荒 |
| 1413 | 长夜月 |
| 1412 | 刻律德菈 |
| 1410 | 海瑟音 |
| 1409 | 风堇 |
| 1408 | 白厄 |
| 1407 | 遐蝶 |

总角色数：91（含 10 个开拓者变体）

---

## 3. 冒烟测试：脚本兼容性

### 测试命令

```bash
python get_misc.py --lang=CHS --repo=<绝对路径>/vendor/StarRailData
```

### 依赖安装

- 无 `requirements.txt`
- 按错误提示安装了 `pandas` 和 `openpyxl`

### 结果：脚本崩溃

```
File "get_misc.py", line 18, in get_misc
    for idx, info in items.items():
                     ^^^^^^^^^^^
AttributeError: 'list' object has no attribute 'items'
```

### 根因分析

新数据仓库的 ExcelOutput 文件格式发生了根本性变更：

| 维度 | 旧格式 | 新格式 |
|---|---|---|
| JSON 顶层结构 | `dict`（以 ID 为 key） | `list`（ID 内嵌在记录中） |
| ExcelOutput 文件数 | 980 | 2140 |
| list 文件占比 | 未知 | **100%（2140/2140）** |

抽取脚本 `get_misc.py`、`get_dialogues.py`、`get_missions.py` 均使用 `.items()` 遍历 dict，与新格式不兼容。

Hash 查找本身已验证可用：随机抽取 50 条 `TalkSentenceConfig`，hash 值在 `TextMapCHS.json` 中的命中率 **100%**。问题纯粹是数据格式变更，不涉及 hash 方案。

### 判定结论：**脚本已失效**

三个脚本全部使用 `.items()` 遍历 ExcelOutput 数据，无法在新格式下运行。按照手册规定，不修改上游代码。

---

## 4. ExcelOutput 完整清单（部分）

总文件数：2140，总大小：259.4 MB

### 体积最大的 10 个文件

| 文件 | 大小 | 记录数 | 关键字段 |
|---|---|---|---|
| SpecialAvatarRelicMainValue.json | 51.2 MB | 64,400 | RelicMainValueType, MainValue |
| TalkSentenceConfig.json | 39.6 MB | 231,687 | TalkSentenceID, TalkSentenceText |
| StageConfig.json | 25.1 MB | 28,832 | StageID, StageType, StageName, Level, … |
| PlaneEvent.json | 11.4 MB | 76,461 | EventID, DropList, DisplayItemList |
| AvatarSkillConfig.json | 10.5 MB | 6,804 | SkillID, SkillName, SkillDesc, … |
| VoiceConfig.json | 8.3 MB | 85,598 | VoiceID, IsPlayerInvolved, VoicePath, VoiceType |
| GridFightFrontSkill.json | 6.4 MB | 4,052 | SkillID, SkillName, SkillDesc, … |
| SpecialAvatarRelic.json | 4.3 MB | 11,442 | RelicPropertyType, RelicIDList |
| AvatarSkillTreeConfig.json | 4.2 MB | 5,196 | PointID, AvatarID, PointName, PointDesc, … |
| MonsterConfig.json | 4.1 MB | 2,591 | MonsterName, MonsterIntroduction, MonsterStrategy, … |

---

## 5. 总结

**数据是新的。** commit 2026-07-29，版本 4.4.0，包含翁法罗斯（2016 次）、黄金裔（993 次）、以及刻律德菈、白厄、遐蝶、昔涟等 3.x 后期角色，确认是当前最新版本。

**脚本已失效。** StarrailDialog 的抽取脚本基于 2024 年的旧数据格式（dict），新数据已全部改为 list 格式。脚本直接崩溃在 `items.items()` 调用上，无法产出任何 JSONL。Hash 查找逻辑本身可用（100% 命中），但脚本在到达 hash 查找之前就崩溃了。

**下一步：需要自己写抽取器。** 新数据格式清晰：每个 ExcelOutput JSON 文件是一个 list，每条记录的第一个字段通常是 ID（如 `ID`、`AvatarID`、`TalkSentenceID`）。所有带 `{"Hash": <number>}` 结构的字段都可以通过 `TextMapCHS.json` 解析为中文文本。建议写一个通用的抽取器，扫描 ExcelOutput 中所有包含叙事文本的字段，按类别分类输出，不依赖上游脚本的 dict 遍历逻辑。