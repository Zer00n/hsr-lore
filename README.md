# 「崩坏：星穹铁道」世界观考据站

《崩坏：星穹铁道》（Honkai: Star Rail）的世界观考据与引证索引站点。
从官方公开游戏文本中提取实体、关系、事件与矛盾，构建可追溯引证的世界观图谱。

> **当前状态**：站点工程骨架已完成，数据为**测试用示例数据**（非真实考据结果）。
> 正式数据管线运行后，本仓库数据文件将被替换为实际产出。

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

所有数据均通过管线自动化提取与逐句校验（quote 精确匹配原文）。每条结论均携带可追溯的引证标识（cite_id + 原文片段），访问者可据此定位游戏内原始出处。

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

## 当前数据说明（示例数据）

`public/data/` 下的 JSON 文件为示例数据，由以下命令生成：

```bash
cd ../hsr-lore
python scripts/build_site_data.py --input tests/fixtures/mock_pass1/
```

特点：

- **pass1-only 数据**：无 pass2 归并，无跨卷矛盾关联
- **实体未归并**：同名实体在多个卷中各自保留（标注「未归并」）
- **时间轴推断**：事件时序来自 order_hint，标注「推断」
- **引证仅含片段**：citations.json 只包含实际引用的原文片段（quote），不包含语料全文

正式数据将在周一管线运行后切换，届时所有标注自动取消。
