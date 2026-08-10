# 第六轮修正

> 两条报告纪律沿用。所有数字由脚本生成，数据来源标注文件路径。

---

## 一、speakerless 重新分类

**数据来源：** `work/speakerless_classified.json`
**生成脚本：** `scripts/r2_classify_speakerless.py`

### 分类规则

按顺序判定，先匹配先归类：

| 类别 | 规则 |
|---|---|
| placeholder | 长度 < 4 字符、全标点、或短括号包裹（≤10 字符） |
| narration | 以「你/你们/您/诸位」开头（二人称），或角色名 + 标点 + 动作动词（三人称），或以叙述标记词开头（这时/忽然/在/沿着/一阵/眼前等） |
| ui_system | 以祈使命令词开头（请选择/点击/返回/确认/取消/前往/探索等） |
| unclassified | 以上均不匹配 |

### 分类结果

总计 65,450 条：

| 类别 | 条数 | 占比 |
|---|---|---|
| placeholder | 3,026 | 4.6% |
| narration | 10,250 | 15.7% |
| ui_system | 191 | 0.3% |
| unclassified | 51,983 | 79.4% |

### 各类别 30 条样例

见 `work/speakerless_classified.json` 的 `samples` 字段。

### narration 样例（前 10）

```
[TALK-802410000] 让时间回到三月七刚开始学剑的时候……
[TALK-802410032] 你这人满脑子都是幻戏呢。
[TALK-802410125] 你们公司的机甲只会搞团建。
[TALK-802410608] 你怎么就断言我肯定没问题…
[TALK-802410916] 你拿上弓箭的话，应该有胜算。
[TALK-802410918] 你休息的时候，机甲却在锻炼。
[TALK-802411128] 你真是三月七吗？
[TALK-802411208] 彦卿师父，你是不想教了？
[TALK-802411507] 你在这里遭遇了事业的挫折。
[TALK-802411523] 你应该堂堂正正拿回你的尊严！
```

### 待确认

1. narration 的 10,250 条是否可以纳入 `corpus/narration.jsonl`？
2. unclassified 的 51,983 条主要是对话片段（"确实，不愧是咱家的三月七。"等），性质为无归属角色对白，建议维持隔离
3. 分类规则中角色名检测依赖 5,215 个角色名，三人称叙述检测可能偏保守

**等确认后再执行语料迁移。**

---

## 二、R1 三项修正

**数据来源：** `work/r1_fixes.json`
**生成脚本：** `scripts/r1_fixes.py`

### 1. 61 条关键词排除的原文

全部 61 条的完整 `clean` 文本已输出到 `work/r1_fixes.json` → `fix1_keyword_excluded.full_entries`。

**关键事实：**
- 61 条全部为 `keyword-only`，不重叠 speaker 判据或 mission 判据
- 文本包含 Fate 特有术语：圣杯战争、从者、御主、令咒、职阶、Rider/Caster/Assassin/Berserker
- 内容性质为 narrator 旁白（`speaker_status: absent`），描述 Fate 联动活动的叙事场景
- 例句：「你的思绪渐渐回溯到了那场『圣杯战争』伊始」「以矜持而优雅的姿态，两位从者将桌上的天环翅堡一扫而空」「幻造圣杯战争 尾声」

### 2. 三件 artifact 排除

| cite_id | 来源 | 完整内容摘要 |
|---|---|---|
| ITEM-250608 | ItemConfig | 仿造令咒制作的水晶浮雕，铭刻着英雄的往昔。 |
| ITEM-140615 | ItemConfig | 二相乐园同好圈子里相当知名的奇幻动作视觉小说。题材与《Fate/stay night》高度相似，但出于某些大人的原因绝对无关。 |
| EQUP-B-23061 | ItemConfigEquipment | 光锥《星火悄然闪耀》——全文描写远坂凛成为魔法使的心路历程。 |

### 3. 对账

```
229  (VoiceAtlas, AvatarID not in AvatarConfig)
1377 (TalkSentenceConfig, speaker-based)
  61 (TalkSentenceConfig, keyword-based)
  23 (TalkSentenceConfig, mission-based)
   4 (TalkSentenceConfig, composite speaker)
   3 (ItemConfig + ItemConfigEquipment)
─────
1697 = 1697 ✅ 完全对平
```

之前的 1,377+61+23=1,461 少算了 4 条 composite speaker。

### 4. 复合说话人标注

全部 4 条确认 `composite speaker` 标注：

| cite_id | speaker | exclusion_reason |
|---|---|---|
| TALK-154030610 | 遐蝶&远坂凛 | composite speaker (遐蝶&远坂凛) |
| TALK-154040019 | 远坂凛&Saber | composite speaker (远坂凛&Saber) |
| TALK-154040220 | 远坂凛&Saber | composite speaker (远坂凛&Saber) |
| TALK-154150156 | 白厄&Saber | composite speaker (白厄&Saber) |

---

## 三、清洗残留修复 ✅

**数据来源：** `work/cleaning_fix_report.json`
**生成脚本：** `scripts/fix_residuals.py`

### 修复内容

| 问题 | 数量 | 修复方式 | 修复后 |
|---|---|---|---|
| `\n` 转义未转换 | 19 条（188 处），全部在 books/LocalbookConfig.BookContent | `\\n` → `\n` | 0 |
| `{TEXTJOIN#N}` 残留 | 4 条，在 dialogue | 正则删除 `{TEXTJOIN...}` 标签 | 0 |
| `{NICKNAME}` 未替换 | 1 条，在 books/BOOK-190729 | 替换为「开拓者」 | 0 |

### 验证结果

```
verify 100/100:         ✅ PASS
cite_id 唯一性:          ✅ 229,702 全部唯一
幂等测试 MD5:            ✅ 10 文件全匹配（新基线已保存）
fixtures 校验:          ✅ 22/22 合规 + 16/16 违规（未变化）
```

---

## 四、灌库覆盖率验证

**脚本：** `scripts/openviking/coverage.py`

### 功能

```
python scripts/openviking/coverage.py --dry-run    # 输出预期 URI 清单
python scripts/openviking/coverage.py --check       # 验证每个 URI 可读且可检索
python scripts/openviking/coverage.py --check --repush  # 重推缺失文件
```

### 干跑结果

预期 URI 总数：4,641（与 ov_plan.json 一致）

### 使用方式（正式灌库后）

```bash
# 1. 灌库完成后立即运行
python scripts/openviking/coverage.py --check
# 2. 查看缺失清单
cat work/ov_coverage.json
# 3. 如有缺失，重推
python scripts/openviking/coverage.py --check --repush
```

### 限制

coverage 脚本需要库中有实际文件才能验证。当前库为空，无法做实检。正式灌库后立即运行。

---

## 五、溯源链指标修正 ✅

**文件：** `scripts/llm/client.py` `log_provenance` 方法  
**测试：** `scripts/llm/test_provenance.py`

### 变更

| 旧字段 | 新字段 | 含义 |
|---|---|---|
| `precision` | `citation_yield` | cited / fetched —— 拉取的引证中被实际引用的比例 |
| `recall` | `hit_utilization` | 贡献了引证的 URI 数 / 唯一命中 URI 数 |
| _(删除)_ | — | cited+fetched-unused 恒等关系已消除 |

### Mock 测试结果

```
[step-001] 纳努克与毁灭命途的关系 → citation_yield=67% hit_util=100%
[step-002] 匹诺康尼的家族势力 → citation_yield=60% hit_util=100%
[step-003] 雅利洛-VI的寒潮起源 → citation_yield=50% hit_util=100%
All 3 records pass structure check. ✅
```

---

## 六、lore/loading 按 ID 切分 ✅

**实现：** `scripts/openviking/plan.py`（已更新 loading 段）

403 条 LoadingDesc 按 `source_pk` 升序排列，每 30 条一个文件，文件名用 ID 区间。

### 结果

403 条 → **14 个文件**（原 1 个大文件）：

```
lore/loading/00001-00030.md   ← LOAD-1 到 LOAD-1030
lore/loading/00031-00060.md   ← LOAD-1031 到 LOAD-1060
...
lore/loading/00391-00403.md   ← LOAD-1391 到 LOAD-1403
```

总文件数：4,641（lore/loading 从 1 个拆为 14 个，+13）

---

## 交付清单

| 文件 | 说明 |
|---|---|
| `scripts/r2_classify_speakerless.py` | speakerless 分类脚本 |
| `work/speakerless_classified.json` | 分类结果（含各 30 条样例） |
| `scripts/r1_fixes.py` | R1 三项修正脚本 |
| `work/r1_fixes.json` | 61 条完整原文 + artifact 详情 + 对账 |
| `scripts/fix_residuals.py` | 清洗残留修复脚本 |
| `work/cleaning_fix_report.json` | 修复前后对比 |
| `work/corpus_hashes.json` | 新 MD5 基线 |
| `scripts/openviking/coverage.py` | 灌库覆盖率验证（干跑模式已验证） |
| `scripts/llm/client.py` | citation_yield + hit_utilization（删除 precision/recall） |
| `scripts/llm/test_provenance.py` | 溯源链测试（通过） |
| `scripts/openviking/plan.py` | loading 改 ID 区间切分 |
| `work/ov_plan.json` | 新干跑结果（4,641 文件） |
| `reports/17_fixes_v6.md` | 本报告 |

## 等待确认

- **一的分类结果**——narration 10,250 条是否创建 `corpus/narration.jsonl`？
- **二之 1**——61 条关键词排除是否全部退回主语料？（内容均为 Fate 联动叙事旁白，无角色说话人）
