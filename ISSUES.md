# ISSUES

## 阶段二：数据源拉取

### 尝试 1：GitHub 直连 — 失败

- 时间：2026-08-06
- 仓库：`https://github.com/Dimbreath/StarRailData.git`
- 错误：`Failed to connect to github.com port 443 after 21116 ms: Could not connect to server`
- 结论：网络不通，尝试备选方案

### 尝试 2：GitLab 镜像 — 成功

- 时间：2026-08-06
- 仓库：`https://gitlab.com/jianghanxia1/StarRailData.git`
- 结果：克隆成功，commit `df89dd11`（2024-06-17）
- 注意：此镜像数据版本为 2024-06-17，可能滞后于最新游戏版本
- 后续：已被新仓库 DimbreathBot/TurnBasedGameData 取代

---

## 数据源更新

### 尝试 1：GitHub HTTPS — 失败

- 时间：2026-08-06
- 仓库：`https://github.com/DimbreathBot/TurnBasedGameData.git`
- 错误：`Recv failure: Connection was reset`
- 结论：HTTPS 不通

### 尝试 2：GitHub SSH — 成功

- 时间：2026-08-06
- 仓库：`git@github.com:DimbreathBot/TurnBasedGameData.git`
- 结果：克隆成功，commit `648b08fb`（2026-07-29，版本 4.4.0）

### 尝试 3：GitLab 镜像搜索 — 发现

- 在 GitLab 搜索到 `Dimbreath/turnbasedgamedata`（16 forks，56 stars，活跃至 2026-07-29）
- 作为备选方案，未使用

### 冒烟测试：get_misc.py 崩溃

- 错误：`AttributeError: 'list' object has no attribute 'items'`
- 根因：新数据 ExcelOutput 全部为 list 格式（2140/2140），脚本期望 dict
- Hash 查找验证：50/50 命中，兼容
- 判定：脚本已失效，需要自写抽取器