> ⚠️ **本报告已被 [01b_source_update.md](./01b_source_update.md) 取代。** 旧数据源（GitLab 镜像，2024-06-17）已替换为 DimbreathBot/TurnBasedGameData（2026-07-29）。

# 阶段二：数据源拉取报告（已过时）

## 2.1 StarRailData（游戏数据 dump）

### 获取方式

| 项目 | 值 |
|---|---|
| 来源 | GitLab 镜像 |
| URL | `https://gitlab.com/jianghanxia1/StarRailData.git` |
| 备选原因 | GitHub 直连失败（HTTP 443 连接超时，疑似区域限制） |
| commit hash | `df89dd1138e751c8b1a62c92fc2bafac421dc18f` |
| 最后更新时间 | 2024-06-17 03:17:16 -0300 |

### 克隆方式

```bash
git clone --depth 1 --filter=blob:none --sparse <url>
git sparse-checkout set TextMap ExcelOutput Story Config
```

### 顶层目录结构

| 目录 | 体积 | 文件/子目录数 | 说明 |
|---|---|---|---|
| TextMap | 20 MB | 1 文件（仅保留 CHS） | 简体中文文本映射表 |
| ExcelOutput | 160 MB | 980 个 JSON 文件 | 游戏配置表（道具、角色、成就等） |
| Story | 9.9 MB | 3 个子目录 | 剧情对话原始数据 |
| Config | 458 MB | 82 个文件/子目录 | 游戏引擎配置（技能、动画、实体等） |
| Stages | 未检出 | — | 关卡场景配置，不需要 |

### TextMap 处理

原始 TextMap 目录包含 26 个文件，覆盖 13 种语言（每种语言有完整版和 Main 精简版两个版本）。按照手册要求只保留 `TextMapCHS.json`，其余 25 个文件已删除，节省约 430 MB 空间。

- `TextMapCHS.json`：207,357 行，20.5 MB

### 二层目录结构

**Story/**
```
Story/
├── BattlePerformance/       # 战斗演出对话
│   ├── 20332051/
│   └── 20332052/
├── Discussion/              # 讨论对话
│   └── Mission/             # 160 个任务目录（编号 1030101 ~ …）
└── Mission/                 # 任务对话
```

**ExcelOutput/**（980 个文件，部分示例）
```
AchievementData.json, AchievementSeries.json, ActionGroup.json,
ActivityConfigPunkLord.json, ...
AvatarConfig.json, ...  // 角色配置
ItemConfig.json, ...    // 道具配置
BookSeriesConfig.json, ...  // 书籍系列
```

**Config/**（82 个文件/子目录，部分示例）
```
AssetPreload/, AudioConfig.json, BattleBGMConfig.json,
CameraTemplate/, ConfigAbility/, ConfigCharacter/,
ConfigMazeBuff/, ConfigProp/, ...
```

### 注意事项

- 此仓库来自 GitLab 镜像，非官方 Dimbreath/StarRailData 主仓库。数据版本为 2024-06-17，可能滞后于最新游戏版本。
- 原始 GitHub 仓库访问失败：`Failed to connect to github.com port 443`，已记录到 ISSUES.md。

---

## 2.2 StarrailDialog（抽取脚本）

### 获取方式

| 项目 | 值 |
|---|---|
| 来源 | GitHub |
| URL | `https://github.com/mrzjy/StarrailDialog.git` |
| commit hash | `149dd8e2e7c9a87fbe6a8f3982e4eba73b0bcd18` |
| 最后更新时间 | 2024-07-12 16:35:09 +0800 |
| 体积 | 11 MB |

### 目录结构

```
StarrailDialog/
├── .gitignore
├── README.md             (46 KB，详细文档)
├── get_dialogues.py      (1.2 KB，对话抽取入口)
├── get_misc.py           (9.8 KB，杂项抽取入口)
├── get_missions.py       (5.2 KB，任务抽取入口)
├── statistics.py         (369 B，统计脚本)
├── data/
│   ├── dialogues/        (空，待产出)
│   ├── misc/             (空，待产出)
│   ├── missions/         (空，待产出)
│   └── html_entities.xlsx (20 KB)
├── util/
│   ├── __init__.py
│   ├── common.py         (7.6 KB)
│   ├── message_util.py   (5.3 KB)
│   ├── story_util.py     (1.2 KB)
│   └── train_visitor_util.py (1.2 KB)
└── img/                  (图片资源)
```

### 依赖关系

StarrailDialog 依赖 StarRailData 仓库，通过 `--repo` 参数指定路径。脚本读取 `TextMap/TextMapCHS.json` 和 `ExcelOutput/`、`Story/` 下的数据，产出 JSONL 格式的语料文件。

---

## 2.3 数据就绪状态

| 检查项 | 状态 |
|---|---|
| StarRailData 已克隆 | ✅（GitLab 镜像，2024-06-17） |
| StarrailDialog 已克隆 | ✅（2024-07-12） |
| 中文 TextMap 已就位 | ✅（TextMapCHS.json，207,357 行） |
| 非中文 TextMap 已清理 | ✅（已删除 25 个文件） |
| ExcelOutput 已就位 | ✅（980 个 JSON 文件） |
| Story 已就位 | ✅（3 个子目录） |
| Config 已就位 | ✅（82 个文件/子目录） |