# 32_site_v4.md — 真数据接入前最终轮 报告

报告时间：2026-08-08 19:06 CST

---

## 一、过滤器三档模式

### 1.1 --filter-mode 参数

| 模式 | 行为 | 输出 |
|---|---|---|
| `audit`（默认）| 运行判据，统计命中率和样本，**不剔除**数据 | `work/quality_audit.json` |
| `filter` | 运行判据，剔除命中条目 | `work/site_filtered_out.jsonl` |
| `off` | 完全跳过 | — |

用法：
```bash
# 周一先跑 audit，看命中率
python scripts/build_site_data.py --input output/pass1 --pass2 --filter-mode audit

# 确认无误伤后切换到 filter
python scripts/build_site_data.py --input output/pass1 --pass2 --filter-mode filter
```

### 1.2 扩展后的 ID 正则（判据 1 完整内容）

```python
RE_INTERNAL_ID = re.compile(
    r'\b\w+[-:]\w*[-:]?(?:实体|矛盾|事件|CHAR|AEON|PATH|ORGN|PLAC|WRLD|CONC|ARTF|RACE)[-_:]?\d*\b'
    r'|\b[a-z]+_[A-Z]+_\d+\b'   # snake_case identifiers
    r'|\b[A-Z]{2,6}[:-]\d+\b'   # TYPE:number or TYPE-number in text
)
```

覆盖泄漏形态：
1. `lore-PLAC-实体-146`（mock 格式，实体/矛盾/事件 后缀）
2. `CHAR:三月七`（entity_id 冒号格式，CHAR/AEON/PATH/… 类型前缀）
3. `AEON-5`、`CHAR-1`（简写 ID 格式）
4. `lore_CHAR_146`、`data_entity_1`（snake_case 标识符）

### 1.3 audit 输出格式

`work/quality_audit.json`：
```json
{
  "mode": "audit",
  "total_entries": 67,
  "total_flagged": 0,
  "flag_rate": 0.0,
  "by_rule": {
    "text_contains_internal_id": {"count": 0, "samples": []},
    "template_sentence": {"count": 0, "samples": []},
    "name_is_internal_id": {"count": 0, "samples": []},
    "text_too_short": {"count": 0, "samples": []},
    "empty_or_id_attribute": {"count": 0, "samples": []}
  }
}
```

---

## 二、Demo 数据验证

### 2.1 数据规模

`tests/fixtures/demo_pass1/lore/` 下生成的手写内容：

| 类型 | 数量 | 说明 |
|---|---|---|
| entities | 35 | 星神(7)、命途(5)、角色(10)、组织(5)、世界/地点(5)、概念(3) |
| relations | 20 | 受控谓词（EMBODIES/MEMBER_OF/OPPOSES/ALLY_OF/LOCATED_IN/RELATED_TO）|
| events | 8 | 含 stated_time 与 order_hint，覆盖叙事与背景传说 |
| discrepancies | 4 | 2 条 contradiction、2 条 gap |
| citations | — | 全部使用真实 cite_id（AEON-1-1、LOAD-10076 等）+ 真实原文片段 |

所有 summary / attributes / analysis 均为手写自然语言，不使用模板句式。

### 2.2 过滤器验证

**audit 模式**：`total_flagged: 0`，`flag_rate: 0.0`
**filter 模式**：`0 entries removed`

**结论**：过滤器对自然语言内容零误伤。验证通过。

### 2.3 站点数据体积

| 文件 | 体积 |
|---|---|
| entities.json | 84,505 B (82 KB) |
| entities-core.json | 9,238 B (9 KB) |
| relations.json | 12,655 B (12 KB) |
| events.json | 12,362 B (12 KB) |
| discrepancies.json | 6,922 B (7 KB) |
| citations.json | 1,467 B (1.4 KB) |
| **合计** | **~127 KB** |

相比之前 mock 数据的 ~1.8MB（全量过滤后 0），demo 数据小巧真实。

---

## 三、七视图 DOM 验证

使用 demo 数据构建后在 headless 浏览器中验证（`http://localhost:4321/`）：

### 标签页
```
命途星图 / 银河编年史 / 矛盾档案 / 未解之谜 / 归并溯源 (待接入·置灰) / 引证审计 / 考据质量
```
7 个标签完整，归并溯源保留并置灰（pass2 缺失）。

### 命途星图
- 工具栏：实体类型按钮（CHAR 20、WRLD 5、AEON 7、PATH 5、…）
- 状态：`35 节点 · 20 边`（无演示模式标记，因为真实数据渲染）

### 银河编年史
- 8 个事件按时间排列，每条带 推断 标记 + 金色 CitationBadge
- 事件名称均为自然语言（星穹列车启程、建木失控、贝洛伯格星核危机…）

### 矛盾档案
- 4 条矛盾卡片：克里珀登神时间（contradiction·高影响）、纳努克动机（ambiguity·高影响）、阿基维利消失（gap·高影响）、星核本质（gap·高影响）
- 每条左右并排显示原文引用 + 分析段 CitationBadge

### 未解之谜墙
- 2 张 gap 卡片：阿基维利的消失、星核的本质
- 每张卡片含原文出处、分析说明、涉及实体标签

### 引证审计台
- 空状态展示：empty-state.png 插画 + 说明文字「暂无数据可审计」

### 考据质量
- 过滤器统计：`content quality filter: 0 flagged`
- 仪表盘内容质量过滤区块显示 5 条判据均为 0

### 控制台错误
- **0 JS 错误**

---

## 四、首屏 JS 体积优化

### 优化措施

ForceGraph 改为 `React.lazy(() => import('./ForceGraph.jsx'))`，d3 代码从主包中完全分离。

### JS 分块对比

| chunk | v3 (优化前) | v4 (优化后) | 加载时机 |
|---|---|---|---|
| client.js | 184,040 B | 184,040 B | 首屏（Astro runtime）|
| SiteApp.js | 86,399 B | **16,964 B** | 首屏（-80%）|
| react.js | 7,555 B | 7,555 B | 首屏 |
| **首屏主包合计** | **277,994 B** | **208,559 B** | — |
| ForceGraph.js | (在内联) | 6,381 B | 懒加载（graph tab） |
| d3 chunk | (在内联) | 61,034 B | 懒加载（graph tab） |
| 其他懒加载 | 23,632 B | 23,632 B | 按需（其他 tabs） |

### 体积缩减

- **首屏主包：278KB → 209KB（-25%）**
- **SiteApp 主包：86KB → 17KB（-80%）**
- 懒加载拆分：d3 + ForceGraph（67KB）并行下载，用户先看到界面结构

### 数据瘦身

| 指标 | mock (全过滤) | demo | 预计 Monday 真数据 |
|---|---|---|---|
| entities.json | 0 | 82 KB | ~800 KB |
| entities-core.json | 0 | 9 KB | ~30-50 KB |
| 首屏数据载荷 | 0 | 9 KB（core only）| ~30-50 KB（core only）|

---

## 五、文件变更

### 新建
- `tests/fixtures/demo_pass1/lore/` — 手写 demo 数据（entities/relations/events/discrepancies.jsonl）
- `scripts/gen_demo_pass1.py` — demo 数据生成脚本

### 修改
- `scripts/build_site_data.py` — +`--filter-mode` 三档、+扩展 ID 正则、+audit 模式输出 `quality_audit.json`
- `src/components/SiteApp.jsx` — ForceGraph → React.lazy
- `src/components/CitationAudit.jsx` — 空状态（插画 + 说明文字）

---

## 六、周一启动流程

```bash
# Step 1: run pass1 pipeline (your existing command)
python scripts/run_tasks.py --live --run-id live_20260811 --concurrency 3

# Step 2: audit mode — check quality
python scripts/build_site_data.py --input output/pass1 --filter-mode audit

# Step 3: review work/quality_audit.json — if flag_rate acceptable, proceed
python scripts/build_site_data.py --input output/pass1 --filter-mode filter
python scripts/build_stats.py

# Step 4: local build verify
cd site && npm run build

# Step 5: deploy
cd .. && bash scripts/deploy_site.sh
```
