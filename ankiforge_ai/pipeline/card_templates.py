"""Pure-Python card template definitions used by generation and quality checks."""

from dataclasses import dataclass


@dataclass(frozen=True, repr=False)
class CardTemplate:
    template_id: str
    mode_id: str
    display_name_zh: str
    display_name_en: str
    description_zh: str
    description_en: str
    best_for: str
    front_guidance: str
    back_guidance: str
    ideal_front_shape: str
    ideal_back_shape: str
    common_bad_patterns: tuple[str, ...]
    quality_priorities: tuple[str, ...]
    supports_cloze: bool = False
    compatible_note_type_hints: tuple[str, ...] = ("Basic",)
    selectable: bool = True

    def __post_init__(self) -> None:
        text_values = (
            self.template_id,
            self.mode_id,
            self.display_name_zh,
            self.display_name_en,
            self.description_zh,
            self.description_en,
            self.best_for,
            self.front_guidance,
            self.back_guidance,
            self.ideal_front_shape,
            self.ideal_back_shape,
        )
        if not all(isinstance(value, str) and value.strip() for value in text_values):
            raise ValueError("card template text fields must be non-empty strings.")
        for values, name in (
            (self.common_bad_patterns, "common_bad_patterns"),
            (self.quality_priorities, "quality_priorities"),
            (self.compatible_note_type_hints, "compatible_note_type_hints"),
        ):
            if not values or not all(
                isinstance(value, str) and value.strip() for value in values
            ):
                raise ValueError(f"{name} must contain non-empty strings.")

    def __repr__(self) -> str:
        return (
            "CardTemplate("
            f"template_id={self.template_id!r}, mode_id={self.mode_id!r}, "
            f"supports_cloze={self.supports_cloze}, selectable={self.selectable})"
        )


_TEMPLATES = (
    CardTemplate(
        "basic_qa",
        "concept",
        "基础问答",
        "Basic Q&A",
        "通用的一问一答卡片",
        "A general-purpose question-and-answer card",
        "Straightforward facts and explanations",
        "Ask one specific question that stands on its own.",
        "Answer directly with only the information needed for recall.",
        "One concrete question",
        "One direct answer",
        ("generic question", "multiple questions", "answer copied as a paragraph"),
        ("atomic", "specific", "concise"),
    ),
    CardTemplate(
        "concept",
        "concept",
        "概念理解",
        "Concept",
        "理解概念、原因、区别与意义",
        "Understand a concept, its causes, distinctions, and significance",
        "Conceptual understanding and causal relationships",
        "Ask what the concept means, why it matters, or how it differs.",
        "Give a concise explanation grounded in the supplied material.",
        "A specific what, why, or difference question",
        "A compact explanatory answer",
        ("term-only front", "vague explain prompt", "several concepts at once"),
        ("atomic", "specific", "explanatory"),
    ),
    CardTemplate(
        "definition",
        "definition",
        "术语定义",
        "Definition",
        "记忆术语、定义和关键特征",
        "Learn a term, its definition, and defining traits",
        "Terminology and precise definitions",
        "Name the term explicitly and ask for its definition or key trait.",
        "State the precise definition and only an essential example if useful.",
        "What is <term>?",
        "Definition plus key distinguishing trait",
        ("unnamed term", "circular definition", "long unrelated example"),
        ("precise", "definitional", "concise"),
    ),
    CardTemplate(
        "exam_answer",
        "exam",
        "考试作答",
        "Exam answer",
        "用明确考点和简洁得分点复习",
        "Review with a clear exam point and concise scoring points",
        "Exam prompts and model-answer points",
        "Ask one explicit, answerable exam-style question.",
        "Give the minimum complete scoring points without essay filler.",
        "One focused exam question",
        "Short model answer with clear scoring points",
        ("vague discuss prompt", "essay response", "unstated scoring point"),
        ("testable", "scoring-points", "direct"),
    ),
    CardTemplate(
        "quick_review",
        "quick_review",
        "快速回顾",
        "Quick review",
        "短问短答，一卡一事实",
        "Short question, short answer, one fact per card",
        "Fast recall of one fact",
        "Use a very short, unambiguous recall cue.",
        "Answer with one fact and no extra explanation.",
        "Short factual question",
        "One short fact",
        ("long context", "multi-sentence explanation", "more than one fact"),
        ("one-fact", "brief", "fast-recall"),
    ),
    CardTemplate(
        "compare_contrast",
        "compare_contrast",
        "对比辨析",
        "Compare & contrast",
        "区分两个容易混淆的概念",
        "Distinguish two concepts that are easy to confuse",
        "Differences, similarities, and decision boundaries",
        "Name both sides and ask for one meaningful distinction.",
        "Contrast both sides on the same dimension.",
        "How do A and B differ in <dimension>?",
        "A versus B on that dimension",
        ("only one side named", "unmatched comparison dimensions", "long table"),
        ("two-sided", "same-dimension", "distinctive"),
    ),
    CardTemplate(
        "process_steps",
        "process_steps",
        "流程步骤",
        "Process steps",
        "记忆步骤、流程和先后顺序",
        "Learn steps, processes, and ordering",
        "Ordered procedures and causal sequences",
        "Ask for a bounded process or the next step in a sequence.",
        "Use explicit order and keep each step concise.",
        "What are the ordered steps of <process>?",
        "A short ordered sequence",
        ("unordered list", "several unrelated processes", "missing transition"),
        ("ordered", "complete", "concise"),
    ),
    CardTemplate(
        "formula_rule",
        "formula_rule",
        "公式规则",
        "Formula or rule",
        "记忆公式、规则、变量与适用条件",
        "Learn a formula or rule, its variables, and conditions",
        "Formulas, rules, variables, and applicability",
        "Ask for the formula or rule together with its applicable condition.",
        "State the formula, define key variables, and name the condition.",
        "Under what condition does <formula/rule> apply?",
        "Formula or rule plus variables and condition",
        ("formula without condition", "undefined variable", "derivation essay"),
        ("correct-form", "variables", "condition"),
    ),
    CardTemplate(
        "mistake_trap",
        "mistake_trap",
        "易错陷阱",
        "Mistake trap",
        "识别常见误区和易混点",
        "Recognize common mistakes and confusions",
        "Misconceptions and corrective distinctions",
        "Ask which common belief is wrong or what is easily confused.",
        "State the misconception and the concise correction.",
        "What is the common mistake about <topic>?",
        "Mistake followed by correction",
        ("invented misconception", "no correction", "opinion presented as fact"),
        ("misconception", "correction", "grounded"),
    ),
    CardTemplate(
        "cloze_candidate",
        "cloze_candidate",
        "填空候选",
        "Cloze candidate",
        "仅用于安全兼容性评估的填空候选",
        "A cloze candidate reserved for safe compatibility checks",
        "Simple, non-nested cloze candidates",
        "Use one simple cloze deletion only when the note type is compatible.",
        "Keep enough context around one unambiguous deletion.",
        "A sentence with one {{c1::deletion}}",
        "Context that makes the deletion uniquely answerable",
        ("nested cloze", "multiple unrelated deletions", "unsupported note type"),
        ("valid-syntax", "single-deletion", "note-type-compatible"),
        supports_cloze=True,
        compatible_note_type_hints=("Cloze",),
        selectable=False,
    ),
)

_BY_TEMPLATE_ID = {item.template_id: item for item in _TEMPLATES}
_DEFAULT_BY_MODE = {
    "concept": "concept",
    "definition": "definition",
    "exam": "exam_answer",
    "quick_review": "quick_review",
    "compare_contrast": "compare_contrast",
    "process_steps": "process_steps",
    "formula_rule": "formula_rule",
    "mistake_trap": "mistake_trap",
    "cloze_candidate": "cloze_candidate",
}


def all_card_templates() -> tuple[CardTemplate, ...]:
    return _TEMPLATES


def selectable_card_templates() -> tuple[CardTemplate, ...]:
    return tuple(item for item in _TEMPLATES if item.selectable)


def get_card_template(template_id: str) -> CardTemplate:
    try:
        return _BY_TEMPLATE_ID[template_id]
    except (KeyError, TypeError):
        raise ValueError(f"unsupported card template: {template_id!r}") from None


def default_template_for_mode(mode_id: str) -> CardTemplate:
    try:
        return get_card_template(_DEFAULT_BY_MODE[mode_id])
    except (KeyError, TypeError):
        raise ValueError(f"unsupported card mode: {mode_id!r}") from None
