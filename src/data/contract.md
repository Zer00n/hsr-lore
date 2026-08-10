# 站点数据契约 / Site Data Contract

站点消费的全部静态数据文件位于 `site/public/data/`，由 `scripts/build_site_data.py` 生成。
字段名与 `schema/` 下的 JSON Schema 完全一致，前端不做重命名。

## 数据文件

### entities.json

实体列表（含 pass2 归并后的结果）。当 pass2 缺失时使用 pass1 原始实体。

```json
[
  {
    "entity_id": "CHAR:三月七",
    "type": "CHAR",
    "canonical_name": "三月七",
    "aliases": [],
    "summary": {
      "text": "三月七是星穹列车的成员...",
      "claim_type": "fact",
      "confidence": "attested",
      "citations": [{"cite_id": "...", "quote": "..."}]
    },
    "attributes": [
      {
        "key": "身份",
        "value": "星穹列车成员",
        "claim_type": "fact",
        "confidence": "attested",
        "citations": [{"cite_id": "...", "quote": "..."}]
      }
    ],
    "source_volume": "characters",
    "_merged": false,
    "_merge_ids": []
  }
]
```

额外字段（前端使用，非 schema 定义）：
- `_merged`: boolean — 是否为 pass2 归并后的实体
- `_merge_ids`: string[] — 归并来源的 entity_id 列表
- `_source_volumes`: string[] — 该实体出现的所有卷

### relations.json

关系列表。pass2 产出合并到同一数组。

```json
[
  {
    "relation_id": "REL:abc123def456",
    "subject_id": "CHAR:三月七",
    "predicate": "MEMBER_OF",
    "object_id": "ORGN:星穹列车",
    "qualifiers": {},
    "claim_type": "fact",
    "confidence": "attested",
    "citations": [{"cite_id": "...", "quote": "..."}],
    "source_volume": "narrative"
  }
]
```

### events.json

事件列表。含 pass1 事件及 T7 补充的 relative_to。

```json
[
  {
    "event_id": "EVT:narrative-abc123",
    "name": "星穹列车启程",
    "summary": {
      "text": "开拓者登上星穹列车...",
      "claim_type": "fact",
      "confidence": "attested",
      "citations": [{"cite_id": "...", "quote": "..."}]
    },
    "participants": ["开拓者", "三月七", "丹恒"],
    "locations": ["星穹列车"],
    "stated_time": "琥珀纪2157年",
    "relative_to": [
      {"relation": "after", "event_id": "EVT:lore-event-1"}
    ],
    "order_hint": 1,
    "confidence": "attested",
    "citations": [{"cite_id": "...", "quote": "..."}],
    "source_volume": "narrative",
    "_timeline_inferred": false
  }
]
```

额外字段：
- `_timeline_inferred`: boolean — T7 补充的时序关系是否为推断（pass2 缺失时为 true）

### discrepancies.json

矛盾与悬案列表。

```json
[
  {
    "discrepancy_id": "DSC:abc123def456",
    "kind": "contradiction",
    "topic": "克里珀的登神时间",
    "statements": [
      {"text": "黄昏战争因琥珀王诞生而终结", "citation": {"cite_id": "...", "quote": "..."}},
      {"text": "0-180琥珀纪古兽依然活跃", "citation": {"cite_id": "...", "quote": "..."}}
    ],
    "analysis": {
      "text": "公司宣称与考古发现相矛盾...",
      "claim_type": "interpretation",
      "confidence": "inferred",
      "citations": [{"cite_id": "...", "quote": "..."}]
    },
    "related_entities": ["克里珀", "黄昏战争"],
    "impact": "high",
    "_cross_volume": false
  }
]
```

额外字段：
- `_cross_volume`: boolean — 是否为 T6 检测的跨卷矛盾（pass2 缺失时仅显示卷内矛盾）

### citations.json

引证索引子集。只包含实际被 entities/relations/events/discrepancies 引用到的 cite_id。
只携带任务实际引用的原文片段（quote）与定位元数据，**不包含语料的 clean 全文**。

```json
[
  {
    "cite_id": "AEON-1-1",
    "quote": "……「存护」克里珀，与「贪饕」奥博洛斯同为宇宙中已知最古老的星神。",
    "volume": "lore"
  }
]
```

### stats.json

质量指标与运行统计。

```json
{
  "citation_pass_rate": 0.85,
  "total_calls": 34,
  "total_input_tokens": 12500000,
  "total_output_tokens": 800000,
  "cumulative_afp": 0,
  "per_task_counts": {
    "T1_entity_relation": {"entities": 1200, "relations": 800},
    "T2_event": {"events": 200},
    "T3_discrepancy_intra": {"discrepancies": 45}
  },
  "rejection_reasons": {
    "cite_id not in whitelist": 12,
    "quote not exact substring": 8,
    "invalid_predicate": 3
  },
  "totals": {
    "entities": 1200,
    "relations": 800,
    "events": 200,
    "discrepancies": 45
  }
}
```
