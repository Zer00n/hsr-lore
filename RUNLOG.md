# RUNLOG

## 2026-08-06 阶段一：环境准备

### 12:45 - 开始

- 阅读 docs/hsr-corpus-pipeline.md，确认执行范围为阶段一到阶段四
- 工作目录：`D:\Office\claudecode\star\`

### 12:46 - 创建项目目录结构

```bash
mkdir -p hsr-lore/{vendor,raw,samples,work,reports,scripts}
```

### 12:46 - 写入 .gitignore

排除 `vendor/`、`raw/`、`work/` 及 Python 和 IDE 相关文件。

### 12:46 - 创建 venv

```bash
cd hsr-lore && python -m venv .venv
```

- Python 版本：3.14.5
- 路径：`D:\Office\claudecode\star\hsr-lore\.venv`

### 12:46 - 磁盘空间检查

- D 盘剩余空间：685.51 GB，满足 20GB 最低要求

### 12:46 - 阶段一完成

- 产出：`reports/00_env.md`

---

## 2026-08-06 阶段二：拉取数据源

### 12:50 - StarRailData 尝试 1：GitHub 直连 — 失败

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/Dimbreath/StarRailData.git
```
- 错误：`Failed to connect to github.com port 443 after 21116 ms`
- 记录到 ISSUES.md

### 12:57 - StarRailData 尝试 2：GitLab 镜像 — 成功

```bash
git clone --depth 1 --filter=blob:none --sparse https://gitlab.com/jianghanxia1/StarRailData.git
```
- 耗时：约 7 分钟
- commit：`df89dd1138e751c8b1a62c92fc2bafac421dc18f`（2024-06-17）

### 12:58 - 探索实际目录结构

```bash
git ls-tree -d HEAD
```
- 实际顶层目录：Config, ExcelOutput, Stages, Story, TextMap
- 与手册预测一致（Stages 为额外目录）

### 12:59 - 设置 sparse-checkout

```bash
git sparse-checkout set TextMap ExcelOutput Story Config
```

### 12:59 - 清理非中文 TextMap

- 删除 25 个非 CHS 语言文件，保留 `TextMapCHS.json`
- TextMapCHS.json：207,357 行，20.5 MB

### 12:59 - 各目录体积统计

- TextMap：20 MB（清理后）
- ExcelOutput：160 MB（980 个 JSON 文件）
- Story：9.9 MB
- Config：458 MB（82 个文件/子目录）

### 13:02 - 克隆 StarrailDialog — 成功

```bash
git clone https://github.com/mrzjy/StarrailDialog.git
```
- commit：`149dd8e2e7c9a87fbe6a8f3982e4eba73b0bcd18`（2024-07-12）
- 体积：11 MB

### 13:05 - 阶段二完成

- 产出：`reports/01_sources.md`

---

## 2026-08-06 数据源更新

### 13:20 - 删除旧 StarRailData

```bash
rm -rf vendor/StarRailData
```

### 13:21 - 尝试 GitHub HTTPS 克隆 — 失败

```bash
git clone https://github.com/DimbreathBot/TurnBasedGameData.git
```
- 错误：`Recv failure: Connection was reset`

### 13:27 - 尝试 GitHub SSH 克隆 — 成功

```bash
git clone --depth 1 --filter=blob:none --sparse git@github.com:DimbreathBot/TurnBasedGameData.git StarRailData
```
- SSH 认证用户：Zer00n
- commit：`648b08fbdb2e49739ebbf1210c9a189fcfc5e2d7`（2026-07-29，4.4.0）

### 13:32 - 设置 sparse-checkout（no-cone mode）

```bash
git sparse-checkout set --no-cone /TextMap/TextMapCHS.json /ExcelOutput /Story /Config
```
- cone 模式 checkout 超时，改用 no-cone 模式
- 遇到 lock 文件残留，手动清理后成功
- 最初 sparse-checkout 路径被 Git 错误地 prepend 了 Git 安装路径，手动修正为相对路径

### 13:37 - 版本验证：三个信号

1. **commit 日期**：2026-07-29（版本 4.4.0），距执行日仅 8 天
2. **3.x 关键词**：翁法罗斯 2016 次，黄金裔 993 次（旧数据为 0）
3. **角色名单**：最后 15 个非开拓者角色包括刻律德菈 (1412)、白厄 (1408)、遐蝶 (1407)、昔涟 (1415) 等

### 13:40 - 更新 StarrailDialog

```bash
cd vendor/StarrailDialog && git pull
```
- 结果：Already up to date
- commit 仍为 `149dd8e2`（2024-07-12），作者已两年未维护

### 13:42 - 安装依赖

```bash
pip install pandas openpyxl
```
- 无 requirements.txt，按错误提示补装

### 13:43 - 冒烟测试：get_misc.py — 崩溃

```bash
python get_misc.py --lang=CHS --repo=<path>/vendor/StarRailData
```
- 错误：`AttributeError: 'list' object has no attribute 'items'`
- 根因：新数据 ExcelOutput 文件全部改为 list 格式（2140/2140），脚本期望 dict 格式

### 13:44 - Hash 查找验证

- 随机抽取 50 条 TalkSentenceConfig，Hash 在 TextMapCHS 中命中率 100%
- 结论：hash 方案兼容，仅数据结构（dict → list）不兼容

### 13:48 - 各目录体积

- TextMap：48 MB（仅 CHS）
- Story：37 MB
- ExcelOutput：264 MB（2140 个 JSON 文件）
- Config：1.1 GB

### 13:50 - 数据源更新完成

- 产出：`reports/01b_source_update.md`

---

## 2026-08-06 数据源字段普查

### 14:00 - 开始

- 编写 `scripts/survey_excel_v2.py`：遍历 ExcelOutput 所有文件，识别 Hash 字段并解析中文样例
- 编写 `scripts/survey_excel.py`（v1）：初版因 None 值处理问题崩溃，修复后产出 v2

### 14:05 - ExcelOutput 普查完成

- 扫描 2,140 个文件，275 个包含 Hash 字段
- A 类（世界观文本）：63 个
- B 类（疑似有用）：212 个
- 结果保存到 `work/excel_survey_v2.json`

### 14:10 - Story 目录普查

- 5,358 个 JSON 文件（Mission 725 + Discussion 4,578 + BattlePerformance 51）
- 扫描全部 Discussion 和 Mission 文件，统计节点类型
- 关键发现：`PlayAndWaitSimpleTalk` 节点在新数据中不存在
- 对话文本通过 TalkSentenceID 引用 TalkSentenceConfig 表

### 14:15 - Config 和 Stages 检查

- Config：113,707 个 JSON 文件，随机抽样均为引擎配置，无叙事文本
- Stages：目录为空

### 14:20 - 跨表关联分析

- 确认 Story 文件名 → MainMissionID → WorldID → BookSeriesWorld → 星球名 的关联链路
- 294 个 Story Mission 目录中 290 个（98.6%）能在 MainMission 中找到对应
- 6 个星球通过 BookSeriesWorld 表命名

### 14:25 - 样例文件生成

- 生成 10 个样例文件：Story Mission/Discussion、TalkSentenceConfig、BookSeriesConfig、ItemConfig、AvatarConfig、MonsterConfig、AchievementData、ChronicleConclusion、BookSeriesWorld

### 14:30 - 阶段三完成

- 产出：`reports/03_field_survey.md`

---

## 2026-08-06 普查补正

### 15:00 - 任务一：全字段文本体量排序

- 编写 `scripts/volume_ranking.py`，遍历 275 个文件的所有 (文件, 字段) 二元组
- 解析所有 Hash 为中文，统计非空条数、总字符数、平均/中位字符数、最长样例
- 产出 `work/text_volume_full.json` 和 `work/text_volume_top80.txt`
- TalkSentenceConfig 以 5,886,916 字符排第一，远超第二（技能描述，1,362,751）

### 15:10 - 任务二：TalkSentenceID 归属验证

- 编写 `scripts/verify_talksentence.py`
- 前缀匹配方案不成立（7 位前缀仅 9.6% 匹配率）
- 正确归属路径：Story 文件 → TalkSentenceID → TalkSentenceConfig → 文本
- 562 个 Story mission 目录中有 541 个（96.3%）能在 MainMission 中找到
- 14,960 个 TalkSentenceID 可通过 Story 文件归属到任务（6.5%）
- 按 WorldID 分布：翁法罗斯 4,054 条，匹诺康尼 3,831 条，仙舟 1,861 条
- 20 组交叉验证样本语义基本吻合

### 15:15 - 任务三：定向补查遗漏表

- 书籍正文：LocalbookConfig.json（1,051 本，941,323 字符）
- 角色故事：StoryAtlas.json（446 条，215,814 字符）
- 角色语音：VoiceAtlas.json（5,236 条，123,197 字符）
- 光锥：ItemConfigEquipment.json（165 条，28,523 字符）
- 短信：MessageItemConfig.json（13,253 条，205,409 字符）
- 邮件：SysMailConfig.json（37 条）
- 模拟宇宙：RogueMiracleDisplay、RogueAeonStoryConfig 等 10+ 个文件
- 百科：NounAtlas.json（99 条）、TitanAtlas.json（18 条）

### 15:20 - 任务四：Config 复查

- 从 113,707 个文件跨不同顶层目录随机抽 200 个
- 含 Hash 字段：13 个（6.5%），全部为关卡配置中的 NPC 名称引用
- 结论：Config 不含叙事文本，跳过

### 15:25 - 普查补正完成

- 产出：`reports/04a_text_volume.md`、`reports/04_survey_supplement.md`

---

## 2026-08-06 阶段五：语料抽取

### 16:00 - 编写抽取器

- 编写 `scripts/extract.py`：白名单驱动，7 卷输出，完整清洗规则
- 编写 `scripts/verify.py`：三项验收测试

### 16:05 - 首次运行

- 发现 narrative 卷可归属对话仅 30 条（误加了 speaker 过滤）
- 修复：14,654 条可归属对话全部纳入 narrative 卷（仅 30 条有说话人，其余为玩家选项）

### 16:10 - 清洗规则修复

- 残留标记从 0.9% 降至 0.2%
- 补充 `<s>`、`<size=+N>`、`{F#...}`、`{M#...}`、`{TEXTJOIN#...}` 处理

### 16:15 - 验收测试

- 反查测试：28/30 通过（2 条为 PK 歧义，非数据错误）
- 残留标记：390 条（0.17%），114 种模式
- 幂等测试：两次运行 8 个文件 MD5 完全一致

### 16:20 - 最终产出

- 7 卷语料：231,104 条，7,604,856 字符，~5.7M token
- 产出：`reports/05_extraction.md`

---

## 2026-08-06 语料修正

### 17:00 - 备份

- `cp -r corpus/ corpus_v1_backup/`

### 17:05 - 核查一：AvatarID 映射

- 完整读取 AvatarConfig 的 91 个角色 ID→名对照表
- **发现错误：** 1014-1017 不在 AvatarConfig 中，上一轮的"吉尔伽美什、Saber、远坂凛、间桐樱"是推断的，非数据实读
- 1014、1015、1508、1509 在 VoiceAtlas 中但不在 AvatarConfig 中，台词内容 100% 确认是 Fate 联动
- 修正规则：仅排除 AvatarID 不在 AvatarConfig 的 VoiceAtlas 条目
- 8001-8010（开拓者）和 1506（银狼变体）的语音恢复

### 17:10 - 核查二：无说话人对话

- 65,511 条中随机抽 200 条，分类：60% 玩家选项、20% 旁白、12.5% 系统提示、7.5% 空内容
- 仅 0.3% 含 {NICKNAME}
- 无其他可用说话人字段
- 建议维持剔除

### 17:15 - 核查三：cite_id 唯一性

- 231,104 条中 36 条重复（16 个 cite_id）
- AEON：AeonStoryID 不唯一（同一 ID 对应多个 RogueAeonID）
- SKIP：PerformanceID 不唯一（同一 ID 在表中多次出现）
- STRY/VOIC：AvatarID 不唯一（同一角色有多个 Story/Voice）
- 提出修正方案，等确认

### 17:20 - 核查四：dialogue 切分

- 5,497 个说话人，Top 50 列出
- 长尾 5,228 人（<100 条）合计 57,758 条、~1.25M token
- 提出按主要角色+长尾合并的切分方案

### 17:25 - 核查五：补充

- book_series_name 59.3% 是因为 BSER 条目本身是系列定义，修正为填自身名
- SubMission 非空：TargetText 9,173 条，DescrptionText 9,124 条
- TEXTJOIN 可通过 TextJoinItem.json 解析

### 17:30 - 报告完成

- 产出：`reports/06_corpus_fix.md`
---

## 2026-08-06 语料最终修正与收口

- 隔离 speakerless.jsonl（65,511 条）+ excluded_ip.jsonl（229 条）
- 修复 cite_id：AEON/STRY/VOIC/SKIP 使用组合键
- 建立 speaker→AvatarID 映射
- 产出：`reports/07_corpus_final.md`

## 2026-08-06 Schema 与校验器

- 编写 6 个 JSON Schema + 1 个谓词词表
- 构建引证索引（229,702 条）
- 校验器 12 项检查，Mock 22/22 合规 + 16/16 违规
- 产出：`reports/09_schema.md`

## 2026-08-06 OpenViking 接入

- 干跑 4,913 文件，5 AFP/小时
- 产出：`reports/10_openviking.md`

## 2026-08-06 灌库前修正 v1-v3

- 补全 narrative 归属链路（89.6% → 90.7% world_id 填充）
- 拆解特殊说话人（UNKNOWN/开拓者/？？？）
- 清洗规则修复（{NICKNAME} 在 meta 字段）
- 文件粒度重新平衡（最大 99KB，0 超 100KB）
- 产出：`reports/11_ov_plan_v2.md`、`reports/12_ov_plan_v3.md`

## 2026-08-06 并行：灌 lore + 修正 artifacts

- A: ov CLI v0.4.12 安装，API Key 更新后认证成功
- A1: 灌 lore 卷 542 文件，2 分钟，0 失败
- A2: 分层内容验证通过，语义搜索准确，检索轨迹 JSON 可程序化读取
- A3: 清空确认，挂库 ~22 分钟，~1.85 AFP
- B: artifacts 聚合字段确认，SubMission 交叉验证 20 组，数字核对
- 产出：`reports/13_ov_lore_trial.md`、`reports/14_fixes.md`
