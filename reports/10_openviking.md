# OpenViking 接入准备

## 1. 配置文件

| 文件 | 状态 | 说明 |
|---|---|---|
| `config/openviking.yaml` | ✅ 已创建 | 端点、库 ID、命名空间、计费模型 |
| `config/providers.yaml` | ✅ 已扩展 | 新增 openviking profile |
| `.env.example` | ✅ 已创建 | `ARK_API_KEY=` 占位 |
| `.gitignore` | ✅ 已更新 | 新增 `.env` |
| `~/.openviking/ovcli.conf` | ✅ 已创建 | 目录此前不存在，无冲突，无需备份 |

## 2. 干跑结果

### 文件数统计

| 指标 | 值 |
|---|---|
| 总文件数 | **4,913** |
| 总字节 | 28,720,431 (27.4 MB) |
| 最大文件 | 2,499,578 bytes (narrative/world-0/mission-0.md) |
| 平均文件 | 5,845 bytes |
| 目录数 | 869 |

### 各卷分布

| 卷 | 文件数 | 字节 | 说明 |
|---|---|---|---|
| lore | 570 | 253,659 | 名词/泰坦/星神/星球，一条一文件 |
| books | 1,772 | 2,450,725 | 按系列分组，一本一文件 |
| characters | 259 | 1,147,808 | 按角色分组，profile/stories/voices |
| narrative | 1,419 | 4,073,376 | 按星球/任务分组 |
| dialogue | 299 | 18,938,689 | by-speaker（≥100 条）+ minor（分组） |
| artifacts | 590 | 1,385,692 | 光锥/遗器/道具/怪物 |
| rogue | 4 | 470,482 | 奇物/方程/其他 |

### 计费估算

| 费率 | 值 |
|---|---|
| 基础费率 | 5 AFP/小时 |
| 文件数 | 4,913（远低于 40,000 阈值） |
| 日成本 | 120 AFP/天 |
| 周成本 | 840 AFP/周 |

### 阈值检查

- 4,913 < 15,000（安全阈值）✅
- 4,913 < 40,000（计费阈值）✅
- 费率档位：5 AFP/小时，无额外加价

## 3. 脚本

| 脚本 | 状态 | 功能 |
|---|---|---|
| `scripts/openviking/plan.py` | ✅ | 干跑，输出 `work/ov_plan.json` |
| `scripts/openviking/push.py` | ✅ | 按 plan 上传，`--only`、`--dry-run`、`--live` |
| `scripts/openviking/status.py` | ✅ | 查询库状态（框架，需 API Key 实现） |
| `scripts/openviking/purge.py` | ✅ | 清空库，`--yes` 二次确认 |

## 4. 证据层扩展

`scripts/llm/client.py` 的 `calls.jsonl` 记录已新增字段：

| 字段 | 说明 |
|---|---|
| `tool_name` | 工具名（viking_search / viking_read / doubao_search） |
| `tool_type` | memory / search / model / evolution |
| `afp_cost` | AFP 消耗 |
| `retrieval_trace` | OpenViking 检索轨迹，原样存档 |
| `target_uri` | 命中路径 |

`manifest.json` 新增：按 `tool_type` 分类的调用次数与 AFP 小计。

## 5. 引证链路约束

**OpenViking 只做导航器，不做信源。** 检索走 OpenViking → 拿到 cite_id → 原文从 `work/cite_index.jsonl` 取 → 模型只能从这份原文里摘 quote。校验器保持精确子串检查不放松。

## 6. 发现的潜在问题

### 6.1 大文件

- `narrative/world-0/mission-0.md`：2.5 MB，17,673 条目。mission_id=0 的条目未归属到任何任务，建议在灌库前进一步拆分或标记为"未归属"。
- `dialogue/by-speaker/UNKNOWN.md`：834 KB，13,287 条目。UNKNOWN 说话人应进一步分类。

### 6.2 书籍系列名

部分 BookSeries 的系列名解析为 `{NICKNAME}`（如"NICKNAME小海豹战队选手变动公告"），需要在灌库前替换为"开拓者"。

### 6.3 narrative 未归属条目

world_id=0 的 narrative 条目有 17,673 条，占 narrative 卷的 47%。这些条目无法按星球分组，全部归入了 `world-0/mission-0.md`。建议灌库前标注为"未归属"或按 source_table 二次分组。

## 7. 交付清单

| 文件 | 说明 |
|---|---|
| `config/openviking.yaml` | OpenViking 接入配置 |
| `config/providers.yaml` | 扩展 openviking profile |
| `.env.example` | API Key 占位 |
| `scripts/openviking/plan.py` | 干跑脚本 |
| `scripts/openviking/push.py` | 推送脚本 |
| `scripts/openviking/status.py` | 状态查询 |
| `scripts/openviking/purge.py` | 清空脚本 |
| `work/ov_plan.json` | 干跑结果 |
| `logs/ov/` | 日志目录 |
| `scripts/llm/client.py` | 扩展日志字段 |
| `reports/10_openviking.md` | 本报告 |