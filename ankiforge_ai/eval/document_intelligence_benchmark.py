"""Deterministic, local-only benchmark for the v0.14 document pipeline."""

from __future__ import annotations

from pathlib import Path

from ankiforge_ai.document import count_blocks_by_kind, document_to_plain_text, import_documents
from ankiforge_ai.intelligence import (
    analyze_document,
    assess_generation_coverage,
    assess_plan_coverage,
    build_local_knowledge_plan,
    chunk_document,
    deduplicate_cards,
    route_template,
)
from ankiforge_ai.pipeline.card_quality import evaluate_card_batch


SCENARIOS = (
    ("python", "documents/sample.py"),
    ("sql", "documents/sample.sql"),
    ("bci_eegnet", "intelligence/bci_eegnet.md"),
    ("math", "intelligence/math_formula.md"),
    ("vocabulary", "intelligence/vocabulary.md"),
    ("biology", "intelligence/biology.md"),
    ("history", "intelligence/history.md"),
    ("process", "intelligence/process.md"),
    ("comparison", "intelligence/comparison.md"),
    ("table", "documents/table.csv"),
    ("transcript", "documents/captions.srt"),
    ("bilingual", "intelligence/bilingual.md"),
    ("ppt", "documents/slides.pptx"),
    ("xlsx", "documents/workbook.xlsx"),
)
EXPECTED_ROUTES = {
    "python": "code_understanding", "sql": "code_understanding",
    "bci_eegnet": "definition", "math": "concept", "vocabulary": "definition",
    "biology": "definition", "history": "concept", "process": "process_steps",
    "comparison": "compare_contrast", "table": "table_relationship",
    "transcript": "transcript_summary_candidate", "bilingual": "definition",
    "ppt": "concept", "xlsx": "formula_rule",
}
_DUPLICATE_SMOKE_FIXTURES = frozenset({"python", "comparison", "ppt"})
_WARNING_SMOKE_FIXTURES = frozenset({"history", "transcript"})
_BLOCKING_SMOKE_FIXTURES = frozenset({"table"})


def evaluate_document_intelligence_suite(fixtures_root: str | Path) -> dict[str, object]:
    """Run all checked-in scenarios without a Provider, network, or Anki."""
    root = Path(fixtures_root)
    outcomes = {}
    failure_reasons = {}
    for fixture_id, relative_path in SCENARIOS:
        try:
            outcomes[fixture_id] = _evaluate_fixture(fixture_id, root / relative_path)
        except Exception as exc:  # benchmark failures remain deterministic and safe
            outcomes[fixture_id] = {
                "fixture_id": fixture_id,
                "parse_passed": False,
                "structure_preserved": False,
                "source_locations_preserved": False,
                "plan_grounded": False,
                "chunk_count": 0,
                "chunk_sizes": (),
                "point_count": 0,
                "route": "",
                "warning_count": 0,
                "blocking_count": 0,
                "duplicate_count": 0,
                "failure_reason": type(exc).__name__,
            }
            failure_reasons[fixture_id] = type(exc).__name__

    values = tuple(outcomes.values())
    count = len(values)
    card_count = count * 2
    chunk_count_distribution = {}
    chunk_size_distribution = {
        "0-32": 0,
        "33-64": 0,
        "65-128": 0,
        "129+": 0,
    }
    for item in values:
        key = str(item["chunk_count"])
        chunk_count_distribution[key] = chunk_count_distribution.get(key, 0) + 1
        for size in item["chunk_sizes"]:
            chunk_size_distribution[_chunk_size_bucket(size)] += 1
    total_points = sum(item["point_count"] for item in values)
    metrics = {
        "fixture_count": count,
        "parse_pass_rate": _ratio(sum(item["parse_passed"] for item in values), count),
        "structure_preservation_rate": _ratio(
            sum(item["structure_preserved"] for item in values), count
        ),
        "source_location_coverage_rate": _ratio(
            sum(item["source_locations_preserved"] for item in values), count
        ),
        "planning_coverage_rate": _ratio(sum(item["plan_grounded"] for item in values), count),
        "template_routing_accuracy": _ratio(
            sum(item["route"] == EXPECTED_ROUTES[item["fixture_id"]] for item in values), count
        ),
        "duplicate_rate": _ratio(sum(item["duplicate_count"] for item in values), card_count),
        "warning_rate": _ratio(sum(item["warning_count"] for item in values), card_count),
        "blocking_rate": _ratio(sum(item["blocking_count"] for item in values), card_count),
        "chunk_count_distribution": chunk_count_distribution,
        "chunk_size_distribution": chunk_size_distribution,
        "quality_fixture_kind": "synthetic_local_rule_smoke",
        "planning_coverage": {
            "covered_points": total_points if all(item["plan_grounded"] for item in values) else 0,
            "total_points": total_points,
        },
    }
    return {
        "fixtures": outcomes,
        "metrics": metrics,
        "failed_fixture_reasons": failure_reasons,
    }


def _evaluate_fixture(fixture_id: str, path: Path) -> dict[str, object]:
    document = import_documents((path,))[0]
    analysis = analyze_document(document)
    chunks = chunk_document(document)
    plan = build_local_knowledge_plan(document, chunks, analysis)
    plan_coverage = assess_plan_coverage(document, chunks, plan)
    block_kinds = tuple(
        block.kind for section in document.sections for block in section.blocks
    )
    route = route_template(analysis, block_kinds=block_kinds)
    source_text = document_to_plain_text(document)
    point = plan.points[0]
    coverage = assess_generation_coverage(
        (point,),
        ({"candidate_id": fixture_id + "-coverage", "point_id": point.point_id, "section_id": point.section_id},),
        section_ids=(point.section_id,),
        max_cards=1,
    )
    cards = _quality_smoke_cards(fixture_id, chunks[0].chunk_id)
    quality = evaluate_card_batch(cards)
    dedup = deduplicate_cards(cards)
    kind_counts = count_blocks_by_kind(document)
    return {
        "fixture_id": fixture_id,
        "parse_passed": bool(document.sections),
        "structure_preserved": bool(kind_counts) and analysis.block_count == sum(kind_counts.values()),
        "source_locations_preserved": all(
            block.location is not None
            for section in document.sections
            for block in section.blocks
        ),
        "plan_grounded": plan_coverage.is_grounded and not coverage.missing_high_priority_point_ids,
        "chunk_count": len(chunks),
        "chunk_sizes": tuple(chunk.char_count for chunk in chunks),
        "point_count": len(plan.points),
        "route": route.mode_id,
        "warning_count": quality.warning_count,
        "blocking_count": quality.blocking_count,
        "duplicate_count": len(dedup.duplicate_candidate_ids),
        "source_char_count": len(source_text),
        "failure_reason": None,
    }


def _quality_smoke_cards(
    fixture_id: str,
    chunk_id: str,
) -> tuple[dict[str, str], dict[str, str]]:
    """Exercise local quality states without pretending to score AI output."""

    first = {
        "candidate_id": fixture_id + "-card-1",
        "chunk_id": chunk_id,
        "front": "What should this local fixture teach?",
        "back": "It teaches a deterministic, reviewable fact.",
    }
    second = {
        "candidate_id": fixture_id + "-card-2",
        "chunk_id": chunk_id,
        "front": "What distinct detail should this fixture teach?",
        "back": "It teaches another deterministic, reviewable fact.",
    }
    if fixture_id in _DUPLICATE_SMOKE_FIXTURES:
        second["front"] = first["front"]
        second["back"] = first["back"]
    elif fixture_id in _WARNING_SMOKE_FIXTURES:
        second["front"] = "Why?"
    elif fixture_id in _BLOCKING_SMOKE_FIXTURES:
        second["back"] = ""
    return first, second


def _chunk_size_bucket(size: int) -> str:
    if size <= 32:
        return "0-32"
    if size <= 64:
        return "33-64"
    if size <= 128:
        return "65-128"
    return "129+"


def _ratio(numerator: int, denominator: int) -> str:
    return f"{numerator}/{denominator}"
