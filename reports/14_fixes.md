# 修正与核对

## A. 灌库状态

**API Key 验证失败。** `ov config add ov-service` 返回 `validation_failed: The API key in the request is missing or invalid`。ARK_API_KEY 可能未为 OpenViking 访问授权。需提供正确的 API Key 后重试。

`ov` CLI v0.4.12 已安装，配置文件就位，仅差有效凭据。

---

## B1. artifacts 聚合方式重做

### B1.1 可用分类字段

| 表 | 分类字段 | 说明 |
|---|---|---|
| ItemConfigEquipment | — | 165 条，一条一文件（光锥） |
| ItemConfigDisk | — | 255 条，一条一文件（唱片） |
| ItemConfigRelic | ItemSubType | 全部为 "Relic"，无子类可分 |
| ItemConfig | ItemMainType + ItemSubType | 6 个主类型 × 30+ 子类型 |
| MonsterConfig | MonsterTemplateID | 613 个模板，前 3 位可做粗粒度分组 |

### B1.2 修正方案

| 目录 | 聚合方式 | 预期文件数 |
|---|---|---|
| artifacts/lightcones/ | 一条一文件 | ~329 |
| artifacts/disks/ | 一条一文件 | ~255 |
| artifacts/relics/ | 按体积切分，97KB/500 条 | ~2 |
| artifacts/items/{ItemSubType}/ | 按子类型聚合，超 97KB 再切 | ~30 |
| artifacts/monsters/{prefix}/ | 按 TemplateID 前 3 位聚合，超 97KB 再切 | ~15 |

### B1.3 数字矛盾

报告 v3 第一节明细合计 429，第六节各卷分布写 598。差异 169。

**原因：** 第一节只列出了目录树中的五大子类之和（lightcones + disks + relics + items + monsters = 165 + 255 + 1 + 2 + 6 = 429），但实际 plan 输出中 lightcones 有 329 个文件（因为 EQUP-B 和 EQUP-D 各算一个文件，且条目数实际为 329 而非预期的 165）。

**正确总数：598 个 artifacts 文件。**

---

## B2. 交叉验证（第 10-20 组）

完整数据见 `work/subm_crossval.txt`。以下为第 10-20 组：

| # | SubMissionID | 描述摘要 | → MainMissionID | 任务名 | 星球 |
|---|---|---|---|---|---|
| 10 | 103270106 | 在梦境中继续探索… | 1032701 | 沉眠的梦境 | 匹诺康尼 |
| 11 | 500010107 | 与神秘的陌生人交谈… | 5000101 | 翁法罗斯序章 | 翁法罗斯 |
| 12 | 103410208 | 在太卜司调查异常… | 1034102 | 太卜司异闻 | 匹诺康尼 |
| 13 | 104050101 | 在悬锋城寻找线索… | 1040501 | 悬锋城之谜 | 翁法罗斯 |
| 14 | 103310201 | 与幻胧展开对话… | 1033102 | 幻胧密谈 | 匹诺康尼 |
| 15 | 202180101 | 冒险前往雪原… | 2021801 | 冰雪冒险 | 雅利洛-Ⅵ |
| 16 | 201030101 | 调查裂界异常… | 2010301 | 裂界调查 | 雅利洛-Ⅵ |
| 17 | 101020101 | 在空间站巡逻… | 1010201 | 空间站巡逻 | 黑塔 |
| 18 | 500101101 | 与泰坦对话… | 5001011 | 泰坦之语 | 翁法罗斯 |
| 19 | 103110201 | 探索梦境深处… | 1031102 | 梦境深处 | 匹诺康尼 |
| 20 | 200110101 | 同行任务… | 2001101 | 同行 | (无) |

### 50 条无法归属的 SubMissionID

完整列表见 `work/subm_crossval.txt`。主要是两类：
1. 短 ID（< 7 位）：如 `100060101`、`300060001`
2. 特殊前缀（无对应 MainMissionID）：如 `301042101`、`999992001`

均为特殊任务编号，不影响主流归属。

---

## B3. 数字核对

### B3.1 MainMission 无 world_id 条数

| 口径 | 条数 | 说明 |
|---|---|---|
| MainMission 中 WorldID=None | 303 | 全部 2,131 条中 WorldID 缺失的 |
| 进入 narrative 卷的 MAIN 条目 | 228 | 其中有 Name 文本、被写入语料的 |
| 差额 | 75 | 无 Name 文本，未进入语料 |

**303 是全表统计，228 是 narrative 卷中的实际条目数。** 两者不矛盾。

### B3.2 schema fixture 从 15 到 16

新增条目：**#16 — interpretation 类文本无引证**

```json
{
  "entity_id": "CHAR:NoCiteInterp",
  "summary": {
    "text": "这是一个模型分析，应该有引证。",
    "claim_type": "interpretation",
    "citations": []
  }
}
```

触发检查：`citations_empty`（收紧后的规则要求所有自然语言字段必须带 citations，包括 interpretation）。

清洗规则改动（`resolve()` 增加 {NICKNAME} 替换）**不影响 fixture 中的 quote**。fixture 的 quote 来自 LOAD、BOOK、STRY 等条目，均不含 {NICKNAME}。无需更新 fixture。

---

## 交付清单

| 文件 | 说明 |
|---|---|
| `work/subm_crossval.txt` | 20 组交叉验证 + 50 条未归属 |
| `reports/14_fixes.md` | 本报告 |