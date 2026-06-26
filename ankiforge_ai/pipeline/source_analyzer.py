"""Markdown source analysis for the v0.3 import pipeline."""

import hashlib
import os
from datetime import datetime, timezone
from typing import List, Tuple

from ..importers.md_importer import _FENCE_PATTERN, _HEADING_PATTERN
from .models import SourceChunk, SourceDocument

UNTITLED_HEADING = "Untitled"


def analyze_markdown_file(file_path: str) -> Tuple[SourceDocument, List[SourceChunk]]:
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    document = build_source_document(file_path, text)
    return document, build_source_chunks(document, text)


def build_source_document(file_path: str, text: str) -> SourceDocument:
    file_name = os.path.basename(file_path) or "Untitled.md"
    file_hash = compute_text_hash(text)
    return SourceDocument(
        document_id=build_document_id(file_name, file_hash),
        file_path=file_path,
        file_name=file_name,
        file_hash=file_hash,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def build_source_chunks(document: SourceDocument, text: str) -> List[SourceChunk]:
    raw_chunks = _split_markdown_with_heading_paths(text)
    if not raw_chunks:
        raw_chunks = [
            {
                "heading_path": [UNTITLED_HEADING],
                "heading_level": 0,
                "text": text.strip(),
            }
        ]

    chunks = []
    for ordinal, raw_chunk in enumerate(raw_chunks):
        heading_path = raw_chunk["heading_path"]
        chunk_text = raw_chunk["text"]
        chunk_hash = compute_text_hash(chunk_text)
        chunks.append(
            SourceChunk(
                chunk_id=build_chunk_id(
                    document.document_id,
                    heading_path,
                    ordinal,
                    chunk_hash,
                ),
                document_id=document.document_id,
                file_path=document.file_path,
                file_name=document.file_name,
                heading_path=heading_path,
                heading_level=raw_chunk["heading_level"],
                ordinal=ordinal,
                text=chunk_text,
                chunk_hash=chunk_hash,
                source_display=build_source_display(document.file_name, heading_path),
            )
        )

    return chunks


def compute_text_hash(text: str) -> str:
    normalized = _normalize_text_for_hash(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def build_document_id(file_name: str, file_hash: str) -> str:
    return _stable_id("document", file_name, file_hash)


def build_chunk_id(
    document_id: str,
    heading_path: List[str],
    ordinal: int,
    chunk_hash: str,
) -> str:
    return _stable_id(
        "chunk",
        document_id,
        "/".join(heading_path),
        str(ordinal),
        chunk_hash,
    )


def build_source_display(file_name, heading_path) -> str:
    path = [str(part).strip() for part in heading_path or [] if str(part).strip()]
    if not path:
        path = [UNTITLED_HEADING]
    return f"{file_name} > {' > '.join(path)}"


def _split_markdown_with_heading_paths(text: str) -> List[dict]:
    lines = text.splitlines()
    chunks = []
    heading_stack: List[str] = []
    current_heading_path = [UNTITLED_HEADING]
    current_level = 0
    current_lines: List[str] = []
    in_fence = False
    fence_char = ""
    fence_len = 0

    def flush():
        content = "\n".join(current_lines).strip()
        if content:
            chunks.append(
                {
                    "heading_path": list(current_heading_path),
                    "heading_level": current_level,
                    "text": content,
                }
            )

    for line in lines:
        fence_match = _FENCE_PATTERN.match(line)
        if fence_match:
            fence_marker = fence_match.group(1)
            marker_char = fence_marker[0]
            marker_len = len(fence_marker)
            if not in_fence:
                in_fence = True
                fence_char = marker_char
                fence_len = marker_len
            elif marker_char == fence_char and marker_len >= fence_len:
                in_fence = False
                fence_char = ""
                fence_len = 0

            current_lines.append(line)
            continue

        match = None if in_fence else _HEADING_PATTERN.match(line)
        if match:
            flush()
            level = len(match.group(1))
            heading = match.group(2).strip() or UNTITLED_HEADING
            heading_stack = heading_stack[: level - 1]
            heading_stack.append(heading)
            current_heading_path = list(heading_stack)
            current_level = level
            current_lines = []
        else:
            current_lines.append(line)

    flush()
    return chunks


def _normalize_text_for_hash(text: str) -> str:
    return "\n".join(line.rstrip() for line in str(text or "").strip().splitlines())


def _stable_id(*parts: str) -> str:
    raw = "\x1f".join(str(part) for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

