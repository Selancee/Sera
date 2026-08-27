"""Build the project-authored Composer V0.3 atomic knowledge packs.

The generated cards are engineering summaries written for Sera.  They do not
contain copied book passages or copyrighted score excerpts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
KB_ROOT = ROOT / "sera_edit" / "composer" / "style_kb"
PACK_ROOT = KB_ROOT / "packs"
PROVENANCE = "sera_original_engineering_summary_v03"
MODES = ["theory_variation", "reharmonize", "orchestration_advice"]


CORE_PRINCIPLES = [
    ("motif", "动机身份", "先保留最短可辨识音程轮廓，再改变终止音或局部方向。", "避免同时改写轮廓、节奏与落点，使动机失去身份。", ["motif", "旋律", "identity"]),
    ("motif", "动机发展", "一次只采用移位、倒影提示、截短或回答句中的一种主要发展手法。", "避免在短乐句中堆叠过多发展技术。", ["motif", "development", "sequence"]),
    ("phrase", "乐句呼吸", "在目标范围内建立起点、延伸、峰值与收束四个可感知阶段。", "避免每一小节都使用相同密度和重音。", ["phrase", "arc", "乐句"]),
    ("phrase", "高潮位置", "短乐句通常让峰值晚于中点，并给终止留出回落空间。", "避免最高音和最强力度机械地落在最后一个事件。", ["climax", "tension", "高潮"]),
    ("melody", "级进骨架", "以级进维持可唱性，把跳进留给结构性强调。", "避免连续同向大跳且没有反向补偿。", ["melody", "stepwise", "可唱性"]),
    ("melody", "跳进补偿", "大跳之后优先反向级进，或在和弦音上稳定停留。", "避免大跳后继续同向扩张音域。", ["leap", "compensation", "旋律"]),
    ("harmony", "和声节奏", "先决定和声变化速度，再选择具体和弦；终止前可以适度加快。", "避免每个音符都触发新的和声解释。", ["harmony", "harmonic rhythm", "和声节奏"]),
    ("harmony", "功能清晰度", "用稳定区、离开区、属功能区和回归区组织短段落。", "避免无目标地罗列和弦。", ["harmony", "function", "cadence"]),
    ("harmony", "非和弦音", "经过音、邻音和延留音必须能由前后声部运动解释。", "避免把所有不协和音都当作新的和弦根音。", ["nonchord tone", "passing", "suspension"]),
    ("voice_leading", "共同音保持", "和弦变化时优先保持共同音，并让其他声部走最短路径。", "避免所有声部同时大跳。", ["voice leading", "common tone", "和弦"]),
    ("voice_leading", "声部独立", "让外声部方向具有对比，内声部避免不必要的交叉。", "避免持续平行同向运动造成声部粘连。", ["voice leading", "contrary motion", "独立"]),
    ("cadence", "终止准备", "在终止前削减旋律歧义，并把重要音放在清晰的节拍位置。", "避免突然终止且没有属功能或旋律落点准备。", ["cadence", "closure", "终止"]),
    ("rhythm", "节奏层级", "用少量核心时值建立层级，装饰性细分只出现在需要推动的位置。", "避免所有拍点都同样活跃。", ["rhythm", "hierarchy", "节奏"]),
    ("rhythm", "切分控制", "切分应与和声或乐句方向一致，并在关键结构点恢复清晰拍感。", "避免持续切分导致终止点不可辨认。", ["syncopation", "groove", "节奏"]),
    ("texture", "密度分层", "主线最活跃，支撑层减少音域和节奏竞争。", "避免各层同时占据相同音区与相同节奏密度。", ["texture", "density", "层次"]),
    ("texture", "留白", "在乐句边界或新材料出现前主动减少声部和音符密度。", "避免持续填满全部拍点。", ["texture", "space", "留白"]),
    ("form", "对比与回归", "先建立可记忆材料，再用一个受控参数制造对比，最后保留身份回归。", "避免对比段改变所有参数。", ["form", "contrast", "return"]),
    ("form", "比例", "目标只有一至八小节时，用微型句法而非假装完整大型曲式。", "避免给短片段强加不可能完成的宏大结构。", ["form", "proportion", "短乐句"]),
    ("playability", "音域边界", "把极端音域当作强调资源，并为跳入跳出预留可演奏路径。", "避免连续停留在乐器极端音区。", ["playability", "range", "乐器"]),
    ("playability", "动作经济", "优先选择能由自然指法、换把或换气连接的局部运动。", "避免只在理论上成立、实际动作代价过高的线条。", ["playability", "idiom", "演奏"]),
    ("orchestration", "角色分离", "明确主线、和声支撑、低音、节奏与色彩角色，再决定加倍。", "避免所有乐器长期齐奏同一密度。", ["orchestration", "role", "配器"]),
    ("orchestration", "音色接力", "用音区重叠和共同音完成音色交接，避免旋律突然失去连续性。", "避免没有准备的远距离音色切换。", ["orchestration", "timbre", "handoff"]),
    ("dynamics", "力度弧线", "力度变化应服务乐句方向，并与音域、密度至少有一个因素协同。", "避免在每个音符上机械增加力度记号。", ["dynamics", "phrase", "力度"]),
    ("articulation", "发音一致性", "同一动机的发音保持可识别，变化用于标记句法或角色转换。", "避免随机分配演奏法。", ["articulation", "motif", "发音"]),
]


STYLE_GUIDES: dict[str, dict[str, str]] = {
    "classical": {"motif": "用短动机、对称问答和清晰终止建立比例。", "melody": "级进为主，跳进后补偿，装饰服从句法。", "harmony": "功能进行清楚，终止区属功能明确。", "voice_leading": "保持共同音，控制平行与声部交叉。", "rhythm": "拍层清晰，表面变化不掩盖句法重音。", "texture": "主次分明，可在旋律伴奏与简洁对位间切换。", "cadence": "用半终止制造开放，用正格倾向完成收束。", "dynamics": "力度弧线与四小节或八小节句法同步。", "form": "对比材料只改变一至两个参数后回归。", "tension": "通过属功能、顺阶上行和密度累积张力。", "ornament": "装饰音连接结构音，不改变骨架节奏。", "avoid": "避免无准备的色彩和弦和持续极端音域。"},
    "romantic": {"motif": "保留动机身份，同时扩大音域和延长线条。", "melody": "允许歌唱性大跳，但用反向级进恢复连贯。", "harmony": "使用经过和弦、延迟解决与局部色彩变化。", "voice_leading": "内声部半音连接应可听且不挤压主线。", "rhythm": "通过延宕、弱起和伴奏流动制造呼吸弹性。", "texture": "让旋律浮在分解和弦或宽广支撑之上。", "cadence": "终止可延迟，但最终落点需具有方向感。", "dynamics": "使用更长的渐强渐弱而非碎片化力度记号。", "form": "回归时允许加厚织体或提高音区。", "tension": "以顺阶高点、和声延迟和半音声部共同累积。", "ornament": "装饰应增强歌唱线条，不遮蔽主音。", "avoid": "避免每小节都过度转调或过度堆叠和弦音。"},
    "jazz": {"motif": "用节奏位移、回答句和有限音高改写发展动机。", "melody": "强调导向音、包围音与和弦延伸音的解决。", "harmony": "优先三七音导向，再选择可控的延伸和替代。", "voice_leading": "让三音与七音以半音或全音平滑连接。", "rhythm": "切分与预期音必须仍能指向稳定拍层。", "texture": "主线留出节奏空间，伴奏避免持续满奏。", "cadence": "用 ii–V 或可解释的替代准备目标和弦。", "dynamics": "用重音和发音塑造律动，少用逐音力度符号。", "form": "保持乐句长度与回合感，变化不能丢失落点。", "tension": "延伸音和变化音需朝目标声部解决。", "ornament": "经过与包围材料应围绕结构音组织。", "avoid": "避免把随机半音集合当作爵士和声。"},
    "pop": {"motif": "用短小、重复、易识别的轮廓形成钩子。", "melody": "控制音域并把关键词式高点留给句尾或副歌感位置。", "harmony": "循环要稳定，变化主要服务段落提升和落点。", "voice_leading": "低音根音运动与上方共同音共同维持连续性。", "rhythm": "建立稳定律动单元，只在句尾做填充。", "texture": "分层进入或退出比持续叠加更有效。", "cadence": "可用开放循环，但必须让旋律落点清楚。", "dynamics": "通过密度、音区和层数共同制造能量变化。", "form": "重复中只改变结尾、配器或密度之一。", "tension": "预副歌感可由上行低音、缩短节奏或提高音区产生。", "ornament": "少量滑音式邻接或经过音服务可唱性。", "avoid": "避免复杂度增长破坏钩子识别。"},
    "minimal": {"motif": "选择短单元，通过相位、重音或单音替换渐变。", "melody": "小音域与重复优先，变化必须可追踪。", "harmony": "保持稳定和声场，慢速移动一个声部。", "voice_leading": "一次改变一个音，保留最大共同音集合。", "rhythm": "使用可感知的循环与受控偏移。", "texture": "层次增减要渐进，并保留透明度。", "cadence": "收束可由稀疏化和音区回落完成。", "dynamics": "用长时程缓变，避免逐事件抖动。", "form": "形态来自累积、替换与消减。", "tension": "通过相位错位、密度或注册变化积累。", "ornament": "装饰应成为重复规则的一部分。", "avoid": "避免随机变化伪装成过程音乐。"},
    "modal": {"motif": "突出调式特征音，但不在每个事件上重复强调。", "melody": "围绕终止音和特征音建立方向。", "harmony": "使用持续音、开放五度和非功能色彩支撑调式。", "voice_leading": "避免强导音解决把材料拉回大小调功能。", "rhythm": "节奏可以不对称，但需有重复支点。", "texture": "持续音与独立旋律层要保持音区分离。", "cadence": "用终止音、共同音和下行回落代替强属功能。", "dynamics": "让力度跟随旋律弧线和持续音层变化。", "form": "以特征音材料的出现、离开和回归划分段落。", "tension": "利用音区、持续音摩擦和特征音延迟。", "ornament": "装饰围绕调式骨架音展开。", "avoid": "避免不自觉引入强 V–I 抹去调式身份。"},
    "cinematic": {"motif": "使用轮廓清晰、可跨音色传递的核心动机。", "melody": "控制高点出现次数，让音区扩展对应叙事升级。", "harmony": "以共同音、低音移动和调式混合塑造色彩方向。", "voice_leading": "层叠和弦仍需控制内声部摩擦和解决。", "rhythm": "固定脉冲、长音层与主线节奏应各司其职。", "texture": "按频段和角色分层，逐步增加而非瞬间全奏。", "cadence": "根据叙事选择明确落地或悬而未决的终止。", "dynamics": "动态应主要由层次、音区和配器共同驱动。", "form": "用建立、扩展、峰值、余韵形成微型叙事。", "tension": "通过低音持续、上层扩张和节奏压缩累积。", "ornament": "色彩性内声部应低于主线显著度。", "avoid": "避免只靠音量和低音轰鸣制造虚假高潮。"},
}


INSTRUMENT_CHARACTER = {
    "general": ("中性符号声部", "以实际宿主乐器和声部约束为准"),
    "piano": ("钢琴", "利用双手分工、踏板共鸣与可达手型"),
    "violin": ("小提琴", "利用歌唱高音区、弓向与换把连续性"),
    "cello": ("大提琴", "利用温暖中低音区和可控换把"),
    "flute": ("长笛", "利用透明高音区并为气息留出空隙"),
    "clarinet": ("单簧管", "利用跨音区色彩差异并谨慎处理换区"),
    "trumpet": ("小号", "利用清晰起音并控制高音区耐力"),
    "guitar": ("吉他", "利用空弦、把位与可持续指型"),
    "voice": ("人声", "以可唱音域、元音延展与换气为核心"),
}

INSTRUMENT_ASPECTS = {
    "range": ("音域", "把极端音区留给少数结构性高点", "避免长时间停留在边缘音区"),
    "leap": ("跳进", "为大跳安排准备音和反向恢复", "避免连续同向大跳"),
    "density": ("密度", "让快速材料与持续材料交替出现", "避免全程维持最高密度"),
    "articulation": ("发音", "让发音分组对应动机与乐句", "避免逐音随机改变发音"),
    "breath_motion": ("呼吸或动作", "在句法边界预留换气、换把或手型调整", "避免无休止的身体动作负担"),
    "register": ("音区角色", "让主线、支撑和色彩使用可分辨的音区", "避免角色长期重叠在同一频段"),
    "repetition": ("重复", "重复材料时改变一次力度、音区或结尾", "避免机械复制而没有方向"),
    "balance": ("平衡", "根据该乐器的穿透力调整加倍和伴奏密度", "避免用音符数量代替平衡判断"),
    "transition": ("连接", "在换区、换把或角色交接前使用共同音或级进", "避免突兀切换造成线条断裂"),
    "safety": ("可演奏边界", "在生成后检查音域、跨度、速度与持续时间的组合", "避免只检查单个音是否存在"),
}


FORM_RULES = [
    ("FORM-QUESTION-ANSWER", "问答句", "前句保持开放，后句复用动机并加强落点。", ["phrase", "question", "answer"]),
    ("FORM-SENTENCE", "乐句句型", "用呈示、重复或变形、延伸与终止组织短句。", ["sentence", "phrase", "development"]),
    ("FORM-PERIOD", "周期句", "前后句共享开头身份，但后句给出更明确的终止。", ["period", "cadence", "phrase"]),
    ("FORM-ARC", "拱形", "音域、密度或张力逐步上升后对称或近似回落。", ["arc", "climax", "form"]),
    ("FORM-THROUGH", "贯穿发展", "保持一个身份参数不变，让其余参数逐步变化。", ["development", "through composed", "form"]),
    ("ORCH-DOUBLING", "加倍", "只在需要强化轮廓或音色融合时加倍，避免长期同度堆叠。", ["doubling", "orchestration", "配器"]),
    ("ORCH-SPACING", "和弦间距", "低音区使用更宽间距，中高音区可逐步收紧。", ["spacing", "voicing", "orchestration"]),
    ("ORCH-REGISTER", "频段占位", "先为低音、主体和亮度层分配频段，再添加填充。", ["register", "spectrum", "orchestration"]),
    ("ORCH-HANDOFF", "旋律交接", "交接前后共享一个音或一小段重叠，维持听觉连续性。", ["handoff", "melody", "orchestration"]),
    ("ORCH-TUTTI", "全奏保留", "把全奏留给少数峰值，前后用减层建立对比。", ["tutti", "climax", "orchestration"]),
    ("GOAL-LYRIC", "抒情目标", "使用较长线条、可预测呼吸和有限高点。", ["lyrical", "抒情", "goal"]),
    ("GOAL-ENERGY", "能量目标", "先提高脉冲清晰度，再增加密度与音区。", ["energy", "driving", "goal"]),
    ("GOAL-DARK", "暗色目标", "优先使用较低音区、窄色彩移动和受控不协和。", ["dark", "暗", "goal"]),
    ("GOAL-BRIGHT", "明亮目标", "使用开放音程、清晰高音区和稳定节拍层。", ["bright", "明亮", "goal"]),
    ("GOAL-SUSPENSE", "悬念目标", "延迟落点并保持一个未解决声部，但仍要控制方向。", ["suspense", "悬念", "tension"]),
    ("GOAL-CLOSURE", "收束目标", "减少新材料，让旋律、低音与和声共同指向落点。", ["closure", "cadence", "终止"]),
    ("METER-DUPLE", "二拍层", "在二拍或四拍框架中区分强拍、次强拍与弱拍装饰。", ["2/4", "4/4", "meter"]),
    ("METER-TRIPLE", "三拍层", "强调一拍支点，避免每拍都使用同等和声重量。", ["3/4", "meter", "triple"]),
    ("METER-COMPOUND", "复拍子", "让细分保持三连组感，跨组切分需回到大拍支点。", ["6/8", "9/8", "12/8", "meter"]),
    ("METER-ODD", "不对称拍", "用稳定分组解释不对称拍，而不是随机重音。", ["5/8", "7/8", "odd meter"]),
]


def _card(rule_id: str, domain: str, title: str, action: str, avoid: str, *, styles: list[str], modes: list[str], instruments: list[str], tags: list[str], priority: float = 0.7) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "domain": domain,
        "title_zh": title,
        "action_zh": action,
        "avoid_zh": avoid,
        "styles": styles,
        "modes": modes,
        "instruments": instruments,
        "goals": tags,
        "meters": ["any"],
        "tags": tags,
        "priority": priority,
        "hard_constraint": domain in {"playability", "voice_leading"},
        "provenance": PROVENANCE,
    }


def build_cards() -> dict[str, list[dict[str, Any]]]:
    """Return deterministic, semantically grouped rule packs."""

    core: list[dict[str, Any]] = []
    for index, (domain, title, action, avoid, tags) in enumerate(CORE_PRINCIPLES, start=1):
        for variant, mode in enumerate(MODES, start=1):
            mode_hint = {"theory_variation": "旋律变奏", "reharmonize": "和声重构", "orchestration_advice": "配器规划"}[mode]
            core.append(_card(f"KB-CORE-{index:03d}-{variant}", domain, f"{title}·{mode_hint}", action, avoid, styles=["any"], modes=[mode], instruments=["general"], tags=[*tags, mode], priority=0.76))

    styles: list[dict[str, Any]] = []
    for style_id, guide in STYLE_GUIDES.items():
        for index, (domain, action) in enumerate(guide.items(), start=1):
            styles.append(_card(f"KB-STYLE-{style_id.upper()}-{index:02d}", domain if domain != "avoid" else "style", f"{style_id}·{domain}", action, guide["avoid"], styles=[style_id], modes=MODES, instruments=["general"], tags=[style_id, domain, "style grammar"], priority=0.82))

    instruments: list[dict[str, Any]] = []
    for instrument, (display, character) in INSTRUMENT_CHARACTER.items():
        for index, (aspect, (title, action, avoid)) in enumerate(INSTRUMENT_ASPECTS.items(), start=1):
            instruments.append(_card(f"KB-INST-{instrument.upper()}-{index:02d}", "playability" if aspect in {"range", "leap", "breath_motion", "safety"} else "orchestration", f"{display}·{title}", f"{character}；{action}。", f"{avoid}；并以宿主乐谱的实际编制为准。", styles=["any"], modes=MODES, instruments=[instrument], tags=[instrument, display, aspect, title], priority=0.86 if aspect == "safety" else 0.74))

    form: list[dict[str, Any]] = []
    for index, (rule_id, title, action, tags) in enumerate(FORM_RULES, start=1):
        domain = "orchestration" if rule_id.startswith("ORCH") else "form"
        if rule_id.startswith("METER"):
            domain = "rhythm"
        form.append(_card(rule_id, domain, title, action, "避免同时改变过多结构参数，且不得绕过目标范围与保护范围。", styles=["any"], modes=MODES, instruments=["general"], tags=tags, priority=0.78 + (index % 3) * 0.03))
    return {"core_theory": core, "style_grammar": styles, "instrument_playability": instruments, "form_orchestration": form}


def write_packs(output_root: Path = PACK_ROOT) -> dict[str, int]:
    """Materialize JSONL packs and return their card counts."""

    output_root.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for pack_name, cards in build_cards().items():
        target = output_root / f"{pack_name}.jsonl"
        content = "\n".join(json.dumps(card, ensure_ascii=False, sort_keys=True) for card in cards) + "\n"
        target.write_text(content, encoding="utf-8")
        counts[pack_name] = len(cards)
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Composer V0.3 atomic knowledge JSONL packs.")
    parser.add_argument("--output", type=Path, default=PACK_ROOT, help="Output directory for JSONL packs.")
    args = parser.parse_args()
    counts = write_packs(args.output)
    print(json.dumps({"status": "built", "packs": counts, "total_cards": sum(counts.values())}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
