# 项目时间线

## 2026-08-06

- **12:45** 项目启动。创建 hsr-lore 目录结构，Python 3.14.5 + Git 2.54.0，venv 就位，磁盘 685GB 可用。
- **12:50** 上游数据仓库消失。原 Dimbreath/StarRailData 仓库已迁移至 DimbreathBot/TurnBasedGameData，GitHub HTTPS 不通（HTTP 451/443），改用 GitLab 镜像 jianghanxia1/StarRailData（2024-06-17 版本）。
- **13:02** 抽取脚本克隆完成。mrzjy/StarrailDialog（2024-07-12），作者已两年未维护。
- **13:20** 数据源更新。发现 GitLab 镜像是死镜像，换到 DimbreathBot/TurnBasedGameData（2026-07-29，4.4.0），通过 SSH 克隆。确认翁法罗斯（2016 次）、黄金裔（993 次）等 3.x 关键词存在。
- **13:43** 抽取脚本失效。StarrailDialog 依赖 dict 格式数据，新仓库全部改为 list，`items.items()` 崩溃。判定脚本已失效，需要自研抽取器。
- **14:00** 字段普查开始。ExcelOutput 2,140 文件，275 个含 Hash 字段。Story 5,358 文件，播放节点类型大改（PlayAndWaitSimpleTalk 消失）。
- **14:20** 跨表关联确认。Story 文件名 → MainMissionID → WorldID → BookSeriesWorld → 星球名，294 个目录中 290 个（98.6%）可归属。
- **15:00** 全字段文本体量排序。TalkSentenceConfig 5,886,916 字符排第一。TalkSentenceID 前缀匹配方案不成立（9.6%），正确归属通过 Story 文件。
- **15:15** 遗漏表补查。发现 LocalbookConfig（书籍正文）、StoryAtlas（角色故事）、VoiceAtlas（语音）、MessageItemConfig（短信）等 20+ 个高价值表。
- **16:00** 语料抽取器 v1。白名单驱动，7 卷输出，231,104 条，~5.7M token。三项验收：反查 28/30、残留 0.2%、幂等通过。
- **17:00** 角色名误判事件。上一轮将 1014-1017 标注为「吉尔伽美什、Saber、远坂凛、间桐樱」并排除，但实际未读取 AvatarConfig。1014-1017 不在 AvatarConfig 中，角色名是凭 VoiceAtlas 台词推断的。修正为「AvatarID 不在 AvatarConfig」作为唯一判据。
- **17:15** cite_id 行号隐患。SKIP 最初用 PerformanceID 做 cite_id，发现不唯一。提议用 row_index，被否决——行号依赖顺序，上游更新即失效。改为 PerformanceType+PerformanceID 组合键。全局约束确立：cite_id 每个组成部分必须来自数据内容本身。
- **17:20** 隔离而非删除通则。Fate 联动内容不再物理删除，改为隔离到 excluded_ip.jsonl。speakerless 对话（65,511 条）同样隔离。通则确立：语料工程只做标记不做删除。
- **17:30** 语料最终修正。cite_id 全部唯一（231,109 条硬断言），反查 100/100 通过，幂等 10 文件 MD5 一致。主卷 7,608,043 字符，隔离卷 speakerless 65,511 条 + excluded_ip 229 条。
- **18:00** 并行准备。模型调用抽象层、证据日志、前端骨架、素材归档、验证集脚手架就位。