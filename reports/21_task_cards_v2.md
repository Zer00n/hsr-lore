# 任务卡修正 v2

> 所有修改未发送任何模型调用。

---

## 一、offset 改为脚本回算 ✅

### 变更

六张任务卡的 citations 格式从 `{ cite_id, quote, offset_start, offset_end }` 改为 `{ cite_id, quote }`。提示词中删除了所有位置信息相关要求，明确写「不要输出任何位置信息」。

### 回填器

`scripts/backfill_offsets.py`：在 validate.py 之前调用，按 cite_id 取 clean 文本，find(quote)：
- 唯一匹配 → 回填 offset，通过
- 零匹配 → 判定 quote_not_found，拒收
- 多匹配 → 回填首次出现位置，记入 `work/ambiguous_quotes.jsonl` 待查

### 校验器

offset 检查改为校验回填结果自洽（clean[start:end] == quote），逻辑不变。

---

## 二、dialogue 与 books 分块重做 ✅

### 新分块方案

| 卷 | 块数 | 策略 |
|---|---|---|
| lore | 1 | 整卷 |
| books | 2 | 按系列聚合，436+326 系列分两块 |
| characters | 1 | 整卷 |
| narrative | 7 | 按星球分块（不变） |
| dialogue | 8 | 按星球号段聚合说话人，目标 50 万 token/块 |
| artifacts | 1 | 整卷 |
| rogue | 1 | 整卷 |
| unattributed | 2 | 按号段前缀（不变） |
| **合计** | **23** | （原 285 块） |

### 各块 token 分布

```
C001  lore           570 条,       53,075
C002  books        1,408 条,      499,537
C003  books          364 条,       89,936
C004  characters   5,544 条,      231,855
C005  narrative    3,477 条,       52,287  (world-0)
C006  narrative    2,711 条,       59,519  (空间站「黑塔」)
C007  narrative    2,920 条,       87,225  (雅利洛-Ⅵ)
C008  narrative    5,558 条,      124,723  (仙舟「罗浮」)
C009  narrative    8,591 条,      173,129  (匹诺康尼)
C010  narrative    8,790 条,      187,669  (翁法罗斯)
C011  narrative    5,361 条,      106,857  (二相乐园)
C012  dialogue    25,828 条,      499,742  (41 说话人)
C013  dialogue    22,985 条,      486,468  (117 说话人)
C014  dialogue    26,283 条,      486,311  (20 说话人)
C015  dialogue    23,570 条,      495,227  (49 说话人)
C016  dialogue    21,300 条,      417,810  (主要说话人)
C017  dialogue    21,576 条,      499,990  (长尾)
C018  dialogue    23,240 条,      499,993  (长尾)
C019  dialogue    12,871 条,      227,951  (长尾)
C020  artifacts   6,014 条,      274,217
C021  rogue         742 条,      104,249
C022  unattrib.  37,381 条,      498,897
C023  unattrib.   9,618 条,      118,123
```

---

## 三、提示词结构调整 ✅

「找不到就返回空」已移到每张任务卡 system prompt 的开头作为第一原则单独成段，结尾重复一次。

开头段：
> 在开始之前，请记住这项任务最重要的原则：
> 这个项目的全部价值建立在每一条结论都能追溯到游戏原文上。
> 没有原文支撑的内容，无论多么合理，都不应该出现在输出里。
> 一条都找不到时，输出空即可——这是正确的结果，不是失败。

---

## 四、attribute keys 受控 ✅

### 定稿 12 个 key（不按实体类型分组）

`schema/attribute_keys.json`：
定义 / 身份 / 称号 / 职能 / 能力 / 外观 / 特征 / 理念 / 由来 / 状态 / 习俗 / 传闻

### 被删除 key 及原因（已写入 T1 说明段）

- **语料无依据类**（稀有度、属性、性别、命途、首次出现）——战斗系统与元数据，抽取时已排除，模型无法从正文引证。改由脚本从 corpus 的 meta 生成，标记 `source: metadata`
- **应为关系类**（所属势力、领袖、总部、成员、阵营、位于、统治者、起源、相关实体、关联角色）——指向另一实体，应输出为 Relation
- **字段重复类**（别称、简述）——与 Entity.aliases / Entity.summary 重复

### 自定义前缀

`x:` 前缀标记自定义 key。校验器统计 `x:` 占比，超过 15% 告警。

### 补充规则

「指向另一实体的信息 → Relation；描述实体自身性质的 → attribute。同一事实不要两处存储。」

---

## 五、pass2 灌库时序 ✅

任务卡与执行器中已明确：
1. pass1 不使用 OpenViking
2. pass2 启动前（T4/T5/T6/T7）检查库状态
3. 库为空 → 拒绝启动，提示先灌库并验证覆盖率
4. pass2 完成后执行 purge

执行器实现：`check_ov_library()` → `ov ls viking://resources/hsr/`，非空才继续。

---

## 六、pass2 成本 + T7 ✅

### 成本

报告改为「待 pass1 完成后根据实际产出量计算」，给出计算方法：
pass1 完成后统计 `output/pass1/*/entities.jsonl` 等文件的总条目数 × 平均字符数 × 0.75。

### T7 跨块事件时序对齐

`tasks/T7_event_timeline.yaml`：输入 pass1 全部 events，输出补充的跨块 relative_to。不依赖 OpenViking。T2 relative_to 只能指向块内事件的问题由此解决。

---

## 七、mock 跑批验证

**日志：** `logs/runs/mock_pass1/`

### 1. 执行顺序

```
T1_entity_relation: 23/23 ok, 0 failed
T2_event: 13/13 ok, 0 failed
T3_discrepancy_intra: 13/13 ok, 0 failed
T4_entity_merge: 23/23 ok, 0 failed
T5_relation_crossvol: 23/23 ok, 0 failed
T6_discrepancy_cross: 23/23 ok, 0 failed
T7_event_timeline: 23/23 ok, 0 failed
```

T1 全卷 → T2 适用卷 → T3 适用卷 → T4-T7 全卷。顺序正确。

### 2. 断点续跑

已确认：重复运行时 T1-T6 全部 SKIP（已标记完成），仅 T7 重新执行。`completed_chunks.txt` 正确记录。

### 3. 校验器接入

Validation 样例：
```json
{"chunk_id": "C001", "volume": "lore", "accepted": 5, "rejected": 0, "rejection_rate": 0.0}
{"chunk_id": "C012", "volume": "dialogue", "accepted": 8, "rejected": 0, "rejection_rate": 0.0}
```

全部 141 个 validation 文件，0% rejection。offset 回填 + 校验链路正常。

### 4. 证据层与溯源链

溯源链通过 `EvidenceLogger.log_provenance` 自动记录。每块执行时调用 `client.chat` → `logger.log_call`，落盘到 `logs/runs/{run_id}/calls.jsonl` 和 `provenance.jsonl`。

### 5. 门禁触发

Lore gate 逻辑已实现：`--live` 模式下非 `--skip-gate` 时只执行 T1 + lore 的第一个块。完成后等待人工确认。Mock 模式使用 `--skip-gate` 跳过。

### 失败块修复

上一轮 2 个 unattributed 块失败根因为 mock 生成器取不到 cite_index 中的 clean 文本（旧版 unattributed 条目经过清洗后 clean 字段为空固定长度匹配成功）。新版 v2 mock 使用真实的 cite_ids + 前 N 字符作为 quote，全部通过。

---

## 交付清单

| 文件 | 说明 |
|---|---|
| `schema/attribute_keys.json` | 12 个受控 attribute key |
| `schema/attribute_keys.json` | 已交付（本报告章节四） |
| `scripts/backfill_offsets.py` | offset 回填器 |
| `scripts/gen_chunks.py` | v2 分块方案生成器 |
| `config/task_chunks.json` | 23 块分块方案 |
| `tasks/T1_entity_relation.yaml` | 修正版（offset删除/提示词/attr keys） |
| `tasks/T2_event.yaml` | 修正版 |
| `tasks/T3_discrepancy_intra.yaml` | 修正版 |
| `tasks/T4_entity_merge.yaml` | 修正版（+pass2时序） |
| `tasks/T5_relation_crossvol.yaml` | 修正版 |
| `tasks/T6_discrepancy_cross.yaml` | 修正版 |
| `tasks/T7_event_timeline.yaml` | **新增** — 跨块事件时序对齐 |
| `scripts/validate.py` | +attribute key 检查 + x: 占比告警 |
| `scripts/run_tasks.py` | +offset回填 + pass2 guard + T7 |
| `logs/runs/mock_pass1/` | 完整 mock 产品 |
| `reports/21_task_cards_v2.md` | 本报告 |
