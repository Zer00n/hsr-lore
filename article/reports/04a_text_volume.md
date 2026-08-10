# 任务一：全字段文本体量排序

> 遍历 ExcelOutput 下 275 个含 Hash 字段的文件，对每个 (文件, 字段) 二元组解析所有 Hash 为中文，统计文本量后按总字符数降序排列。
> 完整排序结果（所有二元组）见 `work/text_volume_full.json`。

## 前 80 行

| Rank | 文件 | 字段 | 非空条数 | 总字符数 | 平均 | 中位 | 最长样例（前 80 字） |
|---|---|---|---|---|---|---|---|
| 1 | TalkSentenceConfig.json | TalkSentenceText | 231,281 | 5,886,916 | 25.5 | 21 | 唔…我记得，乐谱应该是「<color=#ffffffff><icon SpriteName=EmojiFiveDimFluteArrow7 |
| 2 | AvatarSkillConfig.json | SkillDesc | 6,509 | 1,362,751 | 209.4 | 189 | 绯英获得等同于暴击伤害<unbreak>#5[i]%</unbreak>的欢愉度。绯英获得能量时，将同步获得等值 |
| 3 | GridFightFrontSkill.json | SkillDesc | 3,587 | 1,341,048 | 373.9 | 342 | 绯英获得等同于暴击伤害<color=#f29e38ff><unbreak>#5[i]%</unbreak></color>的欢愉 |
| 4 | LocalbookConfig.json | BookContent | 1,051 | 941,323 | 895.6 | 807 | 《随花束附赠的花语手册》正文… |
| 5 | SubMission.json | DescrptionText | 8,526 | 597,109 | 70.0 | 62 | 致未来的无名客… |
| 6 | GridFightFrontSkill.json | SimpleSkillDesc | 3,587 | 459,883 | 128.2 | 108 | 进入战斗时，大丽花恢复能量… |
| 7 | RogueMazeBuff.json | BuffDesc | 1,795 | 246,721 | 137.4 | 126 | 【<u>怀疑</u>】达到… |
| 8 | StoryAtlas.json | Story | 446 | 215,814 | 483.9 | 478 | 小时候，父亲总告诉格妮薇儿… |
| 9 | PerformanceSkipOverride.json | Desc | 3,866 | 209,680 | 54.2 | 55 | 据猎犬家系成员的证言… |
| 10 | MessageItemConfig.json | MainText | 12,858 | 205,409 | 16.0 | 13 | 我是「枘凿六合」秘密结社… |
| 11 | MonsterConfig.json | MonsterIntroduction | 2,590 | 174,762 | 67.5 | 67 | 满愿电视台的台长… |
| 12 | StatusConfig.json | StatusDesc | 2,225 | 165,572 | 74.4 | 60 | 弱点记录… |
| 13 | EquipmentSkillConfig.json | SkillDesc | 825 | 162,960 | 197.5 | 170 | 使装备者的速度提高… |
| 14 | GridFightBackBESkillConfig.json | SkillDesc | 438 | 138,997 | 317.3 | 303 | 绯英获得等同于暴击伤害… |
| 15 | MonsterSkillConfig.json | SkillDesc | 3,052 | 135,119 | 44.3 | 33 | 【兵戈扰攘的常胜军】… |
| 16 | MazeBuff.json | BuffDesc | 1,051 | 134,854 | 128.3 | 122 | 攻击敌方目标时额外对目标造成… |
| 17 | MazeBuff.json | BuffDescBattle | 1,051 | 134,854 | 128.3 | 122 | 同上 |
| 18 | VoiceAtlas.json | Voice_M | 5,236 | 123,197 | 23.5 | 14 | I am the bone of my sword… |
| 19 | TutorialGuideData.json | DescText | 1,516 | 120,564 | 79.5 | 72 | <color=#f29e38ff>妖火</color>… |
| 20 | ItemConfig.json | ItemBGDesc | 2,099 | 119,805 | 57.1 | 42 | 在混沌未分的荒原上… |
| 21 | StageConfig.json | StageName | 24,522 | 113,741 | 4.6 | 4 | 冥魂渡者，死龙残躯… |
| 22 | SubMission.json | TargetText | 8,624 | 91,365 | 10.6 | 10 | 根据「花火妙妙藏宝图」找到炸弹… |
| 23 | AvatarServantSkillConfig.json | SkillDesc | 420 | 81,720 | 194.6 | 198 | 整场生效，对白厄施放后… |
| 24 | RogueMiracleEffect.json | MiracleDesc | 1,013 | 81,029 | 80.0 | 71 | 「量子」属性角色施放战技后… |
| 25 | EvoBdSCMazeBuff.json | BuffDesc | 261 | 78,659 | 301.4 | 283 | 召唤速度为… |
| 26 | EvoBdSCMazeBuff.json | BuffDescBattle | 261 | 78,659 | 301.4 | 283 | 同上 |
| 27 | MappingInfo.json | Desc | 1,651 | 78,002 | 47.2 | 48 | 在二相乐园，人类虚构而出的事物… |
| 28 | AvatarSkillConfigLD.json | SkillDesc | 283 | 71,532 | 252.8 | 266 | 吉尔伽美什或Saber攻击时… |
| 29 | IntroData.json | Desc_Os | 211 | 69,130 | 327.6 | 222 | ◆ 末日幻影 ◆… |
| 30 | IntroData.json | Desc | 211 | 69,020 | 327.1 | 222 | 同上 |
| 31 | RogueTournFormulaDisplay.json | FormulaStory | 300 | 68,645 | 228.8 | 226 | 完成唱名后，肉眼可见的丧气… |
| 32 | GridFightSkillDescMod.json | ModifySkillDesc | 155 | 68,562 | 442.3 | 447 | 敌方目标在进入战斗时… |
| 33 | TarotBookSentence.json | Sentence | 1,437 | 68,334 | 47.6 | 42 | 「这还用问？当然是为了拖堂。」… |
| 34 | ActivityPanel.json | IntroDesc | 242 | 67,712 | 279.8 | 154 | ◆ 货币战争 ◆… |
| 35 | LimaoNewsInterviewContent.json | ANECPHCPLPP | 670 | 64,461 | 96.2 | 61 | 「火花大会」结束的一小时后… |
| 36 | EvolveBuildMazeBuff.json | BuffDesc | 200 | 61,844 | 309.2 | 332 | 召唤速度为… |
| 37 | EvolveBuildMazeBuff.json | BuffDescBattle | 200 | 61,844 | 309.2 | 332 | 同上 |
| 38 | AchievementData.json | AchievementDesc | 1,869 | 61,222 | 32.8 | 28 | 多事… |
| 39 | RogueMazeBuff.json | BuffSimpleDesc | 1,679 | 61,024 | 36.3 | 28 | 我方目标施放攻击后… |
| 40 | RogueMagicUnit.json | MagicUnitDesc | 277 | 51,753 | 186.8 | 156 | 【扩散】对韧性值最低的… |
| 41 | AvatarStatusConfig.json | StatusDesc | 723 | 49,100 | 67.9 | 58 | 火属性抗性穿透提高… |
| 42 | PixAirSkillConfig.json | Desc | 309 | 45,946 | 148.7 | 114 | 改装：当其他装备触发… |
| 43 | FateMazeBuff.json | BuffDesc | 254 | 45,754 | 180.1 | 178 | 我方目标受到攻击后… |
| 44 | ChimeraDuelSkill.json | Description | 260 | 44,212 | 170.0 | 155 | 队伍中最强的燕麦粥被击倒时… |
| 45 | NounAtlas.json | NounDesc | 99 | 44,090 | 445.4 | 387 | 「在宇宙的中心有一团火种…」 |
| 46 | GridFightBackBESkillConfig.json | SimpleSkillDesc | 438 | 43,955 | 100.4 | 80 | 进入战斗时… |
| 47 | AvatarSkillConfigLD.json | SimpleSkillDesc | 278 | 42,600 | 153.2 | 126 | 进入战斗时… |
| 48 | QuestData.json | QuestTitle | 2,369 | 41,933 | 17.7 | 15 | 在「{TextID#UIText_GridFight_Name}」中… |
| 49 | RogueDialogueOptionDisplay.json | OptionDesc | 2,174 | 41,909 | 19.3 | 17 | 10%概率获得… |
| 50 | MonsterStatusConfig.json | StatusDesc | 656 | 40,616 | 61.9 | 57 | 目标已累积【负载生命值】… |
| 51 | AvatarSkillConfig.json | SkillName | 6,744 | 40,248 | 6.0 | 6 | 驻「我」华庭，授予至勋 |
| 52 | LimaoNewsPost.json | KJGJGNLACKF | 79 | 39,843 | 504.3 | 473 | #毁灭大讲堂#… |
| 53 | RogueMiracleDisplay.json | MiracleBGDesc | 249 | 39,302 | 157.8 | 158 | 武装考古学派乃是博识学会的一朵奇葩… |
| 54 | IdleLiveChatContent.json | Content | 4,209 | 38,344 | 9.1 | 8 | 给你打50，够了吗？ |
| 55 | ClockParkCardAction.json | CardDesc | 738 | 38,064 | 51.6 | 51 | 钟表小子说服了果树姑娘… |
| 56 | ChimeraDuelSkill.json | PlainDescription | 260 | 36,990 | 142.3 | 134 | 队伍中最强的燕麦粥被击倒时… |
| 57 | RogueMazeBuff.json | BuffDescBattle | 320 | 36,964 | 115.5 | 107 | 角色发动追加攻击后… |
| 58 | ChronicleConclusion.json | MissionConclusion | 428 | 36,961 | 86.4 | 78 | 你与昔涟回到了第一次逐火之旅… |
| 59 | AvatarServantSkillConfig.json | SimpleSkillDesc | 440 | 34,490 | 78.4 | 82 | 对我方单体角色施加增益效果… |
| 60 | GridFightAugment.json | HexDesc | 334 | 33,421 | 100.1 | 82 | 你的… |
| 61 | GridFightServantSkill.json | SkillDesc | 92 | 31,469 | 342.1 | 208 | 造成…次伤害… |
| 62 | EvolveBuildMazeBuff.json | BuffSimpleDesc | 181 | 29,841 | 164.9 | 159 | 获得和升级【永恒之心】时… |
| 63 | VoiceAtlas.json | VoiceTitle | 5,236 | 29,547 | 5.6 | 5 | 关于自己•「LV.999」卡带 |
| 64 | TextJoinItem.json | TextJoinText | 456 | 29,089 | 63.8 | 7 | 在过去的动画故事里… |
| 65 | ItemConfigRelic.json | ItemBGDesc | 742 | 29,032 | 39.1 | 35 | 位面球封装的是翁法罗斯的神悟树庭… |
| 66 | LimaoNewsComment.json | DNJCIDFBHPC | 1,302 | 28,729 | 22.1 | 15 | 哈哈，看得出来小狸猫们… |
| 67 | ItemComefrom.json | Desc | 2,300 | 28,653 | 12.5 | 12 | 拟造花萼… |
| 68 | ItemConfigEquipment.json | ItemBGDesc | 165 | 28,523 | 172.9 | 157 | 阿斯德纳星系的边缘… |
| 69 | ItemConfigDisk.json | ItemDesc | 255 | 27,399 | 107.4 | 109 | 能在列车的留声机上播放的碟片… |
| 70 | ItemCureInfoData.json | CureInfoDesc | 85 | 24,789 | 291.6 | 138 | 第1回：丹鼎司浩劫终难逃… |
| 71 | EvoBdSCMazeBuff.json | BuffSimpleDesc | 199 | 24,660 | 123.9 | 130 | 我方目标和武器攻击… |
| 72 | ILBattleAvatarSkill.json | SkillDesc | 122 | 23,454 | 192.2 | 186 | 我方前台角色施放普攻时… |
| 73 | RogueTournMiracleDisplay.json | MiracleBGDesc | 135 | 20,984 | 155.4 | 156 | 在混沌医师的诸多药剂里… |
| 74 | BookSeriesConfig.json | BookSeriesComments | 721 | 20,526 | 28.5 | 29 | 从阿克蒙手中… |
| 75 | HeliobusComment.json | HeliobusCommentTextID | 909 | 20,145 | 22.2 | 17 | 所以我只能说懂得都懂… |
| 76 | LoadingDesc.json | DescTextmapID | 403 | 20,074 | 49.8 | 49 | 翁法罗斯世代更迭的形式… |
| 77 | GridFightFrontSkill.json | SkillName | 3,587 | 20,016 | 5.6 | 5 | 驻「我」华庭，授予至勋 |
| 78 | RogueDialogueOptionDisplay.json | OptionTitle | 2,182 | 19,621 | 9.0 | 8 | 直接挑衅… |
| 79 | RogueMagicUnit.json | MagicUnitSimpleDesc | 277 | 19,486 | 70.3 | 67 | 【集中】对当前韧性值最低的… |
| 80 | ExtraEffectConfig.json | ExtraEffectDesc | 307 | 18,715 | 61.0 | 46 | 「银狼LV.999」持有【好活当赏】时… |

## 关键观察

1. **TalkSentenceConfig 是绝对的第一大文本源**（5,886,916 字符），超过第二名（技能描述）4 倍以上
2. 书籍正文（LocalbookConfig.BookContent）排第 4，平均 895 字符/条，是平均长度最长的叙事文本
3. 角色故事（StoryAtlas.Story）排第 8，平均 483 字符/条
4. 技能描述类（SkillDesc）在排名中大量出现，但属于战斗系统文本，对世界观考据价值有限
5. 手机短信（MessageItemConfig.MainText）排第 10，12,858 条，但平均仅 16 字符/条
6. 角色语音（VoiceAtlas.Voice_M）排第 18，5,236 条，平均 23.5 字符/条
7. 名词百科（NounAtlas.NounDesc）排第 45，99 条但平均 445 字符/条，单位文本价值极高
8. 光锥背景故事（ItemConfigEquipment.ItemBGDesc）排第 68，165 条，平均 173 字符/条