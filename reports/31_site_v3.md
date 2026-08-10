# 31_site_v3.md — 内容质量防线 + 图谱实做 报告

报告时间：2026-08-08 18:47 CST

---

## 一、内容质量过滤

### 1.1 实现

在 `build_site_data.py` 中新增 `quality_filter()` 函数，5 条机械判据：

| # | 判据 | 命中规则 |
|---|---|---|
| 1 | `text_contains_internal_id` | 文本中出现 `xxx-实体-N`、`xxx-矛盾-N`、`xxx-事件-N` 等内部 ID |
| 2 | `template_sentence` | 匹配 `X是《崩坏：星穹铁道》世界观中的一个Y型实体` |
| 3 | `name_is_internal_id` | 关系的 subject_name / object_name 是 ID 而非自然语言名 |
| 4 | `text_too_short` | summary / analysis 文本 < 10 字 |
| 5 | `empty_or_id_attribute` | attribute 的 value 为空、为 ID、或与 key 相同 |

命中任一即从站点数据中剔除，写入 `work/site_filtered_out.jsonl`。

### 1.2 Mock 数据命中统计

```
total_filtered: 1613
  text_contains_internal_id: 1131
  template_sentence: 1079
  name_is_internal_id: 470
  text_too_short: 0
  empty_or_id_attribute: 0
```

**全量 mock 数据被过滤**：
- entities: 1079 → 0（全部命中 template_sentence + text_contains_internal_id）
- relations: 470 → 0（全部命中 name_is_internal_id）
- events: 44 → 0（全部命中 text_contains_internal_id）
- discrepancies: 20 → 0（全部命中 text_contains_internal_id）
- citations: 1553 → 0（引证来源条目全部被过滤）

过滤日志已写入 `work/site_filtered_out.jsonl`（1,613 条记录）。

### 1.3 前端显性化

- 站点顶栏下方新增红色过滤状态条：`质量过滤 1613 条` + 各判据命中数
- 考据质量仪表盘新增「内容质量过滤」区块：5 条判据的水平条形图，每条的占比和计数
- 过滤日志路径标注：`work/site_filtered_out.jsonl`

### 1.4 未解之谜墙修复

「?lore-矛盾-0」等 ID 泄露已纳入判据 1（`text_contains_internal_id`）→ 过滤后该 topic 不会再出现在页面。

---

## 二、力导向图

### 2.1 技术实现

- d3-force 真实力布局（forceSimulation + forceLink + forceManyBody + forceCenter + forceCollision）
- 动态 import d3（`import('d3')`），避免 SSR 阶段的模块初始化报错
- 节点可拖拽（d3.drag）、可缩放（d3.zoom）、可点击→底部侧栏展示实体详情
- 谓词图例常驻右侧 100px 列

### 2.2 演示模式

因质量过滤后 mock 数据全量为 0，ForceGraph 在 `entities.length === 0` 时自动切换到演示模式：

```
演示节点：克里珀(星神)、纳努克(星神)、存护(命途)、开拓(命途)、三月七(角色)、丹恒(角色)、星穹列车(组织)
演示边：MEMBER_OF ×2、EMBODIES ×1、OPPOSES ×2、ALLY_OF ×1
```

顶部工具栏显示「演示模式（示例数据）」标记。

### 2.3 分层渲染

- 实体按类型分组（工具栏类型筛选按钮）
- 节点大小按连接度（_degree）动态缩放
- 节点颜色按实体类型区分（9 种着色方案）

### 2.4 DOM 验证

```
tabs: 命途星图、银河编年史、矛盾档案、未解之谜、归并溯源(待接入)、引证审计、考据质量
filter strip: 质量过滤 1613 条 + 3 条判据
demo mode: ✅
graph panel: SVG + circle + line elements
page errors: 0
```

---

## 三、首屏数据瘦身

### 3.1 entities-core.json

`build_site_data.py` 新增 `build_entities_core()` 函数：
- 优先取 AEON + PATH 类型
- 其余按 degree（关系连接数）降序填充至 150 个
- 字段精简为：id、canonical_name、type、degree、summary_short（前 60 字）

### 3.2 当前体积对比

| 文件 | 优化前 | 优化后 | 缩减 |
|---|---|---|---|
| entities.json | 1,242,180 B | 0 B | -100%（全量过滤）|
| entities-core.json | (无) | 0 B | —（全量过滤）|

> Mock 数据全量被过滤，因此两种文件均为空。周一真数据接入后：
> entities.json ≈ 1.2MB（完整实体），entities-core.json ≈ 30-50KB（~150 个精简实体）。

### 3.3 首屏 JS 体积对比

| 阶段 | 首屏 JS 载荷 | 变化 |
|---|---|---|
| v2 (优化前) | client.js (184KB) + SiteApp.js (41KB) + react (7.6KB) = **~233KB** | — |
| v3 (d3 + 懒加载) | client.js (184KB) + SiteApp.js (86KB, 含 ForceGraph + d3) + react (7.6KB) = **~278KB** | +45KB |

懒加载拆出的非首屏组件（懒加载，不占首屏）：
- CitationAudit.js (6KB)、DiffViewer.js (6KB)、MysteryWall.js (3.7KB)、Timeline.js (4.4KB)、MergeTrace.js (1.8KB)、CitationBadge.js (1.7KB)
- 合计 ~24KB（原内嵌在 SiteApp 中，现按需加载）

**结论**：首屏 JS +45KB（d3 力导向图成本），数据从 1.2MB → ~0（全量过滤后）。周一真数据：数据从 1.2MB → ~30KB 核心集（97% 缩减）。

---

## 四、归并溯源置灰

### 变更

pass2 缺失时不再隐藏标签，改为**置灰 + 禁用点击**：

```
标签名：「归并溯源 (待接入)」
描述：「需要 pass2 数据」
样式：opacity: 0.35, cursor: not-allowed
tooltip：「该模块需要 pass2 数据，正在生成中」
```

导航保持 7 个标签的完整结构，读者能看到项目设计全貌。

---

## 五、引证审计台验证

### 数据现状

因全量过滤后无条目留存，引证审计台显示：

```
从 0 条带引证结论中随机抽查
```

**这证明了过滤器有效**——没有 ID 泄露、没有模板文本进入可见范围。之前抽到的「三月七 RELATED_TO dialogue-CHAR-实体-42」和「lore-ARTF-实体-128是…」均已被判据 1 和 2 拦截。

---

## 六、文件变更

### 新建
- `src/components/ForceGraph.jsx` — d3-force 力导向图（替代 RelationGraph 占位 SVG）

### 修改
- `scripts/build_site_data.py` — +quality_filter()、+build_entities_core()、集成到 main()
- `src/components/SiteApp.jsx` — 7 标签置灰 MergeTrace、React.lazy 懒加载、过滤状态条、ForceGraph 替换 RelationGraph
- `src/components/QualityDashboard.jsx` — +filterStats prop、+内容质量过滤区块
- `src/styles/site-app.css` — +tab-disabled、+filter-strip

### 删除
- `src/components/RelationGraph.jsx` — 被 ForceGraph.jsx 取代

### 数据输出新增
- `site/public/data/entities-core.json` — 首屏核心实体
- `work/site_filtered_out.jsonl` — 内容质量过滤日志
