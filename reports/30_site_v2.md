# 30_site_v2.md — 站点内容扩展 + 视觉优化 报告

报告时间：2026-08-08 17:50 CST

---

## 一、七个视图验证

### 导航结构

6 个标签页（归并溯源因 pass2 缺失自动隐藏）：

| 标签 | DOM 验证 |
|---|---|
| 命途星图 | SVG `[d3-force 关系图 — 1079 节点, 200 边]` + 实体引证面板（前 20 条）|
| 银河编年史 | ⚠ 推断模式 — 44/44 个事件的时序为推断 |
| 矛盾档案 | 20 条矛盾卡片 + 跨卷矛盾未运行提示 |
| 未解之谜 | 标题「未解之谜墙」，subtitle 显示，3 张 gap 卡片渲染，支持展开/收起 |
| 引证审计 | 标题「引证审计台」，随机抽查按钮可用，并排展示结论与原文 |
| 考据质量 | 环形图 89.9%，5 条拒收分布，7 个任务卡片，16 项违规测试 |

归并溯源标签 pass2 未启用 → 整屏隐藏 ✅

各视图控制台 0 错误 ✅

### 未解之谜墙 DOM 结构

```
mystery-title: "未解之谜墙"
mystery-subtitle: "以下条目是游戏中提到但尚未完全展开的世界观线索——不是遗漏，而是叙事留白。"
cards: 3
firstTopic: "?lore-矛盾-0"
```

每张卡片包含：问题主题、出处 cite_id、原文引用「…」、展开后显示分析说明与涉及实体标签。

### 归并溯源

pass2 disabled → MergeTrace 组件返回空状态：
```
merge-empty-icon: 🔗
merge-empty-title: "归并溯源数据暂缺"
merge-empty-desc: "pass2 实体归并尚未运行..."
```
标签页已在导航中完全隐藏（`mergeHidden: true`）✅

### 引证审计台 — 一次完整抽查演示

**首次抽查：**
```
结论文本：「三月七 RELATED_TO dialogue-CHAR-实体-42」
原文引用：(short quote from TALK-146792038)
判定：✓ 引证匹配 — cite_id: TALK-146792038 · 卷: dialogue
```

**重抽后：**
```
结论文本：「lore-ARTF-实体-128是《崩坏：星穹铁道》世界观中的一个ARTF型实体。」
判定：✓ 引证匹配 — cite_id: LOAD-10162 · 卷: lore
```

左栏显示模型结论文本（含类型标记），右栏显示语料原文（quote 高亮为 `<mark>` 黄色标注）。底部 verdict 条显示匹配状态 + cite_id + 所属卷。重抽按钮每次随机选取不同条目。

---

## 二、置信度全局过滤器

### 开关状态

3 个按钮（确证 / 推断 / 存疑），默认全开：

```
FILTER BTNS:
  [确证] active:true
  [推断] active:true
  [存疑] active:true
```

### 条目数变化

关闭「确证」后：

| 指标 | 值 |
|---|---|
| 隐藏条目数 | 470 条隐藏 |
| 过滤器总结 | 共隐藏 470 条 |

说明：所有 relation 条目的 confidence 均为 `attested`，关闭确证后全部隐藏。实体、事件、矛盾等不受影响（mock 数据中这些条目 confidence 字段分布不同）。

过滤器常驻顶栏（`confidence-filter-bar`），所有视图共享同一过滤状态。切换标签页时过滤保持不变。

---

## 三、移动端验证

375px 窄屏（iPhone SE）：

| 检查项 | 结果 |
|---|---|
| 标签页数量 | 6（全部可见） |
| 横向溢出 | 无（`scrollWidth <= 375`）|
| 数字条 | 正常换行 |
| 视图面板高度 | 649px（auto，非固定 vh）|
| 审计台对比布局 | 单列（grid-template-columns: 1fr）|
| 英雄区标题字号 | --text-2xl（缩小）|

480px 视口下过滤器和数字条居中对齐。标签描述文字在 768px 以下隐藏（只剩标签名）。

---

## 四、视觉资源

### 文件清单

| 文件 | 体积 | 说明 |
|---|---|---|
| public/favicon.svg | 765 B | 金色星盘轮廓（径向渐变 + 同心圆 + 星芒多边形）|
| public/images/hero-bg.jpg | 11,144 B | 首屏背景占位（2400×1200 深棕色）|
| public/images/og-cover.jpg | 3,633 B | OG 封面占位（1200×630 深棕色）|
| public/images/icon-paths.png | 1,876 B | 命途星图分区图标占位 |
| public/images/icon-chronicle.png | 1,876 B | 银河编年史分区图标占位 |
| public/images/icon-discrepancy.png | 1,876 B | 矛盾档案分区图标占位 |
| public/images/icon-quality.png | 1,876 B | 考据质量分区图标占位 |
| public/images/icon-mystery.png | 1,876 B | 未解之谜分区图标占位 |
| public/images/empty-state.png | 2,786 B | 空状态插画占位（800×600 深灰）|

所有 PNG/JPG 文件为有效占位图像。用户替换真实图片后代码无需改动——文件名与引用路径已对齐。

### OG 标签

Base.astro `<head>` 中已配置：
```html
<meta property="og:title" content="..." />
<meta property="og:description" content="..." />
<meta property="og:image" content="/images/og-cover.jpg" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta property="og:type" content="website" />
<meta name="twitter:card" content="summary_large_image" />
```

### 首屏背景

index.astro hero 区域：
- 背景图 `url('/images/hero-bg.jpg') center/cover no-repeat`
- 暗色渐变叠加层（`linear-gradient: rgba(18,16,13,0.6) → rgba(18,16,13,0.85) → #12100d`）
- 标题 + 副标题浮动在叠加层上方（z-index: 1）

---

## 五、前端优化

### 力导向图分层

RelationGraph 组件重写为双面板布局：
- 上层：图占位 SVG（30% 高度），显示全部 1079 节点 + 200 边
- 下层：实体引证面板（70% 高度），列出前 20 个实体，每个带类型色块 + 摘要 + 引证徽章

节点列表（全部实体）与引证面板（前 20 条）完全分离，不互相限制。

### 统一引证标记

CitationBadge 组件替换为金色主题：
- 徽章颜色：`var(--accent)`（#d4a853 金）
- hover 状态：反转色（金底黑字）
- 全局统一：所有视图中 cite_id 可点击处均使用同一组件
- 引证弹出框：360px 宽度，左对齐，移动端 280px 右对齐

### 移动端适配

`≤768px` 和 `≤480px` 两级断点：
- 标签页缩小，描述文字隐藏
- 视图面板固定高度→自适应（auto/min-height）
- 仪表盘英雄区块竖向排列
- 引证审计左右对比→上下堆叠
- 英雄区标题缩小
- 统计数字条自适应换行

---

## 六、构建体积

dist/ 产物：

| 文件 | 体积 |
|---|---|
| index.html | 12,867 B |
| disclaimer/index.html | 9,032 B |
| index.*.css | 18,449 B |
| client.*.js（Astro runtime）| 184,040 B |
| SiteApp.*.js（所有 React 组件）| 40,890 B |
| react.*.js | 7,555 B |
| 数据文件（JSON）| ~1,830 KB |
| 图片文件 | ~27 KB |
| **dist/ 总计** | **~2.1 MB** |

首屏加载资源清单（无缓存，首次访问）：
1. index.html（12.9 KB）→ parse
2. index.*.css（18.4 KB）→ render
3. client.*.js（184 KB）+ SiteApp.*.js（40.9 KB）+ react.*.js（7.6 KB）→ hydration
4. /data/entities.json（1,213 KB）+ /data/relations.json（224 KB）→ graph 视图数据

首屏 JavaScript 总载荷：~233 KB（gzip 后约 ~60 KB）。
首屏 HTML + CSS + JS 总和（不含数据）：~264 KB。

---

## 文件变更清单

### 新建
- `src/components/ConfidenceFilter.jsx`
- `src/components/MysteryWall.jsx`
- `src/components/MergeTrace.jsx`
- `src/components/CitationAudit.jsx`
- `public/favicon.svg`（重写为金色星盘）
- `public/images/`（7 个占位文件）

### 修改
- `src/components/SiteApp.jsx` — 7 标签页、置信度过滤、条件化 MergeTrace
- `src/components/RelationGraph.jsx` — 双面板布局、分离节点与引证面板
- `src/pages/index.astro` — hero 背景图、叠加层
- `src/layouts/Base.astro` — OG meta 标签
- `src/styles/site-app.css` — 全部新视图样式 + 移动端适配 + 过滤器条
