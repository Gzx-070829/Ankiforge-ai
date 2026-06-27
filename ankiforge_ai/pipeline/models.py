"""Pure data models for the import pipeline."""

from dataclasses import asdict, dataclass
from typing import List


@dataclass
class SourceDocument:
    document_id: str
    file_path: str
    file_name: str
    file_hash: str
    created_at: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SourceChunk:
    chunk_id: str
    document_id: str
    file_path: str
    file_name: str
    heading_path: List[str]
    heading_level: int
    ordinal: int
    text: str
    chunk_hash: str
    source_display: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class KnowledgePoint:
    point_id: str
    document_id: str
    chunk_id: str
    source_display: str
    heading_path: List[str]
    ordinal: int
    title: str
    explanation: str
    evidence: str
    tags: List[str]
    importance: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HumanSelection:
    selection_id: str
    point_id: str
    document_id: str
    chunk_id: str
    source_display: str
    heading_path: List[str]
    ordinal: int
    title: str
    explanation: str
    evidence: str
    tags: List[str]
    importance: str
    decision: str = "selected"
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

