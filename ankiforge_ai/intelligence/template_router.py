"""Pure template routing with explicit-mode precedence."""

from __future__ import annotations

from ..document import BlockKind
from ..pipeline.generation_settings import (
    get_card_mode_profile,
    selectable_card_mode_profiles,
)

from .models import DocumentAnalysis, TemplateRoute


_TEMPLATE_BY_MODE = {
    "concept": "concept",
    "definition": "definition",
    "exam": "exam_answer",
    "quick_review": "quick_review",
    "compare_contrast": "compare_contrast",
    "process_steps": "process_steps",
    "formula_rule": "formula_rule",
    "mistake_trap": "mistake_trap",
    "code_understanding": "concept",
    "table_relationship": "compare_contrast",
    "transcript_summary_candidate": "concept",
}
_CONSTRAINTS = {
    "code_understanding": "preserve_code_context",
    "table_relationship": "preserve_table_headers_and_relationships",
    "transcript_summary_candidate": "preserve_timestamp_context",
    "formula_rule": "preserve_formula_and_conditions",
    "compare_contrast": "compare_on_shared_dimension",
    "process_steps": "preserve_explicit_order",
    "definition": "preserve_term_and_definition",
    "mistake_trap": "require_explicit_misconception",
}


def route_template(
    analysis: DocumentAnalysis,
    requested_mode: str = "auto",
    *,
    point_type: str | None = None,
    block_kinds=(),
) -> TemplateRoute:
    if not isinstance(analysis, DocumentAnalysis):
        raise TypeError("analysis must be a DocumentAnalysis")
    selectable = {
        profile.mode_id for profile in selectable_card_mode_profiles()
    }
    if requested_mode not in selectable:
        raise ValueError("requested mode must be a selectable card mode")

    if requested_mode != "auto":
        return TemplateRoute(
            mode_id=requested_mode,
            template_id=_TEMPLATE_BY_MODE[requested_mode],
            confidence=1.0,
            reason_code="explicit_mode",
            source_constraints=_source_constraints(requested_mode),
            overridden=True,
        )

    try:
        normalized_kinds = {
            kind if isinstance(kind, BlockKind) else BlockKind(kind)
            for kind in block_kinds
        }
    except (TypeError, ValueError):
        raise ValueError("block_kinds must contain known block kinds") from None
    mode_id, reason_code, confidence = _auto_mode(
        analysis, point_type, normalized_kinds
    )
    return TemplateRoute(
        mode_id=mode_id,
        template_id=_TEMPLATE_BY_MODE[mode_id],
        confidence=confidence,
        reason_code=reason_code,
        source_constraints=_source_constraints(mode_id),
        overridden=False,
    )


def _auto_mode(
    analysis: DocumentAnalysis,
    point_type: str | None,
    block_kinds: set[BlockKind],
) -> tuple[str, str, float]:
    normalized_type = point_type.casefold() if isinstance(point_type, str) else ""
    point_rules = (
        (
            normalized_type in {"formula", "rule"} or BlockKind.FORMULA in block_kinds,
            "formula_rule",
            "auto.formula",
        ),
        (
            normalized_type in {"code", "code_understanding"}
            or BlockKind.CODE in block_kinds,
            "code_understanding",
            "auto.code",
        ),
        (
            normalized_type in {"table", "relationship"}
            or BlockKind.TABLE in block_kinds,
            "table_relationship",
            "auto.table",
        ),
        (
            normalized_type in {"transcript", "summary"}
            or BlockKind.TRANSCRIPT in block_kinds,
            "transcript_summary_candidate",
            "auto.transcript",
        ),
        (
            normalized_type in {"comparison", "compare"},
            "compare_contrast",
            "auto.comparison",
        ),
        (
            normalized_type in {"process", "sequence"},
            "process_steps",
            "auto.process",
        ),
        (
            normalized_type in {"definition", "term"},
            "definition",
            "auto.definition",
        ),
    )
    for matches, mode_id, reason in point_rules:
        if matches:
            return mode_id, reason, 0.92

    analysis_rules = (
        (analysis.has_code, "code_understanding", "auto.code"),
        (analysis.has_tables, "table_relationship", "auto.table"),
        (
            analysis.has_transcript,
            "transcript_summary_candidate",
            "auto.transcript",
        ),
        (analysis.has_formulas, "formula_rule", "auto.formula"),
        (analysis.has_comparisons, "compare_contrast", "auto.comparison"),
        (analysis.has_processes, "process_steps", "auto.process"),
        (analysis.has_definitions, "definition", "auto.definition"),
    )
    for matches, mode_id, reason in analysis_rules:
        if matches:
            return mode_id, reason, max(0.8, analysis.confidence)
    return "concept", "auto.concept_fallback", max(0.5, analysis.confidence)


def _source_constraints(mode_id: str) -> tuple[str, ...]:
    constraint = _CONSTRAINTS.get(mode_id)
    if constraint is None:
        return ("grounded_in_source_chunks",)
    return ("grounded_in_source_chunks", constraint)
