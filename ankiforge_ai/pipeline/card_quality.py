"""Deterministic, explainable quality checks for candidate cards."""

from dataclasses import dataclass, field
import re
from typing import Iterable, Mapping, Optional

from .generation_settings import GenerationSettings, coerce_generation_settings


_GENERIC_FRONT_PATTERNS = (
    re.compile(r"(?:请|试着)?解释(?:以下|这个|上述)?内容", re.IGNORECASE),
    re.compile(r"根据(?:这份|上述|以下)?材料(?:可知|回答)?", re.IGNORECASE),
    re.compile(r"\b(?:explain|describe) (?:this|the following|the material)\b", re.IGNORECASE),
    re.compile(r"\bwhat (?:is|does) (?:this|the material)\b", re.IGNORECASE),
)
_BOILERPLATE_PATTERNS = (
    re.compile(r"根据(?:这份|上述|以下)?材料(?:可知|回答)?", re.IGNORECASE),
    re.compile(r"\baccording to (?:the|this) material\b", re.IGNORECASE),
    re.compile(r"\bthe material (?:says|states|shows)\b", re.IGNORECASE),
)
_MARKDOWN_RESIDUE = re.compile(
    r"```|(?:^|\n)\s{0,3}#{1,6}\s|!??\[[^\]]*\]\([^)]*\)|\*\*[^*]+\*\*|__[^_]+__"
)
_BULLET_LINE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")
_PROMPT_ARTIFACT = re.compile(
    r"(?:return\s+(?:only\s+)?json|quality\s+rules?|card\s+mode\s*:|"
    r"template\s+instructions?|system\s+prompt|as\s+an?\s+ai|"
    r"输出\s*json|提示词|模板说明)",
    re.IGNORECASE,
)
_UNNECESSARY_INTRO = re.compile(
    r"^(?:答案是|正确答案是|回答是|根据材料(?:可知)?|"
    r"the answer is|this answer is|according to the material)\s*[:：,，]?",
    re.IGNORECASE,
)
_VALID_CLOZE = re.compile(r"\{\{c[1-9]\d*::[^{}\n]+?(?:::[^{}\n]+?)?\}\}")
_QUESTION_START = re.compile(
    r"^(?:what|why|how|when|where|which|who|name|state|compare|under what)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, repr=False)
class QualityRuleDefinition:
    rule_id: str
    severity: str
    user_message_zh: str
    user_message_en: str
    suggestion_zh: str
    suggestion_en: str
    blocking: bool
    score_delta: float

    def __post_init__(self) -> None:
        if self.severity not in {"info", "warning", "blocking"}:
            raise ValueError("severity must be info, warning, or blocking.")
        if self.blocking != (self.severity == "blocking"):
            raise ValueError("blocking must match blocking severity.")
        if not -1.0 <= self.score_delta <= 0.0:
            raise ValueError("score_delta must be between -1.0 and 0.0.")
        texts = (
            self.rule_id,
            self.user_message_zh,
            self.user_message_en,
            self.suggestion_zh,
            self.suggestion_en,
        )
        if not all(isinstance(value, str) and value.strip() for value in texts):
            raise ValueError("quality rule text fields must be non-empty strings.")

    def __repr__(self) -> str:
        return (
            "QualityRuleDefinition("
            f"rule_id={self.rule_id!r}, severity={self.severity!r}, "
            f"score_delta={self.score_delta:.2f})"
        )


def _definition(
    rule_id: str,
    zh: str,
    en: str,
    suggestion_zh: str,
    suggestion_en: str,
    *,
    severity: str = "warning",
    score_delta: float = -0.12,
) -> QualityRuleDefinition:
    return QualityRuleDefinition(
        rule_id=rule_id,
        severity=severity,
        user_message_zh=zh,
        user_message_en=en,
        suggestion_zh=suggestion_zh,
        suggestion_en=suggestion_en,
        blocking=severity == "blocking",
        score_delta=score_delta,
    )


_RULES = (
    _definition("empty_front", "正面为空，不能写入", "Front is empty and cannot be written", "补充一个具体问题，或丢弃这张卡。", "Add a specific question or discard this card.", severity="blocking", score_delta=-0.55),
    _definition("empty_back", "背面为空，不能写入", "Back is empty and cannot be written", "补充一个直接答案，或丢弃这张卡。", "Add a direct answer or discard this card.", severity="blocking", score_delta=-0.55),
    _definition("short_front", "问题可能过短", "Question may be too short", "补充必要上下文。", "Add enough context for independent review."),
    _definition("generic_front", "问题可能太泛", "Question may be too broad", "把问题改得更具体。", "Make the question more specific."),
    _definition("long_back", "答案偏长", "Answer may be too long", "缩短为直接答案。", "Shorten it to the direct answer."),
    _definition("multiple_questions", "可能包含多个问题", "May contain multiple questions", "拆成一卡一问。", "Split it into one question per card."),
    _definition("multi_point_card", "可能包含多个知识点", "May contain multiple points", "只保留一个知识点。", "Keep one independently reviewable point."),
    _definition("boilerplate_phrase", "包含无助于复习的套话", "Contains review-unhelpful filler", "删除套话。", "Remove filler phrases."),
    _definition("markdown_residue", "可能残留 Markdown 标记", "Markdown markup may remain", "清理格式残留。", "Remove formatting residue."),
    _definition("duplicate_candidate", "与本批另一张卡内容相近", "Similar to another card in this batch", "比较后保留更清楚的一张。", "Compare both cards and keep the clearer one."),
    _definition("too_many_bullets", "答案分点过多", "Answer may have too many bullets", "拆分或只保留必要步骤。", "Split it or keep only essential points.", score_delta=-0.10),
    _definition("answer_too_verbose_for_mode", "答案不符合当前模式的简洁度", "Answer may be too verbose for this mode", "按当前模式缩短答案。", "Shorten the answer for the selected mode."),
    _definition("front_not_question_like", "正面可能不像可复习的问题", "Front may not be a reviewable question", "改成明确问题或回忆提示。", "Turn it into a clear question or recall cue.", score_delta=-0.08),
    _definition("unsupported_cloze", "当前笔记类型不支持 Cloze", "The current note type does not support Cloze", "改用 Basic 卡，或选择兼容的 Cloze 笔记类型。", "Use a Basic card or a compatible Cloze note type.", severity="blocking", score_delta=-0.55),
    _definition("cloze_syntax_invalid", "Cloze 语法无效", "Cloze syntax is invalid", "只使用一个完整且不嵌套的 Cloze。", "Use one complete, non-nested Cloze deletion.", severity="blocking", score_delta=-0.55),
    _definition("source_not_grounded_simple", "答案可能缺少材料依据", "Answer may not be grounded in the source", "核对答案是否来自当前材料。", "Check that the answer is supported by the source.", score_delta=-0.08),
    _definition("too_many_cards_from_short_source", "短材料可能生成了过多卡片", "A short source may have produced too many cards", "减少卡片数量并保留核心知识点。", "Generate fewer cards and keep the core points.", score_delta=-0.08),
    _definition("answer_contains_prompt_artifact", "答案可能包含提示词残留", "Answer may contain prompt artifacts", "删除 JSON、提示词或模板说明。", "Remove JSON, prompt, or template instructions."),
    _definition("front_contains_answer_leak", "问题中可能泄露答案", "The front may reveal the answer", "移除正面中的答案线索。", "Remove the answer from the front."),
    _definition("back_contains_unnecessary_intro", "答案包含不必要的开场语", "Answer contains an unnecessary introduction", "直接写答案。", "Start with the answer directly.", score_delta=-0.08),
    _definition("compare_card_missing_two_sides", "对比卡可能缺少一方", "Compare card may be missing one side", "在问题中明确两个比较对象。", "Name both sides in the question."),
    _definition("process_card_missing_order", "流程卡可能缺少顺序", "Process card may be missing an order", "使用明确的先后顺序。", "Use an explicit sequence."),
    _definition("formula_card_missing_condition", "公式卡可能缺少适用条件", "Formula card may be missing its condition", "补充公式或规则的适用条件。", "Add the formula or rule's applicable condition."),
    _definition("definition_card_missing_term", "定义卡可能没有明确术语", "Definition card may not name its term", "在正面明确要定义的术语。", "Name the term explicitly on the front."),
    _definition("exam_card_too_vague", "考题可能太空泛", "Exam question may be too vague", "改成有明确得分点的问题。", "Ask a question with clear scoring points."),
    _definition("quick_review_too_long", "快速回顾卡可能太长", "Quick-review card may be too long", "缩短为一卡一事实。", "Shorten it to one fact per card."),
)
_RULE_BY_ID = {item.rule_id: item for item in _RULES}


def all_quality_rule_definitions() -> tuple[QualityRuleDefinition, ...]:
    return _RULES


@dataclass(frozen=True, repr=False)
class CardQualityIssue:
    warning_id: str
    severity: str
    suggestion_id: str
    blocking: bool = False
    score_delta: float = -0.12
    user_message_zh: str = ""
    user_message_en: str = ""
    suggestion_zh: str = ""
    suggestion_en: str = ""

    def __post_init__(self) -> None:
        if self.severity not in {"info", "warning", "blocking"}:
            raise ValueError("severity must be info, warning, or blocking.")
        if not self.warning_id or not self.suggestion_id:
            raise ValueError("quality issue identifiers must be non-empty.")
        if self.blocking != (self.severity == "blocking"):
            raise ValueError("blocking must match blocking severity.")

    @property
    def rule_id(self) -> str:
        return self.warning_id

    def user_message(self, language: str) -> str:
        if language == "zh":
            return self.user_message_zh
        if language == "en":
            return self.user_message_en
        raise ValueError("language must be zh or en.")

    def suggestion(self, language: str) -> str:
        if language == "zh":
            return self.suggestion_zh
        if language == "en":
            return self.suggestion_en
        raise ValueError("language must be zh or en.")

    def __repr__(self) -> str:
        return (
            "CardQualityIssue("
            f"rule_id={self.rule_id!r}, severity={self.severity!r}, "
            f"score_delta={self.score_delta:.2f})"
        )


@dataclass(frozen=True, repr=False)
class CardQualityResult:
    quality_score: float
    issues: tuple[CardQualityIssue, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not 0.0 <= self.quality_score <= 1.0:
            raise ValueError("quality_score must be between 0.0 and 1.0.")
        if not all(isinstance(item, CardQualityIssue) for item in self.issues):
            raise ValueError("issues must contain CardQualityIssue values.")

    @property
    def warning_ids(self) -> tuple[str, ...]:
        return tuple(item.warning_id for item in self.issues)

    @property
    def blocking_count(self) -> int:
        return sum(item.blocking for item in self.issues)

    @property
    def warning_count(self) -> int:
        return sum(item.severity == "warning" for item in self.issues)

    @property
    def is_blocking(self) -> bool:
        return bool(self.blocking_count)

    @property
    def severity(self) -> str:
        if self.is_blocking:
            return "blocking"
        if self.warning_count:
            return "warning"
        return "info"

    def __repr__(self) -> str:
        return (
            "CardQualityResult("
            f"quality_score={self.quality_score:.2f}, severity={self.severity!r}, "
            f"issue_count={len(self.issues)})"
        )

    def to_safe_dict(self) -> dict:
        return {
            "quality_score": self.quality_score,
            "severity": self.severity,
            "issue_count": len(self.issues),
            "blocking_count": self.blocking_count,
            "warning_count": self.warning_count,
            "warning_ids": self.warning_ids,
        }


@dataclass(frozen=True, repr=False)
class CandidateQualityResult:
    candidate_id: str
    quality: CardQualityResult

    def __repr__(self) -> str:
        return (
            "CandidateQualityResult("
            f"candidate_id={self.candidate_id!r}, quality={self.quality!r})"
        )


@dataclass(frozen=True, repr=False)
class CardQualityBatch:
    results: tuple[CandidateQualityResult, ...]

    def for_candidate(self, candidate_id: str) -> CardQualityResult:
        for item in self.results:
            if item.candidate_id == candidate_id:
                return item.quality
        raise KeyError(candidate_id)

    @property
    def warning_count(self) -> int:
        return sum(item.quality.warning_count for item in self.results)

    @property
    def blocking_count(self) -> int:
        return sum(item.quality.blocking_count for item in self.results)

    def __repr__(self) -> str:
        return (
            "CardQualityBatch("
            f"candidate_count={len(self.results)}, warning_count={self.warning_count}, "
            f"blocking_count={self.blocking_count})"
        )


def evaluate_card_quality(
    front: object,
    back: object,
    settings: Optional[GenerationSettings] = None,
    *,
    source_text: object = None,
    cloze_supported: bool = False,
) -> CardQualityResult:
    resolved = coerce_generation_settings(settings)
    front_text = _text(front)
    back_text = _text(back)
    source = _text(source_text)
    issues: list[CardQualityIssue] = []

    if not front_text:
        issues.append(_issue("empty_front"))
    if not back_text:
        issues.append(_issue("empty_back"))

    front_core = re.sub(r"[\s?？!！。，,.、:：;；]", "", front_text)
    if front_text and len(front_core) < 4:
        issues.append(_issue("short_front"))
    if front_text and any(pattern.search(front_text) for pattern in _GENERIC_FRONT_PATTERNS):
        issues.append(_issue("generic_front"))

    max_back_chars = 240 if resolved.answer_length == "short" else 500
    if resolved.card_mode == "quick_review":
        max_back_chars = min(max_back_chars, 140)
    if len(back_text) > max_back_chars:
        issues.append(_issue("long_back"))

    if front_text.count("?") + front_text.count("？") > 1:
        issues.append(_issue("multiple_questions"))

    bullet_count = sum(bool(_BULLET_LINE.match(line)) for line in back_text.splitlines())
    multi_front = bool(
        re.search(r"(?:以及|并说明|分别|同时|\band\b.+\band\b)", front_text, re.IGNORECASE)
    )
    if bullet_count >= 3 or multi_front:
        issues.append(_issue("multi_point_card"))
    if bullet_count >= 4:
        issues.append(_issue("too_many_bullets"))

    combined = f"{front_text}\n{back_text}"
    if any(pattern.search(combined) for pattern in _BOILERPLATE_PATTERNS):
        issues.append(_issue("boilerplate_phrase"))
    if _MARKDOWN_RESIDUE.search(combined):
        issues.append(_issue("markdown_residue"))
    if _answer_too_verbose_for_mode(back_text, resolved.card_mode):
        issues.append(_issue("answer_too_verbose_for_mode"))
    if (
        front_text
        and resolved.card_mode not in {"definition", "cloze_candidate"}
        and not _looks_question_like(front_text)
    ):
        issues.append(_issue("front_not_question_like"))

    cloze_present = "{{c" in combined.casefold()
    if (cloze_present or resolved.card_mode == "cloze_candidate") and not cloze_supported:
        issues.append(_issue("unsupported_cloze"))
    if cloze_supported and resolved.card_mode == "cloze_candidate" and not _valid_cloze_text(front_text):
        issues.append(_issue("cloze_syntax_invalid"))

    if source and front_text and back_text and not _is_simply_grounded(back_text, source):
        issues.append(_issue("source_not_grounded_simple"))
    if _PROMPT_ARTIFACT.search(back_text):
        issues.append(_issue("answer_contains_prompt_artifact"))
    if _front_leaks_answer(front_text, back_text):
        issues.append(_issue("front_contains_answer_leak"))
    if _UNNECESSARY_INTRO.search(back_text):
        issues.append(_issue("back_contains_unnecessary_intro"))

    if resolved.card_mode == "compare_contrast" and not _names_comparison_sides(front_text):
        issues.append(_issue("compare_card_missing_two_sides"))
    if resolved.card_mode == "process_steps" and not _contains_explicit_order(back_text):
        issues.append(_issue("process_card_missing_order"))
    if resolved.card_mode == "formula_rule" and not _contains_condition(combined):
        issues.append(_issue("formula_card_missing_condition"))
    if resolved.card_mode == "definition" and _definition_term_missing(front_text):
        issues.append(_issue("definition_card_missing_term"))
    if resolved.card_mode == "exam" and _exam_front_is_vague(front_text):
        issues.append(_issue("exam_card_too_vague"))
    if resolved.card_mode == "quick_review" and (
        len(front_text) > 80 or len(back_text) > 80
    ):
        issues.append(_issue("quick_review_too_long"))

    return _build_result(tuple(_dedupe_issues(issues)))


def evaluate_card_batch(
    cards: Iterable[object],
    settings: Optional[GenerationSettings] = None,
    *,
    source_text: object = None,
    cloze_supported: bool = False,
) -> CardQualityBatch:
    resolved = coerce_generation_settings(settings)
    card_items = tuple(cards)
    source = _text(source_text)
    results: list[CandidateQualityResult] = []
    seen: set[tuple[str, str]] = set()
    for index, card in enumerate(card_items, start=1):
        candidate_id = _card_value(card, "id") or _card_value(card, "candidate_id")
        if not isinstance(candidate_id, str) or not candidate_id:
            candidate_id = f"candidate-{index}"
        front = _card_value(card, "front")
        if front is None:
            front = _card_value(card, "front_preview")
        back = _card_value(card, "back")
        if back is None:
            back = _card_value(card, "back_preview")
        card_source = source or _text(_card_value(card, "source_excerpt"))
        quality = evaluate_card_quality(
            front,
            back,
            resolved,
            source_text=card_source,
            cloze_supported=cloze_supported,
        )
        duplicate_key = (_normalize_duplicate(front), _normalize_duplicate(back))
        if duplicate_key != ("", "") and duplicate_key in seen:
            quality = _with_issue(quality, _issue("duplicate_candidate"))
        else:
            seen.add(duplicate_key)
        results.append(CandidateQualityResult(candidate_id, quality))

    if source and len(source) <= 120 and len(card_items) > max(
        3, _card_limit_for_density(resolved)
    ):
        density_issue = _issue("too_many_cards_from_short_source")
        results = [
            CandidateQualityResult(item.candidate_id, _with_issue(item.quality, density_issue))
            for item in results
        ]
    return CardQualityBatch(tuple(results))


def _issue(rule_id: str) -> CardQualityIssue:
    try:
        rule = _RULE_BY_ID[rule_id]
    except KeyError:
        raise ValueError(f"unknown quality rule: {rule_id!r}") from None
    return CardQualityIssue(
        warning_id=rule.rule_id,
        severity=rule.severity,
        suggestion_id=f"{rule.rule_id}_suggestion",
        blocking=rule.blocking,
        score_delta=rule.score_delta,
        user_message_zh=rule.user_message_zh,
        user_message_en=rule.user_message_en,
        suggestion_zh=rule.suggestion_zh,
        suggestion_en=rule.suggestion_en,
    )


def _build_result(issues: tuple[CardQualityIssue, ...]) -> CardQualityResult:
    score = 1.0 + sum(item.score_delta for item in issues)
    return CardQualityResult(round(max(0.0, min(1.0, score)), 2), issues)


def _with_issue(result: CardQualityResult, issue: CardQualityIssue) -> CardQualityResult:
    if issue.warning_id in result.warning_ids:
        return result
    return _build_result((*result.issues, issue))


def _dedupe_issues(issues: Iterable[CardQualityIssue]) -> list[CardQualityIssue]:
    seen = set()
    return [
        item
        for item in issues
        if not (item.warning_id in seen or seen.add(item.warning_id))
    ]


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _card_value(card: object, name: str):
    if isinstance(card, Mapping):
        return card.get(name)
    return getattr(card, name, None)


def _normalize_duplicate(value: object) -> str:
    return " ".join(_text(value).casefold().split())


def _answer_too_verbose_for_mode(back: str, mode_id: str) -> bool:
    limits = {
        "quick_review": 90,
        "definition": 220,
        "exam": 280,
        "compare_contrast": 320,
        "process_steps": 360,
        "formula_rule": 260,
        "mistake_trap": 240,
        "concept": 260,
        "cloze_candidate": 160,
    }
    return len(back) > limits.get(mode_id, 260)


def _looks_question_like(front: str) -> bool:
    if "?" in front or "？" in front or _QUESTION_START.search(front):
        return True
    return any(
        marker in front
        for marker in (
            "什么",
            "为何",
            "为什么",
            "如何",
            "哪个",
            "哪些",
            "是否",
            "有什么",
            "区别",
            "作用",
            "公式",
            "步骤",
            "常见误区",
            "含义",
            "定义",
        )
    )


def _valid_cloze_text(front: str) -> bool:
    matches = tuple(_VALID_CLOZE.finditer(front))
    if not matches:
        return False
    remainder = _VALID_CLOZE.sub("", front)
    return "{{c" not in remainder.casefold() and "}}" not in remainder


def _is_simply_grounded(card_text: str, source: str) -> bool:
    card_words = set(re.findall(r"[a-z0-9_]{3,}", card_text.casefold()))
    source_words = set(re.findall(r"[a-z0-9_]{3,}", source.casefold()))
    if card_words & source_words:
        return True
    card_cjk = _cjk_bigrams(card_text)
    source_cjk = _cjk_bigrams(source)
    return bool(card_cjk & source_cjk)


def _cjk_bigrams(text: str) -> set[str]:
    characters = "".join(re.findall(r"[\u3400-\u9fff]", text))
    return {characters[index : index + 2] for index in range(len(characters) - 1)}


def _front_leaks_answer(front: str, back: str) -> bool:
    front_core = "".join(re.findall(r"[a-z0-9\u3400-\u9fff]", front.casefold()))
    back_core = "".join(re.findall(r"[a-z0-9\u3400-\u9fff]", back.casefold()))
    return len(back_core) >= 4 and back_core in front_core


def _names_comparison_sides(front: str) -> bool:
    return bool(
        re.search(
            r"(?:\bvs\.?\b|\bversus\b|difference between|compare.+(?:and|with)|"
            r".+(?:与|和).+(?:区别|异同|相比|不同))",
            front,
            re.IGNORECASE,
        )
    )


def _contains_explicit_order(back: str) -> bool:
    markers = re.findall(
        r"(?:首先|其次|然后|接着|最后|第一|第二|第三|"
        r"\bfirst\b|\bthen\b|\bnext\b|\bfinally\b|(?:^|\n)\s*\d+[.)])",
        back,
        re.IGNORECASE,
    )
    return len(markers) >= 2


def _contains_condition(text: str) -> bool:
    return bool(
        re.search(
            r"(?:条件|适用|当.+时|在.+情况下|\bwhen\b|\bif\b|"
            r"\bwhere\b|\bprovided\b|\bappl(?:y|ies)\b)",
            text,
            re.IGNORECASE,
        )
    )


def _definition_term_missing(front: str) -> bool:
    core = re.sub(r"[\s?？!！。，,.、:：;；]", "", front.casefold())
    return len(core) < 4 or bool(
        re.fullmatch(r"(?:它|这|这个|上述内容)(?:是)?什么|what(?:is)?it", core)
    )


def _exam_front_is_vague(front: str) -> bool:
    return bool(
        re.search(
            r"(?:讨论|分析|简述|解释)(?:上述|相关|这个|以下)?内容|"
            r"\b(?:discuss|describe|explain) (?:this|the above|the material)\b",
            front,
            re.IGNORECASE,
        )
    )


def _card_limit_for_density(settings: GenerationSettings) -> int:
    return {"auto": 5, "fewer": 3, "balanced": 5, "more": 8}[
        settings.card_count
    ]
