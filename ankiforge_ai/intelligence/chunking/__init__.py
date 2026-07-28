"""Public structural chunking interface."""

from .models import DocumentChunk
from .structural import (
    MAX_CHUNK_CHARS,
    MAX_DOCUMENT_CHUNKS,
    TARGET_CHUNK_CHARS,
    chunk_document,
)

__all__ = [
    "DocumentChunk",
    "MAX_CHUNK_CHARS",
    "MAX_DOCUMENT_CHUNKS",
    "TARGET_CHUNK_CHARS",
    "chunk_document",
]
