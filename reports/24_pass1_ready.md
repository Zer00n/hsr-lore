# pass1 就绪报告

---

## 一、真实 prompt 拼装验证

### 方法

对全部 34 个 pass1 块执行真实 prompt 拼装（system_prompt + user_prompt，
占位符全部替换），不发送任何模型。每个块的完整 prompt 落盘到
`work/prompts/{chunk_id}.txt`。

### 分块调整过程

原始分块（v2）基于 `len(clean) × 0.75` 估算 token，未计入 `[cite_id]\n`
标签和 prompt template 开销。实际拼装后偏差 +63.6%，8 块超 60 万上限。

修正为 v3：
- 每条目 overhead：18 字符（`[{cite_id}]\n{clean}\n` 标记）
- prompt template overhead：2,000 token
- 单块上限：550,000 token（60 万减 5 万安全余量）

### 最终统计（34 块）

| 指标 | 值 |
|---|---|
| 总块数 | 34 |
| 总实际字符 | 10,283,079 |
| 0 块超 60 万上限 | ✓ |
| 未替换占位符 | 0 |
| 编码正常 | ✓ |
| 偏差范围 | -92.7% ~ +23.1%（预估值整体偏高，实际偏低） |

### 占位符检查

全 34 块未发现未替换的 `{xxx}` 占位符。模板的 `{volume_name}`、
`{entry_count}`、`{scope_description}`、`{corpus_entries}` 全部正确替换。

### 格式检查（3 块各前 20 行）

**C001 (lore, 62K tokens):**
```
[NOUN-2702432903392642343]
于原初混沌的裂隙中萌生了嫩芽，在以亿万年为单位的时间浇灌下，嫩芽长成了无朋巨树。
巨树的枝杈上结出了缤纷的嫩叶，每一枚都承载着宇宙意志的碎片。那意志永恒地言说着

[NOUN-11308015425422997488]
天才俱乐部的黑塔不满足于寻常世界的万物法则，她将目光投向了银河中未解的存在...
```

**C011 (narrative world 401 匹诺康尼):**
```
[CHRN-1000101]
在入侵现场优雅踱步的女人如同一道谜题，她嘲弄着受害者的同时又残酷地将加害者消灭殆尽。
通讯里神秘的协助者透露出两人似乎怀抱着某种目的...

[CHRN-1000201]
目光从陌生的天花板上移开后，你看着周围的各色「奇物」，脑袋中似乎还残留着一个女人的声音。
「当你有机会做出选择的时候，不要让自己后悔。」...
```

**C022 (dialogue minor speakers):**
```
[TALK-802611221]
哟！稀客啊。让我瞧瞧…嗯，有段时间不见，你好像变得更摇滚了！

[TALK-802611222]
加把劲，你的摇滚程度快比得上机械屋的废弃引擎了。
```

格式正确：`[cite_id]\n原文\n\n`。

### 编码检查

34 块全量 reread 无乱码。通过。

### 最大块（C025, dialogue, 759,735 chars）首尾

完整提示词已保存到 `work/prompts/C025.txt`。

前 100 行：system_prompt 完整 + 元信息行 + 语料正文起始行，格式正常。
后 20 行：末尾语料条目 + 任务行，无截断。

---

## 二、断点续跑

### 测试流程

1. 启动完整 mock pass1（T1 全 34 块）
2. 等待约 15 秒（~C010 完成时）
3. 执行 `kill -9` 强制终止（SIGKILL，模拟真实崩溃）
4. 检查 `completed_chunks.txt` 和输出文件
5. 重新启动，确认续跑行为

### 原始输出

**Kill 后状态：**
```
completed_chunks.txt: 10 lines (C001-C010)
output JSONL files: 21 files
```

**重启后：**
```
Resume: 10 chunks already completed
[C001] SKIP (already completed)
...
[C010] SKIP (already completed)
[C011] narrative... OK
```

### 结论

**completed_chunks.txt 在块完成时写入，不在块开始时写入。**
被 SIGKILL 中断的 C011 未被标记完成，重启后重新执行。
已完成的 C001-C010 正确跳过，无遗漏无重复。

---

## 三、pass1 已就绪

### 当前状态清单

| 项 | 状态 |
|---|---|
| 语料封版 8 卷 276,702 条 | ✓ |
| cite_index 重建 | ✓ |
| verify 100/100 | ✓ |
| 幂等 MD5 | ✓ |
| cite_id 唯一性 | ✓ |
| fixtures 22/22 + 16/16 | ✓ |
| 7 张任务卡定稿 | ✓ |
| 34 块分块方案（0 超限） | ✓ |
| prompt 真实拼装 34 块 | ✓ |
| 占位符 0 残留 | ✓ |
| 编码正常 | ✓ |
| 断点续跑 kill+restart | ✓ |
| offset 回填器 | ✓ |
| mock provider 走 LLMClient | ✓ |
| calls.jsonl 证据层 | ✓ |
| gate 触发测试 | ✓ |

### 待完成（推迟到 pass1 之后）

- pass2 块级白名单校验器端
- gen_pass2_chunks.py
- {retrieved_corpus} 构造
- T5/T6 提示词复核（取决于 pass1 实际产出）

### 可开跑

`python scripts/run_tasks.py --provider doubao --live`

（首次运行自动触发 lore gate，只跑 C001 T1 一个块，等人工确认）

---

## 交付

| 文件 | 说明 |
|---|---|
| `scripts/build_prompts.py` | prompt 拼装验证器 |
| `scripts/gen_chunks.py` | v3 分块生成（含 per-entry overhead） |
| `config/task_chunks.json` | 34 块分块方案 |
| `work/prompts/*.txt` | 全部 34 块的完整 prompt |
| `work/prompt_assembly_report.json` | 拼装统计数据 |
| `logs/runs/mock_pass1/completed_chunks.txt` | 断点续跑证据 |
| `reports/24_pass1_ready.md` | 本报告 |
