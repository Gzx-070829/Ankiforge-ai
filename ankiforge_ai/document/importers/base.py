from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, Union

from ..limits import DEFAULT_DOCUMENT_LIMITS, DocumentLimits
from ..models import DocumentIR
from ..source_labels import get_safe_source_label


@dataclass(frozen=True)
class ImportInspection:
    importer_id: str
    source_label: str
    detected_file_type: str
    warnings: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not all(
            isinstance(value, str) and value
            for value in (
                self.importer_id,
                self.source_label,
                self.detected_file_type,
            )
        ):
            raise ValueError("inspection identifiers and labels must be non-empty")
        if self.source_label != get_safe_source_label(self.source_label):
            raise ValueError("inspection source_label must be safe")
        object.__setattr__(self, "warnings", tuple(self.warnings))


class DocumentImporter(ABC):
    importer_id: str
    supported_extensions: Tuple[str, ...]

    @abstractmethod
    def availability(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def inspect(
        self,
        path: Union[str, Path],
        limits: DocumentLimits = DEFAULT_DOCUMENT_LIMITS,
    ) -> ImportInspection:
        raise NotImplementedError

    @abstractmethod
    def import_document(
        self,
        path: Union[str, Path],
        limits: DocumentLimits = DEFAULT_DOCUMENT_LIMITS,
    ) -> DocumentIR:
        raise NotImplementedError
