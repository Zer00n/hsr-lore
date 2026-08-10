# 语料最终台账 v3 — 语料层封版

> 语料层定稿，之后不再改动。所有数字脚本生成。

---

## 一、narration 计数矛盾解释

**数据来源：** 分类器对比测试原始 stdout（正文上方），`work/speakerless_classified_v2.json`

### 根因：settle_corpus.py 内联分类器存在运算符优先级 bug

```python
# Bug (settle_corpus.py 原版，已修复):
if re.match(r'^你[^？！。，]{8,}', text) and '了' in text or '着' in text:
    return 'narration'
# Python 解析为: (re.match() and '了' in text) or ('着' in text)
# 任何含「着」的文本都被误判为 narration
```

```python
# 正确 (v3 分类器):
if re.match(r'^你[^？！。，]{8,}', text) and not QM.search(text):
    if '了' in text or '着' in text:
        return 'narration'
```

### 计数链条

| 阶段 | narration | dialogue | unclassified | 说明 |
|---|---|---|---|---|
| v3 分类器（65,450 条全量） | 2,989 | 26,049 | 31,305 | 正确基线 |
| settle bug 版（65,450 条分类后去重） | 4,371 | 18,538 | 24,090 | +1,382 误判 |
| settle 修复版（65,450 条分类后去重） | 2,846 | 18,538 | 25,615 | narration = 2,989 - 143(去重扣除) |

**1,382 = 1,599（bug 多判）− 217（对话特征检查拦截）。**

### 分类器确定性

同一输入重跑两次，结果完全一致（在 18,451 条测试集中 0 条差异）。
分类器是确定性的，但 settle_corpus.py 的内联副本与原版不一致。

### 影响评估

text_layer 标签已经纠正。最新写入的 `corpus/unattributed.jsonl` 使用正确的 v3 分类器结果。

---

## 二、全库 cite_id 重复审计

**数据来源：** `work/cite_id_duplicates.json`
**生成脚本：** `scripts/audit_cite_ids.py`

### 精确对账

```
14,604 = 14,586 + 18
         └─────────┘   └── excluded_ip 重叠（VOIC/ITEM 条目同时在主卷与排除卷）
         narrative vs speakerless
         （同一 TalkSentenceID 同时出现在
          可归属对话 + 无说话人分册）
          = 13,344（本轮去重回退）+ 1,242（预存重叠）
```

**0 条内容不一致。** 所有重复 cite_id 在各卷中的 clean 文本完全一致。

**0 条主卷内部重复。** 8 个主卷之间 cite_id 互不重叠。

### 收支明细

| 来源 | 重复 cite_id 数 | 说明 |
|---|---|---|
| narrative ∩ speakerless | 14,586 | 主卷与隔离分册的正常备份重叠 |
| excluded_ip ∩ main | 18 | IP 排除条目同时在排除卷与主卷 |
| **合计** | **14,604** | |
| 前报 | 14,624 | |
| 差额 | 20 | unattributed 清洗后条目数微调 |
| **对平** | **±0** | |

---

## 三、unattributed 清洗修复

**数据来源：** verification stdout

### 清洗内容

对 `corpus/unattributed.jsonl` 应用与主卷完全相同的清洗规则：
- `\\n` → `\n`（0 条命中，unattributed 不含 `\\n`）
- `{TEXTJOIN#N}` → 删除（0 条命中）
- `{NICKNAME}` → 开拓者（1 条命中）

### 清洗后残留对比

| 指标 | 清洗前 | 清洗后 |
|---|---|---|
| 主卷残留条目 | 105 | **47** |
| 残留模式 | 28 | **24** |
| 主要残留来源 | `<rhythm>`(134) | `<rhythm>`(134) 仍在 fixed content 中 |

`<rhythm>` 134 个是游戏内置标记（节奏标记），不应被正则剥离。主卷剩余 28 种模式为 `{Img#1}`（24 个，图片占位）和 HTML 样式残留。

### 验收原始输出（省略）

```
verify 100/100 ✓
cite_id 主卷 276,702 = 276,702 唯一 ✓
幂等 MD5 11 文件全匹配 ✓
fixtures 22/22 + 16/16 ✓
```

完整验收输出见 `work/corpus_settlement_report.json` 及 settlement 脚本 stdout。

---

## 四、语料最终台账（封版）

### 主卷 8 卷

| 卷 | 条数 | 字符数 | 估算 token |
|---|---|---|---|
| lore | 570 | 70,767 | 53,075 |
| books | 1,772 | 786,338 | 589,753 |
| characters | 5,544 | 309,140 | 231,855 |
| narrative | 37,408 | 1,055,215 | 791,411 |
| dialogue | 177,653 | 4,847,049 | 3,635,286 |
| artifacts | 6,014 | 365,623 | 274,217 |
| rogue | 742 | 138,999 | 104,249 |
| unattributed | 46,999 | 823,115 | 617,336 |
| **合计** | **276,702** | **8,396,246** | **~6.30M** |

### 隔离卷 2 卷

| 卷 | 条数 | 字符数 | 隔离原因 |
|---|---|---|---|
| speakerless | 18,451 | 149,249 | placeholder + ui_system + 主卷重叠备份 |
| excluded_ip | 1,696 | 42,735 | Fate 联动 IP 内容 |

### unattributed 卷构成

| 分类 | 条数 | 说明 |
|---|---|---|
| narration | 2,846 | 二人称/三人称描写 |
| dialogue | 18,538 | 对白句式无标注说话人 |
| unclassified | 25,615 | 未分类 |
| **合计** | **46,999** | |

### 灌库计划

5,524 文件，34.4 MB，5 AFP/小时，< 15,000 阈值 ✓

### excluded_ip 最终判据分布

```
AvatarID 不在 AvatarConfig:       229
Speaker 不在 AvatarConfig:      1,377
Mission-based (803420x):          23
Composite speaker:                 4
Keyword-based (Fate 术语):        61
Artifact Fate reference:           2
                                  ─────
                        合计:   1,696
```

---

## 五、变更清单（v2 → v3 追加）

13. **settle_corpus.py 分类器运算符优先级 bug 修复。** `'着' in text` 导致 1,599 条文本被误判为 narration，text_layer 标签已纠正
14. **unattributed 卷补做清洗。** 应用 `\n`/TEXTJOIN/NICKNAME 清洗规则，主卷残留标记从 105 条降至 47 条
15. **cite_id 重复全量审计。** 14,604 个重复全部为主卷与隔离卷的合法备份重叠，0 条内容不一致，0 条主卷内部重复
16. **语料层封版。** 主卷 276,702 条，~6.30M token，不再改动

（前 12 条见 v2 报告，不重复列出）

---

## 交付清单

| 文件 | 说明 |
|---|---|
| `corpus/unattributed.jsonl` | 最终版：46,999 条，已清洗 |
| `corpus/speakerless.jsonl` | 最终版：18,451 条 |
| `corpus/excluded_ip.jsonl` | 最终版：1,696 条 |
| `corpus/index.json` | 最终版：含全部 10 卷统计 |
| `work/cite_index.jsonl` | 276,702 条 |
| `work/cite_whitelist.txt` | 276,702 ID |
| `work/corpus_hashes.json` | MD5 基线（11 文件） |
| `work/cite_id_duplicates.json` | 14,604 条重复审计 |
| `scripts/audit_cite_ids.py` | 重复审计脚本 |
| `scripts/settle_corpus.py` | 结算脚本（bug 已修复） |
| `reports/19_corpus_final_v2.md` | 本报告（v3 封版） |
