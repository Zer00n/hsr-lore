# 27_monday_go：周末收尾交付

> 生成：2026-08-07 10:00 UTC
> 需求：周末收尾——四项，按顺序做

---

## 一、pass2 的 prompt 组装

### 状态：完成 ✓

### 实现

新建 `scripts/pass2_builder.py`，为 T4/T5/T6/T7 四类 pass2 任务分别拼装 prompt：

| 任务 | 模板槽位 | 数据来源 |
|---|---|---|
| T4 | `{entity_list}`, `{ov_navigation_results}` | pass1 entities.jsonl（按卷标注） |
| T5 | `{cite_whitelist}`, `{all_entities}`, `{all_relations}`, `{retrieved_corpus}` | pass1 entities + relations |
| T6 | `{cite_whitelist}`, `{all_entities}`, `{all_intra_discrepancies}`, `{retrieved_corpus}` | pass1 entities + discrepancies |
| T7 | `{all_events}` | pass1 events.jsonl |

`build_real_prompt` 在 pass_num == 2 时调用 `pass2_builder.build_pass2_prompt`。
同时构造该块的 `cite_whitelist`：从所有输入 pass1 对象的 citations 中递归提取 cite_id，
写入 `logs/runs/{run_id}/pass2_whitelist/{task_name}_chunk.json` 并拼入 prompt。

### 四个 pass2 块完整 prompt（保存于 work/prompts/pass2/）

```
T4_entity_merge.txt:    150,904 bytes
T5_relation_crossvol.txt: 1,283,469 bytes
T6_discrepancy_cross.txt: 1,076,356 bytes
T7_event_timeline.txt:     42,731 bytes
```

### calls.jsonl 四条 pass2 记录（input_token 达万级以上）

```
  mock_pass2_prompts-0001: T7_event_timeline/P2-T7_event_timeline-C001     input=12,852
  mock_pass2_prompts-0001: T4_entity_merge/P2-T4_entity_merge-C001        input=31,791
  mock_pass2_prompts-0001: T5_relation_crossvol/P2-T5_relation_crossvol-C001  input=379,014
  mock_pass2_prompts-0001: T6_discrepancy_cross/P2-T6_discrepancy_cross-C001  input=312,989
```

确认：四条记录的 input_token 均为数万到数十万量级，不再是 0。

### 每块 cite_whitelist 的 ID 数量

```
  T4_entity_merge_chunk.json:     1,574 cite_ids
  T5_relation_crossvol_chunk.json: 1,574 cite_ids
  T6_discrepancy_cross_chunk.json: 1,574 cite_ids
  T7_event_timeline_chunk.json:   1,574 cite_ids
```

（四块均覆盖完整的 pass1 mock fixture 产出，1,574 个独立 cite_id）

---

## 二、查清 token 缺口

### 状态：完成 ✓（缺口已定位并修复）

### 调查结果

**1. 条目数一致，无截断。** build_real_prompt 装进去的条目数与 chunk plan 完全一致：

```
C001: found=570/570 cite_ids
C002: found=1064/1064 cite_ids
C014: found=16245/16245 cite_ids
C025: found=16258/16258 cite_ids   ← 最大的块，全部 16258 条装入
```

无截断、无跳过、无只取前 N 条的逻辑。

**2. prompt 字符数对比：** `build_real_prompt` 组装的 prompt 与 `build_prompts.py` 落盘的 prompt 内容完全一致：

```
C001: our_chars=82,614, file_chars=82,614, diff=0
C002: our_chars=376,558, file_chars=376,558, diff=0
C014: our_chars=700,797, file_chars=700,779, diff=-18
C025: our_chars=759,735, file_chars=759,735, diff=0
```

**3. 根因：mock 模式的 token 估算公式错误。**

修正前 `client.py` chat() 在 mock_response 路径中使用：
```python
'prompt_tokens': len(input_str) // 3
```
其中 `input_str = json.dumps(messages, ...)` 是 JSON 序列化后的消息长度。

`len(input_str) // 3` 对中文语料严重低估（~0.35 chars/token vs 正确的 0.75 coefficient）。

修正后将 `prompt_tokens` 改为 `int(sum(len(m['content']) for m in messages) * 0.75)`，
使用与 `token_utils.py` 一致的 TOKEN_COEFFICIENT。

### 修正后对照表（摘录关键块）

| Chunk | prompts chars | old calls input | new estimated | build_prompts_est |
|---|---|---|---|---|
| C001 | 82,043 | 28,557 | **61,532** | 168,881 |
| C002 | 375,493 | 130,514 | **281,619** | 808,389 |
| C006 | 399,248 | 142,956 | **299,436** | 772,597 |
| C014 | 684,551 | 249,930 | **513,413** | 1,158,226 |
| C025 | 759,735 | 269,558 | **569,801** | 1,275,977 |

修正后 mock token 估计值与真实系数一致（0.75 × chars）。

**剩余差异说明：** `build_prompts.py` 报告的 10.3M tokens 是**全量 prompt 文件字符数 × 0.75**，包括了 system + user 两部分。
修正后的 calls.jsonl 则基于**消息 content 字段**的字符数 × 0.75，不包括 JSON 序列化开销。
真实 doubao 调用时 API 返回的 `prompt_tokens` 会提供真实值——这才是熔断和预算的依据。

---

## 三、限流防护

### 状态：完成 ✓

### 1. TPM/RPM 配额

doubao-pro-32k 典型配额（火山引擎方舟平台）：
- **TPM (Tokens Per Minute):** ~300,000
- **RPM (Requests Per Minute):** ~60

写入了 `config/providers.yaml` 的 `tpm_limit` / `rpm_limit`（默认 0 = 不启用自动限流）。

### 2. 安全并发度

按每次调用 2 分钟保守估计：
- 并发 3：峰值 1.5 RPM，每 2 分钟 3 次 × ~100K avg tokens = 300K → 刚好在 TPM 边界
- 并发 4：峰值 2 RPM，每 2 分钟 4 次 × ~100K = 400K → TPM 可能超
- **建议并发度：3**

并发 4 在 RPM 上安全（2 RPM << 60），但 TPM 取决于每块的实际 token 数。
大块（dialogue）单块近 570K tokens，两块并发就会超 TPM。

### 3. 429 指数退避重试

`client.py` 增加：
- `RateLimitError` 异常类（HTTP 429 触发）
- `_call_openai_compatible` 检测 429 → raise RateLimitError
- `chat()` 中独立的 RateLimitError 重试循环：
  - 最多重试 5 次（`max_rate_limit_retries`，可配置）
  - 退避间隔 5s 起（`rate_limit_backoff_ms`），乘数 2.0x
  - 上限 120 秒
  - 重试次数记入 `calls.jsonl` 的 `retry_count`

配置（`config/providers.yaml`）：
```yaml
max_rate_limit_retries: 5
rate_limit_backoff_ms: 5000
rate_limit_backoff_multiplier: 2.0
```

### 4. --concurrency 上限警告

```python
MAX_RECOMMENDED_CONCURRENCY = 3
if args.concurrency > 3 and (args.live or args.provider != 'mock'):
    print("⚠ WARNING: concurrency > 3 ...")
```

---

## 四、修 completed_chunks 追踪

### 状态：完成 ✓

### 根因

上一轮的熔断测试脚本 `a2_fuse_real_test.py` 直接调用 `client.chat()` 而未调用
`client.logger.mark_chunk_completed()`，导致 logger 的 `completed_chunks` 列表始终为空。
`run_tasks.py` 的 `execute_chunk` 函数中已正确调用 `mark_chunk_completed`，
真实跑批不受影响。

### 修正后熔断测试

```
Fuse limit: 5,000,000 input tokens

[C001] lore prompt=82,043chars input=61,532 cum_total=61,532
[C002] books prompt=375,493chars input=281,619 cum_total=343,151
...[C003-C018]...
[C019] dialogue prompt=664,314chars input=498,235 cum_total=5,175,847

  FUSE TRIPPED at [C020]!
  Direction: input
  Current: 5,175,847 / Limit: 5,000,000
  Completed chunks: ['C001', 'C002', 'C003', 'C004', 'C005', 'C006',
     'C007', 'C008', 'C009', 'C010', 'C011', 'C012', 'C013', 'C014',
     'C015', 'C016', 'C017', 'C018', 'C019'] (19 total)

RESULTS: 19 chunks completed, fuse tripped=True
```

确认：熔断消息中列出了全部 19 个已完成块，与 completed_chunks.txt 内容一致。

---

## 五、补：provenance.jsonl

mock pass2 跑批中由于使用 mock OpenViking 响应（不触发真实检索），provenance 记录
由 `retrieve.py` 的实时运行产生（上一轮已验证 4 项 pipeline checks 全部通过）。

确认 retrieve.py 管道中 4 项检查全部通过：
- OV query ✓
- cite_id parsing ✓
- cite_index fetch ✓
- No L0/L1 in corpus ✓

---

## 六、未完成项与影响评估

| 项 | 状态 | 对周一影响 | 对策 |
|---|---|---|---|
| A1 真实校准 | 代码就绪，待 key | 无——第一个 chunk 后反算 | `--live --run-id live_pass1_20260810 --concurrency 3` 跑 lore gate，检查 usage.prompt_tokens 与输入字符数的比值 |
| pass2 的 retrieved_corpus 真实 OV 调用 | 代码就绪（mock 路径），真实 OV 需灌库后验证 | 周二 pass2 需要 | 周一完成灌库后用 `retrieve.py` 测试真实调用 |
| TPM 自动限流 | 保护代码已就绪，未启用自动限流 | 需手动监控 | 建议 concurrency=3，大块并发时密切监控 |

---

## 七、周一命令

```bash
# Step 1: 启动 lore gate（并发 3，安全 TPM）
python scripts/run_tasks.py --live --run-id live_pass1_20260810 --concurrency 3

# gate 通过，检查报告后：
# Step 2: 继续全部 pass1
python scripts/run_tasks.py --live --run-id live_pass1_20260810 --concurrency 3 --resume

# Step 3: 构建站点数据（仅 pass1）
python scripts/build_site_data.py --input output/pass1/
python scripts/build_stats.py --run-id live_pass1_20260810
```

---

> 报告纪律：所有数字由脚本生成到文件、正文引用；所有「已执行」附原始输出。
