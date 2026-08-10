# 语料收尾与并行准备

## A. 语料收尾

### A1. verify.py 修复

**100/100 通过。** 抽样从 30 提到 100，覆盖全部 24 种 TYPE，每种至少 2 条。verify.py 改为按 cite_id 组合键反查，不再依赖单字段主键匹配。

### A2. 幂等测试

**通过。** 两次运行全部 10 个输出文件（含 isolation 卷）MD5 完全一致：

```
artifacts.jsonl:  MATCH
books.jsonl:      MATCH
characters.jsonl: MATCH
dialogue.jsonl:   MATCH
excluded_ip.jsonl: MATCH
lore.jsonl:       MATCH
narrative.jsonl:  MATCH
rogue.jsonl:      MATCH
speakerless.jsonl: MATCH
index.json:       MATCH
```

### A3. Fate 联动隔离

**候选清单已提交**（`work/a3_fate_candidates_v2.md`），等待确认后执行迁移。

### A4. 残留标记统计

上一轮报告「28 种模式，105 条」的统计口径错误——`<rhythm>` 134 次出现在隔离卷（speakerless），不应算入主卷。

**正确数字（两个口径）：**

| 口径 | 条目数 | 模式数 | 说明 |
|---|---|---|---|
| 主卷（7 卷） | 47 | 24 | 不含 speakerless/excluded_ip |
| 隔离卷 | 58 | 6 | 仅 speakerless + excluded_ip |
| 合并 | 105 | 28 | 两个口径的模式有重叠 |

### A5. 数字核对补充

- `book_series_name` 填充率：06 报告 59.3% 是正确的（修正前），05 报告 66.1% 是计算错误。修正后 **100%**。
- SubMission 条数：16,324 是实际语料条目数。18,297 是字段非空条数之和（9,173+9,124），06 报告误将后者写为语料条目数。

---

## B. 模型调用抽象层与证据层

### B1. 调用抽象层

`scripts/llm/client.py` 已完成：

- **provider 无关**：切换模型只改 `config/providers.yaml`
- **mock provider**：读本地 `config/mock_responses/{digest}.json`
- **重试与超时**：可配置次数、退避间隔（指数退避）
- **长输入分块**：接口已预留 `chunked_chat()`，实现标记 TODO

### B2. 证据层

每次调用落盘 `logs/runs/{run_id}/calls.jsonl`，字段齐全。同时维护 `manifest.json`。

### B3. Mock 测试

**20 次假调用全部通过验证：**

```json
{
  "run_id": "mock_test_001",
  "call_count": 20,
  "total_input_tokens": 4900,
  "total_output_tokens": 6850,
  "total_tokens": 11750,
  "total_latency_ms": 100,
  "success_count": 20,
  "failure_count": 0
}
```

- 日志结构完整，可被程序读取
- 累计统计正确（call_count 匹配、token 匹配）
- 全部 20 条记录字段齐全

---

## C. 部署管线

### 站点工程骨架

- 技术栈：Astro + React island
- 构建产物：静态站
- 工程位置：`site/`（本次仅创建骨架，不含完整页面）

### 部署配置

- 部署平台：Cloudflare Pages / Vercel（待定）
- CI：`git push` → 自动构建部署
- 构建命令：`npm run build`
- 构建耗时：首次 ~30s（空站）

### 占位首页

已创建 `site/src/pages/index.astro`，内容为：

> 「崩坏：星穹铁道」世界观考据站 — 语料处理阶段已完成，站点建设中。

### 访问地址

待部署后提供。临时开发服务器：`npm run dev` → `http://localhost:4321`

---

## D. 前端骨架与设计系统

### D1. 设计 token 机制

已建立 `site/src/styles/tokens.css`，CSS 变量驱动：色板、字阶、间距刻度、圆角、阴影、动效时长与缓动曲线。

### 三套配色方案

#### 方案 A：星穹铁道官方蓝紫色调

| 变量 | 色值 | 用途 |
|---|---|---|
| `--bg-base` | `#0a0e1a` | 最深背景 |
| `--bg-surface` | `#111827` | 卡片/面板 |
| `--bg-elevated` | `#1a2236` | 悬浮层 |
| `--text-primary` | `#e8ecf4` | 主文字 |
| `--text-secondary` | `#8892a8` | 次要文字 |
| `--accent` | `#5b8def` | 强调色（星穹蓝） |
| `--accent-alt` | `#c4b5fd` | 辅助强调（紫） |
| `--border` | `#1e293b` | 边框 |
| `--success` | `#34d399` | 确定性-高 |
| `--warning` | `#fbbf24` | 确定性-中 |

#### 方案 B：暗金色学术调

| 变量 | 色值 | 用途 |
|---|---|---|
| `--bg-base` | `#0d0d0d` | 最深背景 |
| `--bg-surface` | `#1a1a1a` | 卡片/面板 |
| `--bg-elevated` | `#262626` | 悬浮层 |
| `--text-primary` | `#e6e0d3` | 主文字 |
| `--text-secondary` | `#8c8878` | 次要文字 |
| `--accent` | `#d4a853` | 强调色（琥珀金） |
| `--accent-alt` | `#b8864e` | 辅助强调 |
| `--border` | `#333333` | 边框 |
| `--success` | `#7eb896` | 确定性-高 |
| `--warning` | `#d4a853` | 确定性-中 |

#### 方案 C：低饱和冷灰

| 变量 | 色值 | 用途 |
|---|---|---|
| `--bg-base` | `#0f1117` | 最深背景 |
| `--bg-surface` | `#161822` | 卡片/面板 |
| `--bg-elevated` | `#1e2130` | 悬浮层 |
| `--text-primary` | `#c8ccd4` | 主文字 |
| `--text-secondary` | `#6b7080` | 次要文字 |
| `--accent` | `#7eb8da` | 强调色（冷蓝） |
| `--accent-alt` | `#e8a87c` | 辅助强调（暖橙） |
| `--border` | `#252836` | 边框 |
| `--success` | `#8cb88c` | 确定性-高 |
| `--warning` | `#d4b87c` | 确定性-中 |

**字体：** 系统字体栈占位，中文字体变量预留切换点。

### D2. 组件骨架

三个核心视图的 React 组件骨架已创建：

1. **力导向关系图**（`site/src/components/RelationGraph.jsx`）：d3-force 驱动，节点可点击/拖拽/悬停展示引证来源，支持按类型过滤
2. **可缩放时间轴**（`site/src/components/Timeline.jsx`）：节点带确定性等级标记（明确记载/可推断/存疑），可缩放
3. **并排对照视图**（`site/src/components/DiffViewer.jsx`）：左右两栏展示原文，高亮差异

---

## E. 素材归档

`article/` 目录已建立，`reports/` 下全部报告已归档。`article/timeline.md` 已记录项目关键节点，包括：

- 上游数据仓库消失与迁移
- 抽取脚本因数据结构变更失效
- 自研抽取器
- 角色名误判事件（AvatarID 1014-1017）
- cite_id 行号隐患（PerformanceID → PerformanceType+PerformanceID）
- 隔离而非删除的通则确立

---

## F. 验证集脚手架

`work/fact_candidates.jsonl` 已生成，共 300 条候选：

| 卷 | 候选数 | 筛选条件 |
|---|---|---|
| lore | 100 | 长度 20-120 字 |
| books | 100 | 含专有名词 |
| characters | 100 | 不含代词指代 |

每条含 `cite_id`、`volume`、`text`、`length`。不做题目编写，不做答案标注，只做机械筛选和输出。

---

## 交付清单

| 文件 | 说明 |
|---|---|
| `scripts/verify.py` | 验证脚本 v2（组合键反查，100/100） |
| `scripts/llm/client.py` | 模型调用抽象层 |
| `scripts/llm/test_mock.py` | Mock 测试（20 次，全部通过） |
| `config/providers.yaml` | Provider 配置（mock + doubao） |
| `logs/runs/mock_test_001/` | Mock 运行证据 |
| `site/` | Astro 站点骨架 |
| `article/timeline.md` | 项目时间线 |
| `article/reports/` | 全部报告归档 |
| `work/fact_candidates.jsonl` | 验证集候选（300 条） |
| `work/a3_fate_candidates_v2.md` | Fate 联动候选清单 |
| `reports/08_wrapup_and_prep.md` | 本报告 |