# Schema 与校验器 v2

> 修正 v1 的三项问题：收紧 citations 约束、修复 2 条放行违规、cite_id 对账。

## 变更记录

### 一、收紧 citations 约束

**修改前：** fact 类强制带引证，interpretation 类不强制。

**修改后：** 任何自然语言字段都必须带非空 citations，包括 Discrepancy.analysis 和 MergeRecord.rationale。

- `scripts/validate.py`：`check_nl_fields` 移除 claim_type 分支，统一要求 citations 非空
- `schema/discrepancy.schema.json`：`analysis.citations` 已有 `minItems: 1`（无需改）
- `schema/merge_record.schema.json`：`rationale.citations` 加上 `minItems: 1`（**新增**）
- 新增违规 mock：interpretation 类文本无引证（`CHAR:NoCiteInterp`）

### 二、两条被放行的违规样例

| 序号 | 对象 | 本应触发 | 原因 | 修复 |
|---|---|---|---|---|
| [0] | CHAR:TooLong | quote 超过 200 字符 | mock 数据 `idx[c][:250]` 操作在短文本上实际未超过 200 字符 | 改用真实长文本，确保 quote 长度 250 |
| [14] | CHAR:BadVol | source_volume 不在枚举 | 校验器未实现 source_volume 枚举检查 | 新增 `invalid_source_volume` 检查项 |

### 三、cite_id 对账

```
231,109  (v1 主卷 7 卷合计)
-  1,381  (A3 dialogue → excluded_ip)
-     23  (A3 narrative → excluded_ip)
-      3  (A3 artifacts → excluded_ip)
─────────
= 229,702  (当前主卷 = 白名单 = 引证索引)
```

speakerless 的 61 条不在此列（speakerless 不在 7 卷主卷中）。

**229,702 = 229,702 = 229,702。完全对平。**

---

## 1. 引证索引

| 指标 | 值 |
|---|---|
| 总 cite_id | 229,702 |
| 覆盖卷数 | 7 |
| 构建耗时 | < 1s |

## 2. JSON Schema 文件

| 文件 | 变更 |
|---|---|
| `schema/citation.schema.json` | 无变更 |
| `schema/entity.schema.json` | 无变更 |
| `schema/relation.schema.json` | 无变更 |
| `schema/event.schema.json` | 无变更 |
| `schema/discrepancy.schema.json` | 无变更（analysis.citations 已有 minItems: 1） |
| `schema/merge_record.schema.json` | **rationale.citations 新增 minItems: 1** |
| `schema/predicates.json` | 无变更 |

## 3. 校验器 12+1 项检查

| # | 检查项 | 说明 |
|---|---|---|
| 1 | cite_id 在白名单 | 229,702 个 ID |
| 2 | quote 精确子串匹配 | 按 cite_id 取 clean |
| 3 | offset 对齐 | clean[start:end] == quote |
| 4 | quote 长度 ≤ 200 | 超出即拒收 |
| 5 | 所有自然语言字段 citations 非空 | fact + interpretation 统一要求 |
| 6 | predicate 在受控词表 | 21 个谓词 |
| 7 | subject/object 指向已声明实体 | 跨对象校验 |
| 8 | confidence 在枚举内 | attested/inferred/disputed |
| 9 | claim_type 在枚举内 | fact/interpretation |
| 10 | Discrepancy.analysis.claim_type 强制 interpretation | 模型分析不能标记为 fact |
| 11 | contradiction 类 statements ≥ 2 | |
| 12 | ID 格式正则 | 每种 TYPE 独立 |
| 13 | source_volume 在枚举内 | **新增** |

## 4. Mock 自测结果

### 合规数据（22 条，6 种类型）

```
Total: 22
Accepted: 22 (100.0%)
Rejected: 0
```

### 违规数据（16 条，16 种违规类型）

```
Total: 16
Accepted: 0 (0.0%)
Rejected: 16 (100.0%)
```

拒绝原因分布：

| 原因 | 条数 |
|---|---|
| citation_error | 4 (quote 超长 1, cite_id 不在白名单 1, 非子串 1, offset 不对 1) |
| citations_empty | 3 (fact 无引证 1, interpretation 无引证 1, analysis 无引证 1) |
| subject_id not declared | 3 |
| object_id not declared | 3 |
| invalid_relation_id | 2 |
| invalid_predicate | 1 |
| invalid_confidence | 1 |
| invalid_entity_id | 1 |
| contradiction_needs_2_statements | 1 |
| analysis_not_interpretation | 1 |
| invalid_discrepancy_id | 1 |
| invalid_claim_type | 1 |
| rationale_not_interpretation | 1 |
| invalid_merge_id | 1 |
| invalid_source_volume | 1 |

## 5. 交付清单

| 文件 | 变更 |
|---|---|
| `schema/merge_record.schema.json` | 修改 |
| `scripts/validate.py` | 修改（citation 收紧 + source_volume 检查） |
| `scripts/gen_mock_data.py` | 修改（修复 mock 数据 + 新增 interpretation 无引证） |
| `tests/fixtures/valid/all.json` | 重新生成 |
| `tests/fixtures/invalid/all.json` | 重新生成 |
| `reports/09_schema.md` | 本报告 v2 |