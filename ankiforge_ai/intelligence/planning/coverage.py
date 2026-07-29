"""Deterministic plan grounding and coverage assessment."""

from ...document import DocumentIR

from ..chunking import DocumentChunk
from .local_planner import _validated_chunks, normalize_point_text
from .models import KnowledgePlan, PlanCoverage


def assess_plan_coverage(
    document: DocumentIR,
    chunks,
    plan: KnowledgePlan,
) -> PlanCoverage:
    resolved_chunks = _validated_chunks(document, chunks)
    if not isinstance(plan, KnowledgePlan) or plan.document_id != document.document_id:
        raise ValueError("plan must match the coverage document")
    by_id = {chunk.chunk_id: chunk for chunk in resolved_chunks}
    plan_chunk_ids = set(plan.chunk_ids)
    plan_chunks_valid = plan_chunk_ids.issubset(by_id)
    covered_chunks = set()
    covered_sections = set()
    invalid_points = []
    duplicate_points = []
    seen_titles = set()
    for point in plan.points:
        normalized = normalize_point_text(point.title)
        if normalized in seen_titles:
            duplicate_points.append(point.point_id)
        else:
            seen_titles.add(normalized)
        source_chunks = tuple(
            by_id.get(chunk_id)
            for chunk_id in point.source_chunk_ids
        )
        expected_locations = _ordered_locations(
            chunk for chunk in source_chunks if chunk is not None
        )
        grounded = (
            plan_chunks_valid
            and set(point.source_chunk_ids).issubset(plan_chunk_ids)
            and all(chunk is not None for chunk in source_chunks)
            and all(
                chunk.section_id == point.section_id
                for chunk in source_chunks
            )
            and point.source_locations == expected_locations
            and any(
                normalized and normalized in normalize_point_text(chunk.text)
                for chunk in source_chunks
            )
        )
        if not grounded:
            invalid_points.append(point.point_id)
            continue
        covered_chunks.update(point.source_chunk_ids)
        covered_sections.add(point.section_id)

    ordered_chunk_ids = tuple(chunk.chunk_id for chunk in resolved_chunks)
    ordered_section_ids = tuple(section.section_id for section in document.sections)
    return PlanCoverage(
        covered_chunk_ids=tuple(
            chunk_id for chunk_id in ordered_chunk_ids if chunk_id in covered_chunks
        ),
        uncovered_chunk_ids=tuple(
            chunk_id for chunk_id in ordered_chunk_ids if chunk_id not in covered_chunks
        ),
        covered_section_ids=tuple(
            section_id
            for section_id in ordered_section_ids
            if section_id in covered_sections
        ),
        uncovered_section_ids=tuple(
            section_id
            for section_id in ordered_section_ids
            if section_id not in covered_sections
        ),
        duplicate_point_ids=tuple(duplicate_points),
        invalid_point_ids=tuple(invalid_points),
        is_grounded=plan_chunks_valid and not invalid_points,
    )


def _ordered_locations(chunks) -> tuple:
    result = []
    seen = set()
    for chunk in chunks:
        for location in chunk.source_locations:
            if location not in seen:
                seen.add(location)
                result.append(location)
    return tuple(result)
