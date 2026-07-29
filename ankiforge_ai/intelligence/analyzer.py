"""Bounded, deterministic analysis over reviewed immutable DocumentIR."""

import math
import re

from ..document import BlockKind, DocumentIR, count_blocks_by_kind

from .mode_recommender import recommend_modes
from .models import DocumentAnalysis


_DEFINITION = re.compile(
    r"(?:\b(?:means|defined\s+as|refers\s+to)\b"
    r"|\b(?:is|are)\s+(?:an?\s+|the\s+type\s+of\b|types?\s+of\b)"
    r"|(?:定义为|是指|指的是))",
    re.IGNORECASE,
)
_COMPARISON = re.compile(
    r"(?:\b(?:unlike|versus|whereas|compared\s+(?:with|to)|difference|similar)\b"
    r"|(?:相比|区别|不同于|相同于|而非|对比))",
    re.IGNORECASE,
)
_PROCESS_STAGE = re.compile(
    r"(?:\b(?:first|then|next|finally|step\s*\d*)\b"
    r"|(?:首先|然后|接着|最后|步骤\s*[一二三四五六七八九十\d]*))",
    re.IGNORECASE,
)
_CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
_LATIN = re.compile(r"[A-Za-z]")


def analyze_document(document: DocumentIR) -> DocumentAnalysis:
    if not isinstance(document, DocumentIR):
        raise TypeError("document must be a DocumentIR")

    definition_count = 0
    comparison_count = 0
    process_count = 0
    formula_count = 0
    code_count = 0
    table_count = 0
    transcript_count = 0
    char_count = 0
    cjk_count = 0
    latin_count = 0
    block_count = 0
    content_block_count = 0
    estimated_points = 0

    for section in document.sections:
        for block in section.blocks:
            block_count += 1
            text = block.text
            if not text.strip():
                continue
            content_block_count += 1
            text_length = len(text)
            char_count += text_length
            cjk_count += sum(1 for _ in _CJK.finditer(text))
            latin_count += sum(1 for _ in _LATIN.finditer(text))
            definition_count += int(bool(_DEFINITION.search(text)))
            comparison_count += int(bool(_COMPARISON.search(text)))
            process_count += int(
                sum(1 for _ in _PROCESS_STAGE.finditer(text)) >= 2
            )
            formula_count += int(block.kind is BlockKind.FORMULA)
            code_count += int(block.kind is BlockKind.CODE)
            table_count += int(block.kind is BlockKind.TABLE)
            transcript_count += int(block.kind is BlockKind.TRANSCRIPT)
            estimated_points += max(1, math.ceil(text_length / 800))

    dominant_language = _dominant_language(cjk_count, latin_count)
    specialist_count = sum(
        count > 0
        for count in (formula_count, code_count, table_count, transcript_count)
    )
    if content_block_count == 0:
        document_kind = "empty"
    elif specialist_count > 1:
        document_kind = "mixed"
    elif code_count:
        document_kind = "code"
    elif table_count:
        document_kind = "table"
    elif transcript_count:
        document_kind = "transcript"
    elif formula_count:
        document_kind = "formula"
    elif any(
        block.kind
        in {
            BlockKind.HEADING,
            BlockKind.LIST,
            BlockKind.LIST_ITEM,
            BlockKind.QUOTE,
        }
        for section in document.sections
        for block in section.blocks
    ):
        document_kind = "structured"
    else:
        document_kind = "text"

    distinct_signals = sum(
        value > 0
        for value in (
            definition_count,
            comparison_count,
            process_count,
            formula_count,
            code_count,
            table_count,
            transcript_count,
        )
    )
    structured_blocks = formula_count + code_count + table_count + transcript_count
    structured_ratio = (
        structured_blocks / content_block_count if content_block_count else 0.0
    )
    confidence = (
        0.25
        if content_block_count == 0
        else min(0.98, round(0.55 + distinct_signals * 0.06 + structured_ratio * 0.08, 2))
    )
    warnings = ("analysis.empty_document",) if content_block_count == 0 else ()
    kind_counts = count_blocks_by_kind(document)
    provisional = DocumentAnalysis(
        document_id=document.document_id,
        dominant_language=dominant_language,
        document_kind=document_kind,
        section_count=len(document.sections),
        block_count=block_count,
        char_count=char_count,
        content_density=round(char_count / block_count, 2) if block_count else 0.0,
        definition_count=definition_count,
        comparison_count=comparison_count,
        process_count=process_count,
        formula_count=formula_count,
        code_block_count=code_count,
        table_block_count=table_count,
        transcript_block_count=transcript_count,
        estimated_knowledge_points=min(96, estimated_points),
        recommended_modes=(),
        warnings=warnings,
        confidence=confidence,
        block_kind_counts=kind_counts,
    )
    return DocumentAnalysis(
        **{
            **provisional.__dict__,
            "recommended_modes": recommend_modes(provisional),
        }
    )


def _dominant_language(cjk_count: int, latin_count: int) -> str:
    total = cjk_count + latin_count
    if total == 0:
        return "unknown"
    if (
        min(cjk_count, latin_count) >= 8
        or (
            cjk_count
            and latin_count
            and min(cjk_count, latin_count) / total >= 0.2
        )
    ):
        return "mixed"
    return "zh" if cjk_count > latin_count else "en"
