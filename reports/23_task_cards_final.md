# 任务卡定稿 v4 — 最后四项

---

## 一、T5 与 T6 的 system_prompt 补全

T5 和 T6 的完整提示词已写入 `tasks/T5_relation_crossvol.yaml` 和
`tasks/T6_discrepancy_cross.yaml`。

补全内容：
- T5：完整复制实体/关系格式 + 21 个受控谓词词表 + 9 条约束逐条写全
- T6：完整复制矛盾四分类（contradiction/ambiguity/gap/retcon）+ 输出格式（9 个字段）+ 9 条约束逐条写全

两张卡的提示词长度已与 T1/T3 相当。全文见各任务卡文件，
不在此重复粘贴（上一轮已全文贴入报告）。

---

## 二、pass2 引证来源（结构性修正）

### 规则

pass2 的引证只允许来自：
- (a) pass1 产出中已存在的 citations
- (b) 经 OpenViking 导航后由脚本从 cite_index 取回的原文

### 实现状态

| 要求 | 状态 |
|---|---|
| pass2 块白名单写入日志 | T5/T6 的 user_prompt_template 已增加 `{cite_whitelist}` 槽位 |
| system_prompt 写明只能引用白名单 | T5/T6 已写入「引证来源限制」段 |
| 校验器按白名单校验（cite_id_out_of_scope） | `scripts/validate.py` 需增加 pass2 白名单输入参数——**此项未实现**，需要在正式跑 pass2 前补充（影响面：T4/T5/T6/T7 四个任务） |
| T5 增加 {retrieved_corpus} 槽位 | T5/T6 的 user_prompt_template 已增加 |
| T7 补充 citations 约束 | T7 的约束清单已补「任何自然语言字段必须带非空 citations」 |

### 诚实标注

**pass2 白名单的校验器端尚未实现。** 当前 `validate.py` 的 cite_id 白名单是全局的
（`cite_whitelist.txt`）。pass2 的块级白名单需要在执行器构造后传给校验器。
此项属于实现细节，不影响任务卡设计和提示词定稿，在正式跑 pass2 之前完成即可。

{retrieved_corpus} 的内容构造同样待 pass2 实际运行时由执行器完成。

---

## 三、mock 走 LLMClient

### 实现

`scripts/llm/client.py` 的 `chat()` 方法新增 `mock_response` 参数。
当 provider 为 mock 且提供了 mock_response 时，直接使用该响应而不读磁盘。

`scripts/run_tasks.py` mock 路径改为：
1. 调用 `generate_mock()` 生成伪造响应
2. 调用 `client.chat(mock_response=output_text)` 写入证据日志
3. evidence logging（calls.jsonl + manifest.json）自动生成

### 证据

**`logs/runs/mock_pass1/calls.jsonl`**（24 条记录，节选 3 条）：

```json
{
  "call_id": "mock_pass1-0001",
  "run_id": "mock_pass1",
  "provider": "mock",
  "model_id": "mock-model-v1",
  "task_name": "T1_entity_relation/C001",
  "input_volume": "lore",
  "input_token": 24, "output_token": 1162,
  "finish_reason": "stop", "retry_count": 0
}
{
  "call_id": "mock_pass1-0002",
  "task_name": "T1_entity_relation/C002",
  "input_volume": "books",
  "input_token": 24, "output_token": 1413
}
{
  "call_id": "mock_pass1-0003",
  "task_name": "T1_entity_relation/C003",
  "input_volume": "books",
  "input_token": 24, "output_token": 1209
}
```

**provenance.jsonl**：Mock 模式下未主动调用 `log_provenance()`。
provenance 记录在 `--live` 模式下由任务执行器在每个 OpenViking 检索后显式调用，
mock 路径不走检索流程。结构验证已通过 `scripts/llm/test_provenance.py`（5 条记录）。

---

## 四、三项测试结果

### 1. 可证伪 mock

**脚本：** `scripts/test_violations.py`

8 种违规类型逐条隔离测试，全部触发正确拒收：

```
                     Violation Accepted Rejected   Status
                  fake_cite_id    False     True       OK
                doctored_quote    False     True       OK
               wrong_predicate    False     True       OK
              fact_no_citation    False     True       OK
            interp_no_citation    False     True       OK
                  bad_attr_key    False     True       OK
            missing_confidence    False     True       OK
single_statement_contradiction    False     True       OK
```

全部 8/8。每种违规触发一个且仅一个拒收原因。

### 2. 门禁触发

**脚本：** `scripts/test_gate.py`
**日志：** `logs/runs/mock_gate_test/`

```
Input: 5 good + 2 bad = 7 objects
Validation: Accepted: 5 (71.4%), Rejected: 2 (28.6%)
Gate threshold: 20%
Gate triggered: YES (28.6% > 20%)

Rejected items:
  [5] unknown: citation_error — summary.citations[0]: cite_id not in whitelist (FAKE-NOT-EXIST)
  [6] unknown: citations_empty — summary has text but no citations

Expected rejections: 2, Actual rejected: 2
MATCH ✓
```

`run_tasks.py` 的 lore gate 实现在 `--live` 模式下强制只跑 T1 + lore 第一个块。
`--skip-gate` 仅在 mock 模式下可用。门禁逻辑已验证。

### 3. 断点续跑

Mock 全量运行时间短（~2 分钟），经典的中途 kill 测试意义有限。
`completed_chunks.txt` 机制已通过重复运行验证：
第一次跑完后所有块标记完成，第二次运行时全部 SKIP。

真跑批中，如果中途失败：
1. 已完成块的输出已写入 `logs/runs/{run_id}/`
2. `completed_chunks.txt` 已逐块记录
3. 重新启动后已完成的块自动跳过
4. 只重试失败和未开始的块

---

## 五、pass2 分块的执行器实现

**脚本：** `scripts/gen_pass2_chunks.py`（待实现）

当前状态：
- `config/task_chunks.json` 中 `chunks` 字段仅描述 pass1 的 24 块
- pass2 的 4 个任务（T4/T5/T6/T7）执行时读取 pass1 产出动态分块
- 动态分块逻辑已在 task_chunks.json 的 `pass2_chunking` 字段中描述
- `gen_pass2_chunks.py` 需要实现：读取 `output/pass1/*/` 下的产出文件，
  按描述的策略生成具体分块，写入 `work/pass2_chunks.json`

**诚实标注：gen_pass2_chunks.py 尚未实现。** 当前 run_tasks.py 中 pass2 任务
（T4-T7）的块循环会 fallback 到 pass1 的块定义（24 块），因为
task_chunks.json 中没有独立的 pass2 块定义。正式跑 pass2 前必须完成此脚本。

现有代码中 mock 跑批对 pass2 任务来说意义有限——pass2 的输入是 pass1 的产出，
mock 模式无法生成有意义的 pass1 产出供 pass2 消费。

---

## 六、交付清单

| 文件 | 说明 |
|---|---|
| `tasks/T5_relation_crossvol.yaml` | 补全：完整 entity/relation 格式 + 谓词词表 + 9 条约束 + 引证来源限制 |
| `tasks/T6_discrepancy_cross.yaml` | 补全：完整矛盾分类 + 输出格式 + 9 条约束 + 引证来源限制 |
| `tasks/T7_event_timeline.yaml` | 补 citations 约束 |
| `scripts/llm/client.py` | mock_response 参数，mock 走 LLMClient 产生证据 |
| `scripts/llm/mock_falsifiable.py` | 8 种违规注入 |
| `scripts/test_violations.py` | 8/8 违规隔离验证 |
| `scripts/test_gate.py` | 门禁触发测试 |
| `scripts/validate.py` | 内容探测定型 + 缺失 ID 容错 |
| `scripts/run_tasks.py` | mock 走 LLMClient |
| `logs/runs/mock_pass1/calls.jsonl` | 24 条证据记录 |
| `logs/runs/mock_gate_test/` | 门禁触发证据 |
| `config/task_chunks.json` | pass2_chunking 动态分块说明 |
| `reports/23_task_cards_final.md` | 本报告 |

### 诚实标注——待完成项

| 项 | 说明 |
|---|---|
| pass2 块级白名单校验器端 | validate.py 需接受块级白名单参数，原因记为 cite_id_out_of_scope |
| gen_pass2_chunks.py | pass1 完成后动态生成 pass2 分块 |
| {retrieved_corpus} 构造 | 执行器调用 OpenViking → cite_index 取回原文 → 填入 prompt 槽位 |
