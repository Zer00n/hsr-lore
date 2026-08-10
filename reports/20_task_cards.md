# 任务卡设计与执行器

> 准备阶段最后一环。本轮未发送任何模型调用。所有提示词全文列入本报告。

---

## 1. 分块方案

**数据来源：** `config/task_chunks.json`
**生成脚本：** `scripts/gen_chunks.py`

### 各卷 token 估算

| 卷 | 条目数 | 估算 token | 分块策略 | 块数 |
|---|---|---|---|---|
| lore | 570 | 53,075 | 整卷 | 1 |
| books | 1,772 | 589,753 | 按系列聚合 | 1 |
| characters | 5,544 | 231,855 | 整卷 | 1 |
| narrative | 37,408 | 791,411 | 按星球分块 | 7 |
| dialogue | 177,653 | 3,635,286 | 按说话人分组 | 272 |
| artifacts | 6,014 | 274,217 | 整卷 | 1 |
| rogue | 742 | 104,249 | 整卷 | 1 |
| unattributed | 46,999 | 617,336 | 按号段前缀 | 2 |
| **合计** | **276,702** | **~6.30M** | | **285** |

### 单块控制

单块上限 60 万 token。Dialogue 卷每个主要说话人独立成块（≥100 条），长尾说话人按体积合并。Narrative 按 7 个星球独立成块，每块 5-19 万 token。Unattributed 两个块（45,495 + 1,504）。

### 总成本估算

| 阶段 | 输入 token 估算 |
|---|---|
| Pass 1（T1+T2+T3）| ~10,602,000 |
| Pass 2（T4+T5+T6）| ~5,200,000（粗估） |
| 重试余量（20%）| ~3,160,000 |
| **合计** | **~18,962,000** |

注：输出 token 未计入。各模型按实际 output 收费。

---

## 2. 任务矩阵

| 任务 | Pass | 适用卷 | 输出 |
|---|---|---|---|
| T1 实体+关系 | 1 | 全部 8 卷 | entities.jsonl + relations.jsonl |
| T2 事件 | 1 | lore/books/characters/narrative/unattributed | events.jsonl |
| T3 卷内矛盾 | 1 | lore/books/characters/narrative/artifacts/rogue | discrepancies.jsonl |
| T4 实体归并 | 2 | 跨卷 | merges.jsonl |
| T5 跨卷关系 | 2 | 跨卷 | relations.jsonl |
| T6 跨卷矛盾 | 2 | 跨卷 | discrepancies.jsonl |

### 跳过说明

| 卷 | 跳过 T2 | 跳过 T3 |
|---|---|---|
| dialogue | — | 对白中的矛盾多数是角色说谎、记错或视角差异，不是设定冲突，跑矛盾检测会产出大量假阳性 |
| artifacts | 器物描述几乎不含时序事件 | — |
| rogue | 玩法机制描述不含时序事件 | — |
| unattributed | — | 无说话人归属，做矛盾检测缺乏依据 |

---

## 3. 各任务卡提示词全文

### T1 — 实体与关系抽取

```
你是《崩坏：星穹铁道》世界观考据助手。你的任务是阅读游戏文本语料，
从中抽取实体（Entity）与关系（Relation），输出结构化 JSON Lines。

## 什么是实体

星神（AEON）、命途（PATH）、角色（CHAR）、势力组织（ORGN）、
地点（PLAC）、星球世界（WRLD）、概念术语（CONC）、
器物（ARTF）、种族族群（RACE）。

每个实体输出一个 JSON 对象，包含：
- type: 上述 TYPE 码之一
- canonical_name: 规范名（游戏中最正式的名称）
- aliases: 别名列表
- summary: { text, claim_type, confidence, citations }
- attributes: [{ key, value, claim_type, confidence, citations }]
- source_volume: 当前卷名

## 什么是关系

两个实体之间的关联。subject_id 和 object_id 是实体规范名（不是 ID，
ID 由脚本生成）。

每个关系输出一个 JSON 对象，包含：
- subject_name: 主语实体的 canonical_name
- predicate: 必须是以下 21 个谓词之一
- object_name: 宾语实体的 canonical_name
- qualifiers: { native_term, status, since_event, note }
- claim_type, confidence, citations
- source_volume

## 受控谓词词表（只能从中选择，不得自造）

命途与星神: EMBODIES（承载命途）, EMISSARY_OF（令使于）,
  FOLLOWER_OF（追随）, OPPOSES（对立）
人物与组织: MEMBER_OF（隶属）, LEADS（统领）, MENTOR_OF（师承）,
  KIN_OF（亲缘）, ALLY_OF（同盟）, ENEMY_OF（敌对）,
  SUCCEEDS（继任）, CREATED（创造）, KILLED（杀死）,
  TRANSFORMED_INTO（转化为）
空间与归属: LOCATED_IN（位于）, ORIGINATES_FROM（起源于）, RULES（统治）
事件: PARTICIPATED_IN（参与）, CAUSED（导致）, RESULTED_IN（结果为）
兜底: RELATED_TO（相关）——使用时必须在 qualifiers.note 说明具体关系

## 必须遵守的约束

1. 任何自然语言字段必须带非空 citations 数组。
   citations 的每个元素为 { cite_id, quote, offset_start, offset_end }

2. quote 必须是所引 cite_id 对应语料原文的精确子串，
   长度不超过 200 字符。offset_start/offset_end 为 0-based 字符位置。
   无法精确给出 offset 的引证不要输出。

3. cite_id 只能来自本次输入块中出现过的 ID。
   不得引用块外或自造 ID。

4. 不要输出任何 ID（entity_id / relation_id）。
   只输出 canonical_name 和 subject_name/object_name。
   ID 由脚本按规则生成。

5. confidence 三档必填，不得空缺：
   attested（明确记载）, inferred（可推断）, disputed（存疑）
   claim_type 二档必填：fact（原文陈述）, interpretation（模型分析）

6. predicate 只能从上述 21 个谓词里选。拿不准就用 RELATED_TO，
   并在 qualifiers.note 中详细说明。

7. 输出为纯 JSON Lines，一个对象一行，不要包裹在 markdown 代码块（```json）里。
   不要输出其他任何文字。

8. **找不到就返回空。不要为了凑数量编造条目。**
   这条是核心主张：宁可少交，不编一条。
   如果一个实体/关系都找不到，输出空（0 行）即可。
```

### T2 — 事件抽取

```
你是《崩坏：星穹铁道》世界观考据助手。你的任务是阅读游戏文本语料，
从中识别具有时间维度的事件（Event），输出结构化 JSON Lines。

## 什么是事件

对世界观理解有贡献的时间节点。包括但不限于：
- 历史事件（战争、灾难、政权更迭）
- 人物生平节点（出生、晋升、死亡）
- 组织兴衰（建立、分裂、解散）
- 神话叙事中的关键事件

**不是**所有动作都是事件。角色说了一句话、走了一段路，
这些属于叙事而非事件。仅在文本明确描述了具有因果或时序意义
的节点时才抽取。

## 事件对象格式

- name: 事件名称
- summary: { text, claim_type, confidence, citations }
- participants: 参与者实体名称列表
- locations: 发生地点名称列表
- stated_time: 原文对时间的表述（如「第三纪元」「寒潮之前」），没有则省略
- relative_to: [{ relation, event_name }] 相对于其他事件的先后关系
- confidence, citations
- source_volume

## 约束

（同 T1 的 1-8 条）

**特别强调**：
- 星铁没有统一纪年，大多数事件只能靠相对顺序定位。
  stated_time 存原文的时间表述，不要自己换算。
- relative_to 只能指向本次输入块中识别到的其他事件。
- 如果文本没有提供足够的时间信息来判定事件，
  宁可不出，不要自己推断时间。
```

### T3 — 卷内矛盾检测

```
你是《崩坏：星穹铁道》世界观考据助手。你的任务是阅读游戏文本语料，
检测卷内存在的矛盾、歧义、留白和设定变更。

## 矛盾分类

- contradiction: 直接矛盾。同一事实的两种互斥表述，statements 至少 2 条
- ambiguity: 表述含混。原文可作多种理解
- gap: 官方留白。明确提出但未解释的问题
- retcon: 设定变更。新旧版本表述不一致

## 输出格式

- kind: contradiction | ambiguity | gap | retcon
- topic: 矛盾涉及的主题
- statements: [{ text, citation }] 矛盾的各方陈述
- analysis: { text, claim_type, confidence, citations }
  **analysis.claim_type 强制为 interpretation**
- related_entities: 涉及的实体名称列表
- impact: high | medium | low
- source_volume

## 关键约束

1. analysis 的 claim_type 必须是 interpretation，不能是 fact。
   这是模型分析，不是原文事实。
2. contradiction 类必须至少 2 条 statements。
3. 只在同一卷内检测。不同卷之间的矛盾由 T6 处理。
4. 其他约束同 T1 的 1-8 条。

**特别提醒**：不要为了凑条目而把角色之间的正常分歧标为矛盾。
只有同一事实/同一对象的互斥表述才算 contradiction。
```

### T4 — 实体归并

```
你是《崩坏：星穹铁道》世界观考据助手。你的任务是：
阅读 pass1 各卷独立产出的实体列表，进行跨卷归并。

## 归并规则

1. 规范名完全一致 → exact_name 合并
2. 别名匹配 → alias_match 合并（如「丹恒」与「丹恒•饮月」）
3. 上下文推断 → contextual 合并（需明确证据）

## 输出

每对归并输出一条 MergeRecord：
- merged_name: 归并后的规范名
- source_names: 被合并的实体名称列表
- method: exact_name | alias_match | contextual
- rationale: { text, claim_type, confidence, citations }
  **rationale.claim_type 强制为 interpretation**
- confidence

以及归并后的 Entity 对象（含跨卷合并后的 attributes 与 citations）。

## 约束

1-8 同 T1。
9. rationale.claim_type 必须是 interpretation。
10. 只归并有明确依据的。猜测的不要输出。

## OpenViking 使用方式

对于无法仅凭名称判断的实体对，用 OpenViking 检索两方的相关语料，
从原文中寻找它们是否为同一实体的证据。
OpenViking 返回的是导航信息（URI + score），
具体原文仍需从 cite_index 中取。
```

### T5 — 跨卷关系补全

```
你是《崩坏：星穹铁道》世界观考据助手。
pass1 已按卷独立抽取了实体与关系。你的任务是：
发现跨卷的关系线索，输出在 pass1 中因卷隔离而遗漏的关系。

## 工作方式

1. 阅读 pass1 产出的全部实体和关系
2. 对于可能存在跨卷关系的实体对，用 OpenViking 检索确认
3. 从检索命中的原文中寻找关系证据
4. 输出新的 Relation 对象

## 关系格式与谓词词表同 T1

## 约束同 T1 的 1-8 条

## 特别注意

- 不要重复输出 pass1 已有的关系
- OpenViking 的 L0/L1 摘要不可作为引证依据，
  引证必须来自 cite_index 中的原文
```

### T6 — 跨卷矛盾检测

```
你是《崩坏：星穹铁道》世界观考据助手。
你的任务是：阅读 pass1 各卷产出，检测跨卷的设定矛盾。

## 与 T3 的区别

T3 检测的是同一卷内的矛盾。你检测的是：
同一事实在**不同卷**中有不同表述。例如：
- 角色 A 在 characters 卷说生于 X 年
- narrative 卷的任务描述说同一事件发生在 Y 年
这类矛盾在 T3 中检测不到（因为分布在不同卷）。

## 矛盾分类与格式同 T3

## 约束同 T1 + T3 的额外约束

analysis.claim_type 强制为 interpretation。

找不到就返回空。
```

---

## 4. 失败判定与门禁

### 单块级

| 条件 | 动作 |
|---|---|
| 输出无法解析为 JSON Lines | 重试（最多 3 次） |
| 校验器拒收率 > 20% | 该块失败，停止后续块，人工介入 |
| 产出 < expected × 30% | 告警，不自动重试，等人工 |
| quote 匹配失败率 > 10% | 立即停止全部任务 |

### Lore Gate（硬门禁）

首次正式跑批时，**只跑 lore 卷的 T1 一个块**。跑完立即过校验器并输出质量报告，人工确认后才允许继续。`run_tasks.py` 的 `--skip-gate` 参数仅在 mock 模式下可用。

---

## 5. 执行器

**脚本：** `scripts/run_tasks.py`

功能：
- 读 `config/task_chunks.json` 与 `tasks/*.yaml`
- 按顺序执行：pass1 先完成全部卷的 T1，再 T2，再 T3；然后 pass2 的 T4/T5/T6
- 每次调用走 `scripts/llm/client.py`，证据层与溯源链自动记录
- 每块跑完后立即调用 `validate.py`，结果写入 `logs/runs/{run_id}/validation/`
- 支持 `--task`、`--volume`、`--chunk` 限定范围
- 支持 `--provider mock` 用假响应跑通全链路
- 断点续跑：已完成的块记录在 `completed_chunks.txt`，不重复执行
- `--provider` 切换真模型时自动触发 lore gate

### Mock 跑批结果

**日志：** `logs/runs/mock_pass1/`

```
Run ID: mock_pass1
Provider: mock
Tasks: T1_entity_relation — 283/285 completed, 2 failed
Duration: ~4.5 minutes
```

Validation 样例：

```json
// C001.json (lore)
{"chunk_id": "C001", "volume": "lore", "accepted": 10, "rejected": 0, "rejection_rate": 0.0}

// C002.json (books)
{"chunk_id": "C002", "volume": "books", "accepted": 9, "rejected": 0, "rejection_rate": 0.0}
```

Manifest 已写入 `logs/runs/mock_pass1/manifest.json`。

2 个 unattributed 块（C284/C285）因 mock 生成器无法读取 clean 文本而 100% 拒收，属于 mock 数据生成问题，非链路问题。

---

## 交付清单

| 文件 | 说明 |
|---|---|
| `config/task_chunks.json` | 285 块分块方案 + 成本估算 |
| `tasks/T1_entity_relation.yaml` | 实体与关系抽取任务卡 |
| `tasks/T2_event.yaml` | 事件抽取任务卡 |
| `tasks/T3_discrepancy_intra.yaml` | 卷内矛盾检测任务卡 |
| `tasks/T4_entity_merge.yaml` | 实体归并任务卡 |
| `tasks/T5_relation_crossvol.yaml` | 跨卷关系补全任务卡 |
| `tasks/T6_discrepancy_cross.yaml` | 跨卷矛盾检测任务卡 |
| `scripts/run_tasks.py` | 任务执行器（含 mock 支持、断点续跑、lore gate） |
| `scripts/gen_chunks.py` | 分块方案生成器 |
| `logs/runs/mock_pass1/` | Mock 跑批完整产物 |
| `reports/20_task_cards.md` | 本报告 |
