# 33_demo_full.md — 真数据接入前收尾 报告

报告时间：2026-08-08 19:25 CST

---

## 一、修正日期

周一 (2026-08-10) pass1，周二 (2026-08-11) pass2。

| 位置 | 修正内容 |
|---|---|
| run_id | `live_pass1_20260810` / `live_pass2_20260811` |
| deploy_site.sh | 添加 `--filter-mode filter`，修正 run_id 引用 |
| 报告第六节 | 所有命令更新为正确日期 |

---

## 二、收紧 ID 正则 + 真实语料反向验证

### 2.1 修改内容

判据 1 第三条正则从：
```
\b[A-Z]{2,6}[:-]\d+\b           ← 会误伤型号/编号（AR-26710 等）
```
收紧为：
```
\b(?:CHAR|AEON|PATH|ORGN|PLAC|WRLD|CONC|ARTF|RACE)[:-]\d+\b   ← 只匹配类型码
```

### 2.2 真实语料验证

对 `cite_index.jsonl` 的 `lore`、`books`、`characters` 三卷 `clean` 字段进行对比扫描：

| 卷 | 旧正则命中 | 新正则命中 |
|---|---|---|
| lore | 0 | 0 |
| books | 0 | 0 |
| characters | 4 | 0 |
| **total** | **4** | **0** |

### 2.3 旧版 4 条误伤样例（均为游戏内型号/编号，非内部 ID）

1. **[characters] cite_id=STRY-1310-2**
   match: `AR-26702`
   context: "有人走到她身边，轻轻地说。那人身上有一个号牌，**AR-26702**——那是什么？她看向自己，AR-26710。「过来…我的"

2. **[characters] cite_id=STRY-1310-2**
   match: `AR-26710`
   context: "身上有一个号牌，AR-26702——那是什么？她看向自己，**AR-26710**。「过来…我的孩子…」"

3. **[characters] cite_id=STRY-1310-3**
   match: `AR-53935`
   context: "战甲上有红色的绶带。「下一片战场，希望能看见星星。」——**AR-53935**，他是和自己不同的「另一种型号」。"

4. **[characters] cite_id=STRY-1310-3**
   match: `AR-4077`
   context: "「各位，欢迎归队！」——**AR-4077**，虽然自己和他素未谋面，但知道他从来不上战场，只待在后方。"

这 4 条全部是剧情中士兵/型号的编号（AR-XXXXX 格式），属于正常游戏叙事内容，被旧正则误判为内部 ID。新正则已排除此类误伤。

---

## 三、Demo 数据卷分布

### 3.1 卷分布表

| 卷 | 实体 | 关系 | 事件 | 矛盾 | 说明 |
|---|---|---|---|---|---|
| `lore` | 17 | 8 | 2 | 2 | 星神/命途/概念/组织 |
| `characters` | 11 | 10 | 1 | 1 | 角色/角色组织 |
| `narrative` | 8 | 2 | 5 | 1 | 世界/地点/任务剧情 |
| `books` | 3 | 1 | 1 | 1 | 古籍/历史条目 |
| **pass1 合计** | **39** | **21** | **9** | **5** | — |
| **pass2 merges** | — | — | — | — | 2 条归并记录 |
| **pass2 cross-disc** | — | — | — | **1** | 1 条跨卷矛盾 |
| **最终** | **37** | **21** | **9** | **6** | 2 实体归并 → 37 |

### 3.2 跨卷实体（供归并溯源展示）

| 实体 | 出现卷 | 归并方法 |
|---|---|---|
| 三月七 (CHAR) | characters + narrative | exact_name — 同名确认为同实体 |
| 星穹列车 (ORGN) | characters + narrative | exact_name — 同名确认为同实体 |

每个跨卷实体在两个卷中有不同的 summary 与属性：
- **三月七 (characters)**: "星穹列车的少女，从漂流于太空的六相冰中被救出。"
- **三月七 (narrative)**: "在贝洛伯格的行动中展现出了远超其开朗外表下的冷静判断力。"

不同卷提供的不同侧面信息，归并后以 characters 卷的完整描述为准（记录在 merge.rationale 中）。

### 3.3 跨卷矛盾（供矛盾档案展示）

`塔伊兹育罗斯的陨落原因`：
- **books 卷**：古籍《诸界虫灾纪》记载虫皇陨落是"群虫突然失去方向，虫巢开始自我吞噬"→ 内部崩溃叙事
- **narrative 卷**：仙舟行动记录中岚的光矢曾"洞穿虫皇甲胄"→ 外部干预叙事

同一条星神陨落的史实在不同文本体裁中呈现方式截然不同——典型的跨卷矛盾。

---

## 四、七视图全部有内容的 DOM 验证

```
tabs: 命途星图 / 银河编年史 / 矛盾档案 / 未解之谜 / 归并溯源(非置灰) / 引证审计 / 考据质量
归并溯源: disabled: false  ← pass2 接入后恢复可用
page errors: 0
```

### 命途星图
- `25 节点 · 21 边`（真实数据，非演示模式）
- 谓词图例: EMBODIES, OPPOSES, RELATED_TO, MEMBER_OF, ALLY_OF, LOCATED_IN

### 银河编年史
- 9 个事件按 order_hint 排列，含推断标记
- 事件名称均为自然语言（星穹列车启程、贝洛伯格星核危机…）

### 矛盾档案
- 6 条矛盾（5 卷内 + 1 跨卷）
- 跨卷矛盾「塔伊兹育罗斯的陨落原因」在跨卷分区显示

### 未解之谜
- 2 张 gap 卡片：阿基维利的消失、星核的本质

### 归并溯源
- **不再置灰！** pass2 merges 提供 2 条归并记录（三月七、星穹列车）
- 每条显示归并目标、来源、方法、判定理由

### 引证审计台
- 空状态（无 citables 数据时显示 empty-state.png + 说明文字）

### 考据质量
- 质量过滤 0 flagged，所有判据通过

---

## 五、周一启动流程（修正版）

```bash
# Monday Aug 10 - Pass1
python scripts/run_tasks.py --live --run-id live_pass1_20260810 --concurrency 3

# Verify quality
python scripts/build_site_data.py --input output/pass1 --filter-mode audit
# → check work/quality_audit.json

# Build site data (filter mode)
python scripts/build_site_data.py --input output/pass1 --filter-mode filter
python scripts/build_stats.py --run-id live_pass1_20260810

# Local build verify → push
cd site && npm run build
cd .. && bash scripts/deploy_site.sh

# Tuesday Aug 11 - Pass2 (after pass1 data is clean)
python scripts/run_tasks.py --live --run-id live_pass2_20260811 --concurrency 3 --resume

# Full site build with pass2
python scripts/build_site_data.py --input output/pass1 --pass2 --filter-mode filter
python scripts/build_stats.py --run-id live_pass2_20260811
cd site && npm run build
bash scripts/deploy_site.sh
```

---

## 六、文件变更

### 修改
- `scripts/build_site_data.py` — 正则第三条收紧为类型码匹配
- `scripts/gen_demo_pass1.py` — 多卷分布 + pass2 产出
- `scripts/deploy_site.sh` — +`--filter-mode filter`，修正 run_id

### 新增（demo 数据）
- `tests/fixtures/demo_pass1/lore/` — 17 实体 + 8 关系 + 2 事件 + 2 矛盾
- `tests/fixtures/demo_pass1/characters/` — 11 实体 + 10 关系 + 1 事件 + 1 矛盾
- `tests/fixtures/demo_pass1/narrative/` — 8 实体 + 2 关系 + 5 事件 + 1 矛盾
- `tests/fixtures/demo_pass1/books/` — 3 实体 + 1 关系 + 1 事件 + 1 矛盾
- `tests/fixtures/demo_pass2/merges.jsonl` — 2 条归并记录
- `tests/fixtures/demo_pass2/discrepancies.jsonl` — 1 条跨卷矛盾
