# 灌 lore 卷验证链路 ✅

## A1. 灌库

| 指标 | 值 |
|---|---|
| 推送文件数 | 542 |
| 失败 | 0 |
| 耗时 | ~120s（首次）+ 已存在跳过 |
| 开始时间 | 2026-08-06T22:42:59+08:00 |
| 结束时间 | 2026-08-06T22:47:11+08:00 |

## A2. 验证

### A2.1 目录结构

```
viking://resources/hsr/lore/
├── aeons/        40 文件 — 星神条目
├── nouns/        99 文件 — 名词百科
├── titans/       22 文件 — 泰坦
└── worlds/      409 文件 — 星球 + 加载文字
```

### A2.2 分层内容

以 `viking://resources/hsr/lore/nouns/绝灭大君-毁灭.md` 为例：

**L0 摘要**（自动生成，准确）：
> 这是一篇针对游戏《崩坏：星穹铁道》的设定类参考文档，主要整理介绍毁灭星神纳努克麾下反物质军团统领者绝灭大君的相关官方设定。文档明确了绝灭大君的身份定位，逐一讲解了七位已公开绝灭大君的特点、行动逻辑与针对目标。

**L1 概览**（自动生成，带导航）：
> 包含 Quick Navigation 和 Detailed Description 两部分，自动提取了关键观点和导航建议。

**L2 详情**：原文，包含 YAML frontmatter 和 `[cite_id]` 标记的正文。

**结论：** L0/L1 是模型生成的摘要，L2 是原文。引证链路保持完整——模型检索到 L0/L1 后，通过 cite_id 从 `work/cite_index.jsonl` 获取原文进行精确 quote 匹配。

### A2.3 检索验证

| 查询 | 结果数 | 首位得分 | 首位内容 |
|---|---|---|---|
| 纳努克 | 8 | 0.594 | lore/aeons/纳努克.md |
| 命途是什么 | 7 | 0.563 | lore/nouns/命途行者现象.md |
| 哪些实体与毁灭相关 | 8 | 0.481 | lore/nouns/绝灭大君人物.md |

所有查询返回相关结果，语义检索准确。

### A2.4 检索轨迹

OpenViking 返回的 JSON 结构字段：

```json
{
  "ok": true,
  "result": {
    "resources": [
      {
        "context_type": "resource",
        "uri": "viking://resources/hsr/lore/aeons/纳努克.md/纳努克.md",
        "level": 2,
        "score": 0.594,
        "category": "",
        "match_reason": "",
        "relations": [],
        "abstract": "L0 summary text...",
        "overview": null
      }
    ],
    "total": 8
  }
}
```

关键字段：
- `uri` — 命中的资源路径，可用于程序化读取
- `level` — 0=摘要, 1=概览, 2=详情
- `score` — 相关性得分
- `abstract` — 该层级的文本内容

## A3. 清空

| 指标 | 值 |
|---|---|
| 清空时间 | 2026-08-06T23:04+08:00 |
| 挂库总时长 | ~22 分钟 |
| 估算 AFP | 5 AFP/小时 × 0.37h ≈ **1.85 AFP** |

## 结论

1. **灌库链路通。** 542 文件，0 失败，~2 分钟推送完成。
2. **分层生成正常。** L0 摘要准确，L1 概览带导航，L2 原文不变。
3. **检索可用。** 语义搜索返回相关结果，得分合理。
4. **检索轨迹可程序化读取。** JSON 格式，包含 uri、level、score、abstract。
5. **引证链路完整。** OpenViking 做导航 → cite_id → cite_index → 原文。

**注意：** 使用 `ov add-resource --to` 时，文件会被包裹在同名目录中（`xxx.md/xxx.md`），原因是 `--to` 参数要求目标是一个目录。建议后续使用 `--parent` 参数避免此问题。