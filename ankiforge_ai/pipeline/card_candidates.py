"""Deterministic mock card candidate generation for the pipeline layer."""

from typing import Iterable, List

from .models import CardCandidate, HumanSelection


def build_candidate_id(selection_id: str) -> str:
    return f"cc_{selection_id}_0"


def create_card_candidate(selection: HumanSelection) -> CardCandidate:
    if selection.decision != "selected":
        raise ValueError("Card candidates require a selected human selection.")

    return CardCandidate(
        candidate_id=build_candidate_id(selection.selection_id),
        selection_id=selection.selection_id,
        point_id=selection.point_id,
        document_id=selection.document_id,
        chunk_id=selection.chunk_id,
        source_display=selection.source_display,
        heading_path=list(selection.heading_path),
        ordinal=selection.ordinal,
        card_type="basic",
        front=f"What is {selection.title}?",
        back=selection.explanation,
        extra=(
            f"Evidence: {selection.evidence}\n"
            f"Source: {selection.source_display}"
        ),
        tags=list(selection.tags),
        source=selection.source_display,
    )


def create_card_candidates(
    selections: Iterable[HumanSelection],
) -> List[CardCandidate]:
    return [
        create_card_candidate(selection)
        for selection in selections
        if selection.decision == "selected"
    ]
