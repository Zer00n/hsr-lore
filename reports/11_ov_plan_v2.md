# 灌库前四项修正

## 一、narrative 归属链路补全

### 1.1 SubMission 关联

SubMission 表只有 3 个字段：`SubMissionID`、`TargetText`、`DescrptionText`，无直接的 `MainMissionID` 字段。通过 **SubMissionID 前 7 位前缀匹配 MainMissionID**：

| 指标 | 值 |
|---|---|
| SubMission 总数 | 14,584 |
| 可归属到 MainMission | 14,534（99.7%） |
| 无法归属 | 50（ID 前缀不匹配） |

归属后链路：`SubMissionID → MainMissionID → WorldID → BookSeriesWorld → 星球名`。

### 1.2 其他表归属

| 表 | 可归属率 | 说明 |
|---|---|---|
| PerformanceSkipOverride | 97.6%（3,799/3,894） | PerformanceID 前 7 位 → MainMissionID |
| ChronicleConclusion | 100%（428/428） | MissionID 直接匹配 |

### 1.3 修复后 narrative 卷 world_id 填充率

| 指标 | 修复前 | 修复后 |
|---|---|---|
| 有 world_id 的条目 | ~53% | **89.6%**（33,514/37,408） |
| 无 world_id（world-0） | ~17,673 | **3,894**（PerformanceSkipOverride 中 95 条无法归属 + MainMission 自身无 world_id 的条目） |

**world_id 分布：**

| WorldID | 星球 | 条目数 |
|---|---|---|
| 101 | 空间站「黑塔」 | 2,655 |
| 201 | 雅利洛-Ⅵ | 2,847 |
| 301 | 仙舟「罗浮」 | 5,470 |
| 401 | 匹诺康尼 | 8,520 |
| 501 | 翁法罗斯 | 8,711 |
| 601 | （新世界） | 5,311 |

## 二、dialogue 特殊说话人拆解

### 2.1 UNKNOWN（13,287 条）

**根因：不是字面字符串 UNKNOWN，是空字符串被 plan.py 的 `or 'UNKNOWN'` 兜底成了 UNKNOWN。**

这 13,287 条来自 MessageItemConfig（MSG）和 MessageContactsConfig（CTAC），它们的 meta 中有 `sender` 字段而非 `speaker` 字段。修复后 plan.py 使用 `sender` 字段作为归组依据。

### 2.2 {NICKNAME}（4,867 条）

**开拓者（主角）本人的台词。** 修复后：
- speaker 替换为「开拓者」
- 单独成文件 `开拓者.md`
- meta 标记 `speaker_type: protagonist`

### 2.3 ？？？（1,653 条）

**剧情中刻意隐藏身份的说话人。** 修复后：
- 保留说话人名「？？？」
- 单独成文件 `？？？.md`
- meta 标记 `speaker_type: anonymous`

## 三、清洗规则覆盖

### 3.1 当前清洗规则作用字段

`clean_text()` 函数仅作用于 `clean` 字段。`title`、`meta` 中的文本字段（名称、标题、系列名、说话人名、任务名等）未经过清洗。

### 3.2 残留模板变量

`{NICKNAME}` 出现在书籍系列名中（如"NICKNAME小海豹战队选手变动公告"），原因是 `BookSeriesConfig` 的 `BookSeries` 字段值在 TextMap 中存储为 `{NICKNAME}xxx`，而 `resolve()` 函数直接返回原始 TextMap 值，未通过 `clean_text()` 处理。

### 3.3 修复方案

1. 在 `resolve()` 函数中增加模板变量替换：`{NICKNAME}` → 开拓者，`{M#...}`、`{F#...}` 处理
2. 在 `make_entry()` 中，title 字段也经过清洗
3. 规则执行顺序：模板变量替换 → 标签剥离（当前顺序已正确，但 resolve 未包含模板替换）

### 3.4 修复后统计

- 书籍系列名中的 `{NICKNAME}` 已全部替换为"开拓者"
- 修复后重新生成语料，cite_id 唯一性重新确认：229,702 条全部唯一 ✅
- 残留标记：47 条（0.02%），无新增

## 四、文件粒度重新平衡

### 4.1 规则

| 规则 | 值 |
|---|---|
| 单文件体积上限 | 100 KB |
| 单文件条目数上限 | 500 |
| 单文件体积下限参考 | 2 KB（低于此值考虑合并，但不强制） |

### 4.2 修正后分布

| 指标 | 修正前 | 修正后 |
|---|---|---|
| 总文件数 | 4,913 | **4,560** |
| 总大小 | 27.4 MB | 28.9 MB |
| 最大文件 | 2,499 KB | **102 KB** |
| 平均文件 | 5,845 B | 6,655 B |

### 4.3 各卷分布

| 卷 | 文件数 | 大小 | 说明 |
|---|---|---|---|
| lore | 570 | 0.2 MB | 一条一文件，无需切分 |
| books | 1,772 | 2.3 MB | 一本一文件，无需切分 |
| characters | 259 | 1.1 MB | 按角色聚合，无需切分 |
| narrative | 1,422 | 3.9 MB | 按星球/任务聚合，大任务切分 |
| dialogue | 515 | 19.7 MB | 按说话人聚合，大文件切分 |
| artifacts | 16 | 1.3 MB | 按类别聚合，大文件切分 |
| rogue | 6 | 0.4 MB | 按类别聚合，大文件切分 |

### 4.4 超过 100KB 的文件

14 个文件在 102KB 左右（最大 102,442 bytes），因最后一个条目超出阈值导致。超出量 < 3KB，在可接受范围内。

### 4.5 阈值检查

- 4,560 < 15,000（安全阈值）✅
- 4,560 < 40,000（计费阈值）✅
- 费率：5 AFP/小时

## 5. 交付清单

| 文件 | 变更 |
|---|---|
| `scripts/extract.py` | SubMission 归属链路 |
| `scripts/openviking/plan.py` | 说话人分类 + 文件大小限制 |
| `work/ov_plan.json` | 更新干跑结果 |
| `reports/11_ov_plan_v2.md` | 本报告 |