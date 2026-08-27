"""Build Composer V0.4 research-grounded, project-authored knowledge packs.

The cards below are concise engineering summaries. They do not reproduce book
passages or copyrighted score excerpts. Published sources are recorded at the
pack level in the V0.4 registry and documentation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from build_composer_knowledge_v03 import MODES, PACK_ROOT, build_cards as build_v03_cards


PROVENANCE = "sera_original_research_summary_v04"
MELODY_MODES = ["theory_variation", "reharmonize"]


def _card(
    rule_id: str,
    domain: str,
    title: str,
    action: str,
    avoid: str,
    tags: list[str],
    *,
    modes: list[str] | None = None,
    priority: float = 0.82,
    hard: bool = False,
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "domain": domain,
        "title_zh": title,
        "action_zh": action,
        "avoid_zh": avoid,
        "styles": ["any"],
        "modes": modes or MELODY_MODES,
        "instruments": ["general"],
        "goals": tags,
        "meters": ["any"],
        "tags": tags,
        "priority": priority,
        "hard_constraint": hard,
        "provenance": PROVENANCE,
    }


EXPECTATION_RULES = [
    ("统计学习边界", "把听觉期待视为特定语料和风格中学得的概率倾向；候选排序应服从当前风格与上下文。", "避免把一种文化或体裁的常见模式宣称为普遍旋律定律。", ["melodic_expectation", "huron", "style conditioning"]),
    ("近距离延续", "默认优先搜索小音程延续，再把较大跳进保留给结构重音或动机身份。", "避免把级进率直接等同于审美质量，或禁止具有明确功能的大跳。", ["melodic_expectation", "proximity", "stepwise"]),
    ("音域中心回归", "旋律接近当前音域边缘后，优先测试向中位音区回归的后续走向。", "避免使用全曲固定音域中心；只依据当前乐句和声部统计。", ["melodic_expectation", "tessitura", "mean regression"]),
    ("跳进后转向", "大跳之后优先比较反向级进候选，并记录该选择是否同时缓解音域边缘压力。", "避免把跳后反向当作孤立心理法则；它也可能是有限音域的统计副作用。", ["melodic_expectation", "post-skip reversal", "tessitura"]),
    ("音域外扩警戒", "若大跳把旋律推向乐句极端音区，降低继续同向外扩候选的排序。", "避免仅凭一次大跳拒绝候选；检查后续是否有恢复路径。", ["melodic_expectation", "registral direction", "boundary"]),
    ("音区回返", "局部高点或低点出现后，在数个事件内寻找回返、停留或句法解释。", "避免要求机械回到完全相同的音高。", ["melodic_expectation", "registral return", "contour"]),
    ("空隙填充谨慎解释", "大跳后若反向填充部分音程空隙，可作为连贯性加分项而非硬规则。", "避免把 gap-fill 与跳后反向重复计分成两个独立证据。", ["melodic_expectation", "gap fill", "proxy"]),
    ("终点稳定性", "乐句末音同时结合调性稳定度、时值停驻和接近方向评估闭合感。", "避免只因末音属于主和弦就判定终止充分。", ["melodic_expectation", "closure", "tonal anchoring"]),
    ("强拍锚定", "在强拍和长时值位置提高结构音或可解释非和弦音的权重。", "避免让所有强拍都机械重复主音或和弦根音。", ["melodic_expectation", "metrical anchoring", "structure tone"]),
    ("非和弦音去向", "显著非和弦音应有邻接、经过、延留或明确色彩功能，并在局部得到解释。", "避免把每个半音都惩罚为错误，或把每个半音都解释成新和声。", ["melodic_expectation", "dissonance", "resolution"]),
    ("三全音后续", "旋律性三全音之后优先搜索短距离反向解决或和声上可解释的延宕。", "避免在没有和声语境时把所有三全音一律判为非法。", ["melodic_expectation", "tritone", "resolution"]),
    ("方向惯性限度", "短小级进可以维持方向形成动量；连续过长同向运动则检查是否缺少转折。", "避免把方向延续和方向改变同时设为不可调和的硬约束。", ["melodic_expectation", "directional inertia", "motion"]),
    ("单一结构高点", "短乐句优先保留一个最显著音域高点，并让接近与离开方式支持其句法角色。", "避免多个同强度极端高点稀释高潮，除非目标是序列或持续张力。", ["melodic_expectation", "climax", "arch"]),
    ("拱形作为语料倾向", "把中后段升高、末端回落作为一种可比较的轮廓候选，而非唯一正确形状。", "避免把西方民歌的拱形统计直接推广到所有风格。", ["melodic_expectation", "melodic arch", "phrase contour"]),
    ("句尾下降倾向", "在闭合目标下测试音区回落、较长末音和稳定级数的组合。", "避免要求开放式、问句式或上行终止也必须下降。", ["melodic_expectation", "declination", "phrase ending"]),
    ("重复建立预测", "先用可识别重复建立预测，再只改变结尾、重音或一个音程参数。", "避免在预测尚未建立前连续改写全部材料。", ["melodic_expectation", "prediction", "motif repetition"]),
    ("受控违背", "需要惊异时只违反一个已建立的期待维度，并用后续事件给出解释或新规则。", "避免随机偏离同时破坏调性、节奏、轮廓和织体。", ["melodic_expectation", "surprise", "controlled violation"]),
    ("不确定性与张力", "候选可通过延迟落点或增加局部不确定性累积张力，但应在计划位置降低不确定性。", "避免把持续不可预测当作持续高张力的可靠替代。", ["melodic_expectation", "tension", "uncertainty"]),
    ("预测与反应分离", "规划证据区分事前可预测性、事件当下反差与事后结构解释，不把它们压成单一分数。", "避免宣称一个代理指标完整复现 ITPRA 的心理与情绪反应。", ["melodic_expectation", "ITPRA", "auditability"]),
    ("风格词汇条件化", "以当前风格的音阶、半音率、惯用跳进和句法统计调整期待评分。", "避免用古典阈值直接惩罚爵士、调式或现代材料。", ["melodic_expectation", "style vocabulary", "conditioning"]),
    ("声部独立建模", "多声部乐谱先分别提取每条旋律线，再计算期待特征；不要按 XML 事件顺序混合声部。", "避免把同时发声的不同声部当成一条旋律产生伪大跳。", ["melodic_expectation", "voice separation", "polyphony"], {"priority": 0.92, "hard": True}),
    ("乐句边界重置", "在休止、终止、长时值或明确段落边界处弱化此前方向惯性的影响。", "避免让上一乐句末端的大跳永久约束下一乐句开头。", ["melodic_expectation", "phrase boundary", "reset"]),
    ("原谱相对改进", "编辑候选同时报告绝对期待分与相对原谱变化，优先避免新引入的明显问题。", "避免因原谱已有非常规写法而拒绝所有不新增问题的局部修改。", ["melodic_expectation", "baseline", "relative improvement"], {"priority": 0.9, "hard": True}),
    ("代理指标非审美结论", "把期待分用于发现塌缩、大跳未解决和弱收束，并保留人工试听与盲评边界。", "避免声称高期待分必然更好听或更有创意。", ["melodic_expectation", "evaluation", "human review"], {"modes": MODES, "priority": 0.95, "hard": True}),
]


TEXTURE_RULES = [
    ("织体是局部关系", "织体识别同时观察声部数量、密度、音区和声部交互，并限定在当前选区。", "避免用全曲单一标签覆盖局部织体变化。", ["texture", "local scope", "density"]),
    ("单声部识别", "仅有一个独立活动旋律线时标为 monophonic，并保留同度加倍可能造成的歧义。", "避免仅按谱表数量判断单声部或复调。", ["texture", "monophonic", "voice count"]),
    ("同节奏和弦织体", "多个声部攻击点高度同步且节奏轮廓相近时，优先识别为 homorhythmic_chordal。", "避免因偶然同时起音就把整段误判为齐奏式和弦。", ["texture", "homorhythmic_chordal", "onset alignment"]),
    ("旋律伴奏识别", "有明确主线角色，且其节奏或音区与支撑层形成对比时，识别为 melody_accompaniment。", "避免默认最高音永远是旋律；优先结合 track role 与持续显著度。", ["texture", "melody_accompaniment", "role"]),
    ("复调识别", "多条声部具有不同攻击模式与可追踪旋律连续性时，提高 contrapuntal 置信度。", "避免把分解和弦的单一功能层误判为独立复调。", ["texture", "contrapuntal", "rhythmic independence"]),
    ("异音歧义", "多声部轮廓高度相似但装饰与时值不完全一致时标记异音可能性并降低确定度。", "避免在缺乏旋律对应证据时强行标记 heterophony。", ["texture", "heterophony", "contour similarity"]),
    ("分层织体识别", "当多个角色持续共存但不满足齐奏或独立复调阈值时使用 layered，并列出角色证据。", "避免把 layered 当作无法分析时的无证据兜底。", ["texture", "layered", "functional layers"]),
    ("稀疏织体", "活动声部少、攻击间隔大且留白显著时标记 sparse 特征，但保留基本纹理类别。", "避免把休止较多直接等同于单声部。", ["texture", "sparse", "space"]),
    ("攻击点对齐率", "以精确拍位比较同时攻击比例，作为同节奏与和弦织体证据。", "避免用浮点近似误合并不同拍位。", ["texture", "onset alignment", "exact time"]),
    ("声部节奏相似度", "对声部攻击集合计算成对相似度，区分共同节奏与独立节奏。", "避免只比较音符总数而忽略攻击位置。", ["texture", "rhythmic similarity", "voice interaction"]),
    ("持续音局限", "符号分析应记录当前只建模攻击点；需要判断持续重叠时必须扩展时值区间分析。", "避免把攻击点分类结果描述成完整声学纹理。", ["texture", "sustain", "limitation"], {"priority": 0.9, "hard": True}),
    ("主线角色优先", "若 ScoreDocument track 已标记 lead_melody，应优先于简单最高音启发式。", "避免忽略宿主或用户已明确的声部角色。", ["texture", "lead_melody", "track role"], {"priority": 0.9, "hard": True}),
    ("主线显著度后备", "无角色元数据时综合右手倾向、音区、事件数量与连续性选择主线。", "避免仅凭单个最高音选择旋律。", ["texture", "salience", "fallback"]),
    ("音区分离", "主线与支撑层平均音区明显分离可加强旋律伴奏解释。", "避免把音区分离单独当作角色证明。", ["texture", "register separation", "melody_accompaniment"]),
    ("功能低音层", "最低持续或规律声部承担根音与拍点时标记 functional bass 角色。", "避免把偶然最低音一律视为独立低音层。", ["texture", "functional bass", "role"]),
    ("和声填充层", "中音区较同步、轮廓独立性较低的声部可标记 harmonic filler。", "避免让填充层在音区和节奏上持续遮蔽主线。", ["texture", "harmonic filler", "role"]),
    ("脉冲层", "重复攻击模式稳定强调拍层时标记 explicit beat 或 ostinato 功能。", "避免仅因重复音高就假设其承担节拍功能。", ["texture", "explicit beat", "ostinato"]),
    ("新奇层", "短暂插入、问答或异质材料应作为 novelty layer，而非持续主线。", "避免新奇层持续占据主线音区和最大密度。", ["texture", "novelty layer", "call response"]),
    ("主线与伴奏互补", "旋律活跃时降低支撑层节奏或音区竞争，旋律停顿时再允许伴奏填充。", "避免所有层同时达到最高活动度。", ["texture", "melody_accompaniment", "complementary rhythm"]),
    ("复调声部平衡", "独立声部保持可辨识轮廓，并用交错活动与音区规划避免长期遮蔽。", "避免用简单音量或音符数量解决全部复调平衡问题。", ["texture", "contrapuntal", "voice balance"]),
    ("同节奏写作", "块状和弦或赞美诗式段落让声部共享句法节奏，同时保持外声部方向与和声连接。", "避免只追求垂直和弦而忽略横向声部进行。", ["texture", "homorhythmic_chordal", "voice leading"]),
    ("分解和弦辨识", "若单一支撑声部按稳定顺序展开和弦音，将其识别为 arpeggiated accompaniment。", "避免把每个分解音都当作独立旋律。", ["texture", "arpeggiated", "accompaniment"]),
    ("织体转换准备", "改变织体前先减少或共享一个角色，再引入新的密度、音区或攻击关系。", "避免无过渡地同时改变所有声部角色。", ["texture", "transition", "form"]),
    ("织体峰值保留", "最厚织体只用于少数结构峰值，并在前后保留密度对比。", "避免全段持续同样厚度导致层次失效。", ["texture", "density arc", "climax"]),
    ("织体骨架保护", "当前 Composer 只改音高时，应验证声部、攻击点、时值和事件数量的织体骨架完全不变。", "避免把音高改写伪装成已经完成的结构性织体重配。", ["texture", "host scaffold", "protected scope"], {"priority": 0.96, "hard": True}),
    ("织体目标与源织体分离", "规划同时记录 source_texture 与 target_texture；若结构编辑不受支持，只能解释目标而不能假装实现。", "避免将 LLM 选择的目标织体误报为原谱识别结果。", ["texture", "source texture", "target texture"], {"priority": 0.94, "hard": True}),
    ("低置信度显示", "证据接近阈值或选区音符不足时显示 mixed/unknown 与具体指标。", "避免在证据不足时给出高置信度单一标签。", ["texture", "confidence", "unknown"], {"priority": 0.9, "hard": True}),
    ("织体非审美等级", "织体分类用于选择规则和检查保护，不把某类织体当作更高级或更好听。", "避免用分类标签替代风格、功能和人工判断。", ["texture", "evaluation", "human review"], {"modes": MODES, "priority": 0.95, "hard": True}),
]


COMPOSITION_RULES = [
    ("旋律骨架与装饰分层", "先确定强拍、长时值和句尾结构音，再在弱位加入经过、邻接或倚音。", "避免先随机生成表面音符再强行解释骨架。", ["composition_craft", "melody", "structure tone"]),
    ("轮廓与音程分离", "先规划上行、下行、拱形或波浪方向，再选择符合调性与可唱性的具体音程。", "避免轮廓和每个音程同时无约束变化。", ["composition_craft", "melody", "contour"]),
    ("局部音域预算", "为一个短句设定常用音域与少数越界高点，候选不得无目的持续扩张。", "避免把乐器总音域当作每个乐句都应使用的范围。", ["composition_craft", "melody", "tessitura"]),
    ("动机最小身份", "用节奏、音程符号或终止落点中的至少一项维持动机可识别性。", "避免变奏同时改掉全部身份参数。", ["composition_craft", "motif", "identity"]),
    ("序列的退出", "序列重复两至三次后改变结尾、缩短单元或转向终止，避免无限机械复制。", "避免把复制粘贴当作完整发展。", ["composition_craft", "sequence", "development"]),
    ("问答关系", "回答句保留开头身份并改变末端方向、和声功能或闭合强度。", "避免前后句完全相同而没有句法差异。", ["composition_craft", "question answer", "phrase"]),
    ("高潮稀缺", "一个短段落只设置一处最显著的音域、力度或密度峰值。", "避免多个参数在每小节都同时到顶。", ["composition_craft", "climax", "hierarchy"]),
    ("旋律呼吸", "在长时值、休止或较稳定音上形成可感知分组，并让边界与和声句法协调。", "避免把等长事件流误当作自然乐句。", ["composition_craft", "breath", "phrase"]),
    ("乐句呈示", "开头用短基本想法清楚建立调性、节拍与动机身份。", "避免开头立即堆叠过多变化导致身份不明。", ["composition_craft", "presentation", "sentence"]),
    ("乐句延伸", "中段可用碎片化、序列、加速和声节奏或提高音区推动离开稳定区。", "避免延伸段完全重复呈示而没有方向。", ["composition_craft", "continuation", "sentence"]),
    ("乐句结论", "结尾减少新材料，让旋律落点、低音与和声功能共同完成或保持开放。", "避免最后一拍才突然决定终止。", ["composition_craft", "conclusion", "cadence"]),
    ("周期句差异", "前句建立开放终止，后句共享材料并给出更强闭合。", "避免两个半句终止强度完全相同。", ["composition_craft", "period", "phrase"]),
    ("短选区比例", "一至八小节只规划能在该长度内听见的微型句法。", "避免为四小节片段宣称完整奏鸣曲或交响展开。", ["composition_craft", "proportion", "scope"], {"priority": 0.9, "hard": True}),
    ("对比参数限额", "制造对比时优先改变织体、音区、节奏密度或和声色彩中的一至两项。", "避免所有参数同时改变导致材料失去联系。", ["composition_craft", "contrast", "form"]),
    ("回归携带记忆", "回归材料至少保留核心动机，同时允许结尾、音区或伴奏密度产生获得感。", "避免逐字复制或完全无关的新材料冒充回归。", ["composition_craft", "return", "form"]),
    ("张力多参数协同", "用和声不稳定度、音区、密度与节奏压缩中的少数参数共同塑造张力。", "避免只靠逐渐变响制造全部方向。", ["composition_craft", "tension", "coordination"]),
    ("主功能起点", "闭合型调性乐句先建立主功能或稳定区域，再安排离开。", "避免在没有语境时直接把中间和弦当作终点。", ["composition_craft", "harmony", "tonic"]),
    ("前属到属", "需要明确终止时让前属功能准备属功能，再决定是否回归主功能。", "避免功能进行无目标地左右倒退。", ["composition_craft", "harmony", "predominant dominant"]),
    ("和声节奏分层", "稳定区保持较慢和声节奏，终止或延伸处再有目的地加快。", "避免每个旋律事件触发新和弦。", ["composition_craft", "harmonic rhythm", "phrase"]),
    ("共同音连接", "和声变化优先保留共同音，让其他声部走最短可解释路径。", "避免全部声部同时跳进制造无意重音。", ["composition_craft", "voice leading", "common tone"]),
    ("外声部方向", "旋律与低音尽量形成反向或斜向运动，以加强独立和清晰度。", "避免长期严格同向平行造成外声部粘连。", ["composition_craft", "outer voices", "contrary motion"]),
    ("低音定义功能", "优先让低音清楚支持根音、转位或经过功能，再安排上方色彩。", "避免用随机最低音造成错误和声暗示。", ["composition_craft", "bass", "harmonic function"]),
    ("内声部经济", "内声部以最短移动、共同音和受控半音连接维持和声连续性。", "避免内声部比旋律更频繁大跳或交叉。", ["composition_craft", "inner voices", "economy"]),
    ("终止不是和弦标签", "终止评估结合低音、旋律落点、节拍位置、时值与后续停顿。", "避免看到 V–I 标签就自动判定强终止。", ["composition_craft", "cadence", "multi cue"]),
    ("开放终止用途", "问句、延伸或悬念目标可以停在属功能、持续音或非主音稳定点。", "避免所有短句都强制完全终止。", ["composition_craft", "cadence", "open ending"]),
    ("非和弦音分类", "经过、邻接、延留和先现分别依据进入、离开与节拍位置判断。", "避免只按音级集合判断非和弦音是否合法。", ["composition_craft", "nonchord tone", "counterpoint"]),
    ("平行完全协和检查", "古典或严格对位目标下检查外声部连续平行五八度，并允许风格配置显式放宽。", "避免把体裁相关规则误作所有风格的硬禁令。", ["composition_craft", "parallel fifths", "style conditioning"]),
    ("声部交叉用途", "声部交叉只能作为短暂表达手段并保持身份可追踪；默认候选不新增交叉。", "避免持续交叉使声部角色不可辨认。", ["composition_craft", "voice crossing", "identity"], {"priority": 0.9, "hard": True}),
    ("节拍层级", "强拍承担结构落点，弱拍承担连接和装饰；切分后在句法关键点恢复拍感。", "避免所有细分位置获得同等结构重量。", ["composition_craft", "meter", "hierarchy"]),
    ("核心节奏单元", "建立一至两个可识别节奏单元，通过位移、截短或尾部变化发展。", "避免每小节随机更换节奏词汇。", ["composition_craft", "rhythm", "motif"]),
    ("密度弧线", "节奏密度随乐句方向变化，并在终止前选择加速推动或稀疏收束。", "避免全段保持同一活动度。", ["composition_craft", "rhythm", "density"]),
    ("复拍子分组", "六八等复拍子保留大拍三分结构，跨组节奏必须仍能听出分组支点。", "避免把复拍子机械当成快速三四拍。", ["composition_craft", "compound meter", "grouping"]),
    ("弱起与回收", "弱起材料应把重心导向后续强拍，并在句尾考虑相应时值回收。", "避免弱起只作为孤立装饰而破坏小节时值。", ["composition_craft", "anacrusis", "meter"]),
    ("钢琴双手角色", "钢琴写作先区分主线、低音和填充，再根据手型分配而非只按音高分手。", "避免左右手长期争抢同一音区与同一节奏密度。", ["composition_craft", "piano", "hand roles"], {"modes": MODES}),
    ("钢琴和弦间距", "低音区采用较宽间距，中高音区可适度密集并保持旋律突出。", "避免低音区紧密堆叠造成浑浊。", ["composition_craft", "piano", "voicing"], {"modes": MODES}),
    ("钢琴手型连续", "连续和弦优先保持共同音与相近手型，大跨度转换应留出时间或分解路径。", "避免理论上可按但连续动作代价过高。", ["composition_craft", "piano", "playability"], {"modes": MODES, "priority": 0.9, "hard": True}),
    ("踏板非修复工具", "延音踏板只服务共鸣与连接，和声混浊或断裂声部不能依赖踏板掩盖。", "避免用踏板替代正确时值和声部进行。", ["composition_craft", "piano", "pedal"], {"modes": MODES}),
    ("配器角色先于乐器名", "先确定主线、低音、和声填充、脉冲和色彩角色，再选择乐器与加倍。", "避免先罗列乐器后再寻找其功能。", ["composition_craft", "orchestration", "role"], {"modes": MODES}),
    ("音色交接连续", "旋律换乐器时使用共同音、短暂重叠或相邻音区保持听觉连续。", "避免无准备的远距离音色切换。", ["composition_craft", "orchestration", "handoff"], {"modes": MODES}),
    ("审美代理边界", "自动规则只用于检查结构一致性和常见失败；最终创作质量需试听、演奏与盲评。", "避免以理论规则数量或综合分直接宣称作品质量。", ["composition_craft", "evaluation", "human review"], {"modes": MODES, "priority": 0.96, "hard": True}),
]


def _materialize(rows: list[tuple[Any, ...]], prefix: str, domain: str) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        title, action, avoid, tags, *options = row
        kwargs = options[0] if options else {}
        cards.append(_card(f"KB-{prefix}-{index:03d}", domain, title, action, avoid, tags, **kwargs))
    return cards


def build_cards() -> dict[str, list[dict[str, Any]]]:
    packs = build_v03_cards()
    packs.update(
        {
            "melodic_expectation": _materialize(EXPECTATION_RULES, "EXPECT", "melodic_expectation"),
            "texture_structure": _materialize(TEXTURE_RULES, "TEXTURE", "texture"),
            "composition_craft": _materialize(COMPOSITION_RULES, "CRAFT", "composition_craft"),
        }
    )
    return packs


def write_packs(output_root: Path = PACK_ROOT) -> dict[str, int]:
    output_root.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for pack_name, cards in build_cards().items():
        target = output_root / f"{pack_name}.jsonl"
        target.write_text(
            "\n".join(json.dumps(card, ensure_ascii=False, sort_keys=True) for card in cards) + "\n",
            encoding="utf-8",
        )
        counts[pack_name] = len(cards)
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Composer V0.4 knowledge JSONL packs.")
    parser.add_argument("--output", type=Path, default=PACK_ROOT, help="Output directory for JSONL packs.")
    args = parser.parse_args()
    counts = write_packs(args.output)
    print(json.dumps({"status": "built", "packs": counts, "total_cards": sum(counts.values())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
