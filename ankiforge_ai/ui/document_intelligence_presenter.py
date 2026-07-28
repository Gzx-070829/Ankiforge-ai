"""Pure bilingual view models for document intelligence UI surfaces."""

from __future__ import annotations

from dataclasses import dataclass

from ..document import DocumentIR
from ..intelligence import (
    DocumentAnalysis,
    GenerationRun,
    GenerationStage,
    IntelligenceLevel,
    PlanEstimate,
)


_COPY = {
    "zh": {
        "summary": "{sections} 个章节 · {blocks} 个内容块 · {chars} 个字符",
        "auto": "自动推荐",
        "mode_code_understanding": "代码理解",
        "mode_table_relationship": "表格关系",
        "mode_transcript_summary_candidate": "转录摘要",
        "mode_formula_rule": "公式与规则",
        "mode_compare_contrast": "比较与对照",
        "mode_process_steps": "流程步骤",
        "mode_definition": "定义",
        "mode_concept": "概念",
        "mode_general": "综合理解",
        "fast": "快速",
        "standard": "标准",
        "deep": "深度",
        "calls": "计划 {planned} 次 · 最多 {maximum} 次调用",
        "estimate": "{chunks} 个分块 · 预计 {minimum}–{maximum} 张卡片",
        "batch_estimate": (
            "{documents} 个文档 · {chunks} 个分块 · 预计 "
            "{minimum}–{maximum} 张卡片"
        ),
        "confirm_fast": "计划调用仅包含分组生成。",
        "confirm_standard": (
            "计划调用包含 1 次规划和分组生成；"
            "只有本地检查需要时才调用有来源依据的修复。"
        ),
        "confirm_deep": (
            "计划调用包含 1 次规划、分组生成和 1 次检查；"
            "只有需要时才调用有来源依据的修复和最多 1 次覆盖补充。"
        ),
        "stage_analyzing": "分析文档",
        "stage_planning": "规划知识点",
        "stage_generating": "生成卡片",
        "stage_reviewing": "检查质量",
        "stage_repairing": "修复卡片",
        "stage_checking_coverage": "检查覆盖度",
        "stage_deduplicating": "去除重复",
        "stage_completed": "生成完成",
        "stage_failed": "生成未完成",
        "stage_superseded": "已被新任务替代",
        "progress": "{completed}/{total} 个分块完成",
        "retry": "仅重试失败分块",
    },
    "en": {
        "summary": (
            "{sections} {section_word} · {blocks} {block_word} · "
            "{chars} {character_word}"
        ),
        "auto": "Auto recommendation",
        "mode_code_understanding": "Code understanding",
        "mode_table_relationship": "Table relationships",
        "mode_transcript_summary_candidate": "Transcript summary",
        "mode_formula_rule": "Formula and rule",
        "mode_compare_contrast": "Compare and contrast",
        "mode_process_steps": "Process steps",
        "mode_definition": "Definition",
        "mode_concept": "Concept",
        "mode_general": "General understanding",
        "fast": "Fast",
        "standard": "Standard",
        "deep": "Deep",
        "calls": "{planned} planned · up to {maximum} calls",
        "estimate": "{chunks} chunks · {minimum}–{maximum} cards",
        "batch_estimate": (
            "{documents} documents · {chunks} chunks · "
            "{minimum}–{maximum} cards"
        ),
        "confirm_fast": "Planned calls are grouped generation only.",
        "confirm_standard": (
            "Planned calls include one planner and grouped generation; "
            "a source-grounded repair call is made only if needed."
        ),
        "confirm_deep": (
            "Planned calls include one planner, grouped generation, and one "
            "critic; source-grounded repair and one coverage supplement are "
            "called only if needed."
        ),
        "stage_analyzing": "Analyzing document",
        "stage_planning": "Planning knowledge points",
        "stage_generating": "Generating cards",
        "stage_reviewing": "Checking quality",
        "stage_repairing": "Repairing cards",
        "stage_checking_coverage": "Checking coverage",
        "stage_deduplicating": "Removing duplicates",
        "stage_completed": "Generation complete",
        "stage_failed": "Generation incomplete",
        "stage_superseded": "Replaced by a newer request",
        "progress": "{completed}/{total} chunks complete",
        "retry": "Retry failed chunks only",
    },
}


@dataclass(frozen=True)
class DocumentSummaryView:
    title: str
    detail: str
    warning_count: int


@dataclass(frozen=True)
class AutoRecommendationView:
    label: str
    modes: tuple[str, ...]
    detail: str


@dataclass(frozen=True)
class IntelligenceEstimateView:
    level: IntelligenceLevel
    level_label: str
    call_range: str
    detail: str
    requires_confirmation: bool
    confirmation_text: str


@dataclass(frozen=True)
class GenerationProgressView:
    stage_label: str
    progress_text: str
    completed_chunks: int
    total_chunks: int
    failed_chunks: int
    show_retry_failed: bool
    retry_label: str


def present_document_summary(
    document: DocumentIR,
    analysis: DocumentAnalysis,
    *,
    language: str,
) -> DocumentSummaryView:
    if not isinstance(document, DocumentIR):
        raise TypeError("document must be a DocumentIR")
    if not isinstance(analysis, DocumentAnalysis):
        raise TypeError("analysis must be a DocumentAnalysis")
    if document.document_id != analysis.document_id:
        raise ValueError("document and analysis do not match")
    copy = _copy_for(language)
    return DocumentSummaryView(
        title=document.source_label,
        detail=copy["summary"].format(
            sections=analysis.section_count,
            blocks=analysis.block_count,
            chars=analysis.char_count,
            section_word=(
                "section" if analysis.section_count == 1 else "sections"
            ),
            block_word="block" if analysis.block_count == 1 else "blocks",
            character_word=(
                "character" if analysis.char_count == 1 else "characters"
            ),
        ),
        warning_count=len(document.warnings) + len(analysis.warnings),
    )


def present_auto_recommendation(
    analysis: DocumentAnalysis,
    *,
    language: str,
) -> AutoRecommendationView:
    if not isinstance(analysis, DocumentAnalysis):
        raise TypeError("analysis must be a DocumentAnalysis")
    copy = _copy_for(language)
    mode_ids = analysis.recommended_modes or ("general",)
    modes = tuple(
        copy.get(f"mode_{mode_id}", copy["mode_general"])
        for mode_id in mode_ids
    )
    return AutoRecommendationView(
        label=copy["auto"],
        modes=modes,
        detail=" · ".join(modes),
    )


def present_intelligence_estimate(
    estimate: PlanEstimate,
    *,
    language: str,
    card_limit: int | None = None,
) -> IntelligenceEstimateView:
    if not isinstance(estimate, PlanEstimate):
        raise TypeError("estimate must be a PlanEstimate")
    copy = _copy_for(language)
    card_minimum, card_maximum = _bounded_card_range(
        estimate.estimated_card_min,
        estimate.estimated_card_max,
        card_limit,
    )
    return IntelligenceEstimateView(
        level=estimate.level,
        level_label=copy[estimate.level.value],
        call_range=copy["calls"].format(
            planned=_planned_call_count(
                estimate.level,
                estimate.chunk_count,
            ),
            maximum=estimate.estimated_call_max,
        ),
        detail=copy["estimate"].format(
            chunks=estimate.chunk_count,
            minimum=card_minimum,
            maximum=card_maximum,
        ),
        requires_confirmation=estimate.requires_confirmation,
        confirmation_text=copy[f"confirm_{estimate.level.value}"],
    )


def present_batch_intelligence_estimate(
    estimates,
    *,
    language: str,
    card_limit: int | None = None,
) -> IntelligenceEstimateView:
    selected = tuple(estimates)
    if not selected or not all(
        isinstance(estimate, PlanEstimate) for estimate in selected
    ):
        raise ValueError("estimates must contain at least one PlanEstimate")
    level = selected[0].level
    if any(estimate.level is not level for estimate in selected):
        raise ValueError("batch estimates must use one intelligence level")
    copy = _copy_for(language)
    chunk_count = sum(estimate.chunk_count for estimate in selected)
    card_minimum, card_maximum = _bounded_card_range(
        sum(estimate.estimated_card_min for estimate in selected),
        sum(estimate.estimated_card_max for estimate in selected),
        card_limit,
    )
    return IntelligenceEstimateView(
        level=level,
        level_label=copy[level.value],
        call_range=copy["calls"].format(
            planned=_planned_call_count(level, chunk_count),
            maximum=selected[0].estimated_call_max,
        ),
        detail=copy["batch_estimate"].format(
            documents=len(selected),
            chunks=chunk_count,
            minimum=card_minimum,
            maximum=card_maximum,
        ),
        requires_confirmation=selected[0].requires_confirmation,
        confirmation_text=copy[f"confirm_{level.value}"],
    )


def _bounded_card_range(
    minimum: int,
    maximum: int,
    card_limit: int | None,
) -> tuple[int, int]:
    if card_limit is None:
        return minimum, maximum
    if (
        isinstance(card_limit, bool)
        or not isinstance(card_limit, int)
        or not 1 <= card_limit <= 96
    ):
        raise ValueError("card_limit must be between 1 and 96")
    return min(minimum, card_limit), min(maximum, card_limit)


def stage_label(stage: GenerationStage, *, language: str) -> str:
    try:
        normalized = GenerationStage(stage)
    except (TypeError, ValueError):
        raise ValueError("stage is unsupported") from None
    copy = _copy_for(language)
    return copy[f"stage_{normalized.value}"]


def present_generation_progress(
    run: GenerationRun,
    *,
    language: str,
) -> GenerationProgressView:
    if not isinstance(run, GenerationRun):
        raise TypeError("run must be a GenerationRun")
    copy = _copy_for(language)
    completed = sum(
        chunk.state.value in {"succeeded", "failed", "skipped"}
        for chunk in run.chunks
    )
    failed = len(run.failed_chunk_ids)
    return GenerationProgressView(
        stage_label=stage_label(run.stage, language=language),
        progress_text=copy["progress"].format(
            completed=completed,
            total=len(run.chunks),
        ),
        completed_chunks=completed,
        total_chunks=len(run.chunks),
        failed_chunks=failed,
        show_retry_failed=failed > 0,
        retry_label=copy["retry"],
    )


def _copy_for(language: str) -> dict[str, str]:
    if language not in _COPY:
        raise ValueError("language must be zh or en")
    return _COPY[language]


def _planned_call_count(
    level: IntelligenceLevel,
    chunk_count: int,
) -> int:
    generation_calls = min(3, max(1, chunk_count))
    if level is IntelligenceLevel.FAST:
        return generation_calls
    if level is IntelligenceLevel.STANDARD:
        return 1 + generation_calls
    return 2 + generation_calls


__all__ = [
    "AutoRecommendationView",
    "DocumentSummaryView",
    "GenerationProgressView",
    "IntelligenceEstimateView",
    "present_auto_recommendation",
    "present_batch_intelligence_estimate",
    "present_document_summary",
    "present_generation_progress",
    "present_intelligence_estimate",
    "stage_label",
]
