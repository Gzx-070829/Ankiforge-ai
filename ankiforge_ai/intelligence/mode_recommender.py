"""Deterministic mode recommendations derived from bounded analysis signals."""

from .models import DocumentAnalysis


def recommend_modes(analysis: DocumentAnalysis) -> tuple[str, ...]:
    modes = []
    for enabled, mode_id in (
        (analysis.has_code, "code_understanding"),
        (analysis.has_tables, "table_relationship"),
        (analysis.has_transcript, "transcript_summary_candidate"),
        (analysis.has_formulas, "formula_rule"),
        (analysis.has_comparisons, "compare_contrast"),
        (analysis.has_processes, "process_steps"),
        (analysis.has_definitions, "definition"),
    ):
        if enabled:
            modes.append(mode_id)
    modes.append("concept")
    return tuple(modes)
