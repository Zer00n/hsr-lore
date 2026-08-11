# 「崩坏：星穹铁道」世界观考据站

《崩坏：星穹铁道》（Honkai: Star Rail）的世界观考据与引证索引站点。
从官方公开游戏文本中提取实体、关系、事件与矛盾，构建可追溯引证的世界观图谱。

> **当前状态**：站点已上线 pass1 全量真实考据数据（doubao-seed-evolving 生成，
> 2026-08-10 跑批）。每条收录对象均通过逐字引证校验；未通过校验的对象不予收录。
> 跨卷归并（pass2）尚未并入，实体/事件/矛盾以 pass1 形态展示并标注未归并/推断。

---

## 技术栈

- **框架**：[Astro](https://astro.build/)（静态站点生成）
- **UI**：React 19（island 架构，按需 hydration）
- **数据格式**：JSON（详见 [数据契约](src/data/contract.md)）
- **部署**：Cloudflare Pages（静态托管）

## 本地运行

```bash
# 安装依赖
npm install

# 开发服务器（热更新）
npm run dev

# 生成生产构建
npm run build

# 预览生产构建
npm run preview
```

Node.js 版本要求：`>=18.17.1`（推荐 20+）。

## 数据来源

本项目的考据数据全部来自以下公开来源：

- 游戏内公开文本（角色故事、书籍、对话、遗器描述等）
- 官方公开 Wiki 与设定集
- 公开数据集

所有数据均通过管线自动化提取，并经逐句引证校验（quote 对语料原文做精确子串匹配，含空白归一化）。每条收录结论均携带可追溯的引证标识（cite_id + 原文片段），访问者可据此定位游戏内原始出处；未通过校验的对象不予收录。

## 版权声明

本网站为**非商业性质的同人考据作品**。

- 所引用游戏文本片段（包括但不限于角色对话、故事文本、物品描述等）之著作权、商标权及其他相关知识产权，均归 **COGNOSPHERE PTE. LTD.** 及其关联方所有。
- 本站不对任何游戏资产主张所有权。所引用的原文片段仅用于学术研究与同人考据目的，属于合理引用（fair use / 合理使用）范畴，不构成对原作的替代或侵权。
- 如版权方认为本作品存在不当使用，请联系仓库维护者进行内容调整或删除。
- 本站点不涉及任何商业盈利，不向访问者收取费用，不投放广告。

维护者：[@Zer00n](https://github.com/Zer00n)

项目仓库：[https://github.com/Zer00n/hsr-lore](https://github.com/Zer00n/hsr-lore)

---

## 站点结构

```
├── public/
│   ├── data/          ← 六类静态数据文件（JSON）
│   └── favicon.svg
├── src/
│   ├── components/    ← React 组件（命途星图 / 时间轴 / 矛盾档案 / 考据质量）
│   ├── data/          ← 数据契约与 TypeScript 类型定义
│   ├── layouts/       ← Astro 布局（Base.astro）
│   ├── pages/         ← 路由页面（index.astro、disclaimer.astro）
│   └── styles/        ← 设计 Token（CSS 自定义属性）
├── astro.config.mjs
├── package.json
└── tsconfig.json
```

## 当前数据说明（pass1 真实数据）

`public/data/` 下的 JSON 由管线从 `output/pass1/` 构建，构建时强制通过校验闸：

```bash
cd ../hsr-lore
python scripts/build_site_data.py --input output/pass1 --require-validation --filter-mode filter
python scripts/build_stats.py --run-id live_pass1_20260810
```

特点：

- **校验闸默认开启**（`--require-validation`）：只有校验器判定 ACCEPTED 的对象才会进入站点数据；未通过逐字引证校验的对象被剔除。可用 `--no-require-validation` 关闭（非正式发布口径）。
- **pass1-only 数据**：无 pass2 归并，无跨卷矛盾关联
- **实体未归并**：同名实体在多个卷中各自保留（标注「未归并」）
- **时间轴推断**：事件时序来自 order_hint，标注「推断」
- **引证仅含片段**：citations.json 只包含实际引用的原文片段（quote），不包含语料全文

pass2 跨卷归并跑完并并入后，未归并/推断标注将自动取消。
