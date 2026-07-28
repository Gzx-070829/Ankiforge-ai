import math
from dataclasses import asdict, dataclass
from typing import Dict, Union


MAX_SOURCE_FILE_BYTES = 10 * 1024 * 1024
MAX_TEXT_FILE_BYTES = 5 * 1024 * 1024
MAX_TOTAL_BATCH_BYTES = 25 * 1024 * 1024
MAX_FILES_PER_BATCH = 20
MAX_ARCHIVE_MEMBERS = 2_048
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_COMPRESSION_RATIO = 100.0
MAX_MEMBER_BYTES = 20 * 1024 * 1024
MAX_DOCUMENT_BLOCKS = 20_000
MAX_TABLE_ROWS = 10_000
MAX_TABLE_COLUMNS = 256
MAX_CELL_CHARS = 32_000
MAX_JSON_DEPTH = 64
MAX_XML_DEPTH = 64
MAX_XML_ELEMENTS = 100_000
MAX_TEXT_CHARS = 5_000_000
MAX_NOTEBOOK_OUTPUT_CHARS = 100_000
MAX_CHUNK_CHARS = 12_000
TARGET_CHUNK_CHARS = 6_000
MAX_DOCUMENT_CHUNKS = 48
MAX_AI_CALLS_PER_RUN = 12


@dataclass(frozen=True)
class DocumentLimits:
    max_source_file_bytes: int = MAX_SOURCE_FILE_BYTES
    max_text_file_bytes: int = MAX_TEXT_FILE_BYTES
    max_total_batch_bytes: int = MAX_TOTAL_BATCH_BYTES
    max_files_per_batch: int = MAX_FILES_PER_BATCH
    max_archive_members: int = MAX_ARCHIVE_MEMBERS
    max_archive_uncompressed_bytes: int = MAX_ARCHIVE_UNCOMPRESSED_BYTES
    max_archive_compression_ratio: float = MAX_ARCHIVE_COMPRESSION_RATIO
    max_member_bytes: int = MAX_MEMBER_BYTES
    max_document_blocks: int = MAX_DOCUMENT_BLOCKS
    max_table_rows: int = MAX_TABLE_ROWS
    max_table_columns: int = MAX_TABLE_COLUMNS
    max_cell_chars: int = MAX_CELL_CHARS
    max_json_depth: int = MAX_JSON_DEPTH
    max_xml_depth: int = MAX_XML_DEPTH
    max_xml_elements: int = MAX_XML_ELEMENTS
    max_text_chars: int = MAX_TEXT_CHARS
    max_notebook_output_chars: int = MAX_NOTEBOOK_OUTPUT_CHARS
    max_chunk_chars: int = MAX_CHUNK_CHARS
    target_chunk_chars: int = TARGET_CHUNK_CHARS
    max_document_chunks: int = MAX_DOCUMENT_CHUNKS
    max_ai_calls_per_run: int = MAX_AI_CALLS_PER_RUN

    def __post_init__(self) -> None:
        values = asdict(self)
        ratio = values.pop("max_archive_compression_ratio")
        for name, value in values.items():
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer")
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        if isinstance(ratio, bool) or not isinstance(ratio, (int, float)):
            raise TypeError("max_archive_compression_ratio must be numeric")
        if not math.isfinite(ratio) or ratio <= 0:
            raise ValueError(
                "max_archive_compression_ratio must be finite and positive"
            )
        if self.max_text_file_bytes > self.max_source_file_bytes:
            raise ValueError(
                "max_text_file_bytes must not exceed max_source_file_bytes"
            )
        if self.target_chunk_chars > self.max_chunk_chars:
            raise ValueError("target_chunk_chars must not exceed max_chunk_chars")

    def to_safe_dict(self) -> Dict[str, Union[int, float]]:
        return asdict(self)


DEFAULT_DOCUMENT_LIMITS = DocumentLimits()
