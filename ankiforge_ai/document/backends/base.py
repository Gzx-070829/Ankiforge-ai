from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

from ..limits import DEFAULT_DOCUMENT_LIMITS, DocumentLimits
from ..models import DocumentIR


@dataclass(frozen=True)
class BackendCapability:
    backend_id: str
    display_name: str
    supported_extensions: Tuple[str, ...]
    supports_structure: bool
    supports_tables: bool
    supports_pdf: bool
    enabled_by_default: bool = False
    local_only: bool = True
    ocr_enabled: bool = False
    remote_enabled: bool = False
    plugins_enabled: bool = False
    downloads_enabled: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.backend_id, str) or not self.backend_id:
            raise ValueError("backend_id must be a non-empty string")
        if not isinstance(self.display_name, str) or not self.display_name:
            raise ValueError("display_name must be a non-empty string")
        extensions = tuple(self.supported_extensions)
        if not extensions or not all(
            isinstance(extension, str)
            and extension.startswith(".")
            and extension == extension.casefold()
            for extension in extensions
        ):
            raise ValueError("supported_extensions must be lowercase extensions")
        object.__setattr__(self, "supported_extensions", extensions)
        if (
            self.enabled_by_default
            or not self.local_only
            or self.ocr_enabled
            or self.remote_enabled
            or self.plugins_enabled
            or self.downloads_enabled
        ):
            raise ValueError("optional document backends must be local and default-off")

    def to_safe_dict(self) -> Dict[str, object]:
        return {
            "backend_id": self.backend_id,
            "display_name": self.display_name,
            "supported_extensions": list(self.supported_extensions),
            "supports_structure": self.supports_structure,
            "supports_tables": self.supports_tables,
            "supports_pdf": self.supports_pdf,
            "enabled_by_default": self.enabled_by_default,
            "local_only": self.local_only,
            "ocr_enabled": self.ocr_enabled,
            "remote_enabled": self.remote_enabled,
            "plugins_enabled": self.plugins_enabled,
            "downloads_enabled": self.downloads_enabled,
        }


@dataclass(frozen=True, repr=False)
class BackendProbe:
    backend_id: str
    available: bool
    version: Optional[str] = None
    reason_code: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.backend_id, str) or not self.backend_id:
            raise ValueError("backend_id must be a non-empty string")
        if self.available and self.reason_code is not None:
            raise ValueError("an available backend cannot have an unavailable reason")
        if not self.available and not self.reason_code:
            raise ValueError("an unavailable backend requires a reason code")
        for name in ("version", "reason_code"):
            value = getattr(self, name)
            if value is not None and (
                not isinstance(value, str)
                or not value
                or len(value) > 128
                or any(character in value for character in "\r\n/\\")
            ):
                raise ValueError(f"{name} must be a bounded safe value")

    def __repr__(self) -> str:
        return (
            f"BackendProbe(backend_id={self.backend_id!r}, "
            f"available={self.available!r}, has_version={self.version is not None!r}, "
            f"reason_code={self.reason_code!r})"
        )


@dataclass(frozen=True)
class BackendVersionInfo:
    backend_id: str
    available: bool
    version: Optional[str] = None


@dataclass(frozen=True)
class BackendHealth:
    backend_id: str
    healthy: bool
    reason_code: Optional[str] = None


@dataclass(frozen=True, repr=False)
class BackendCommand:
    executable: Union[str, Path]
    arguments: Tuple[str, ...]
    source_path: Union[str, Path]
    output_format: str = "text"
    output_artifact_suffix: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "arguments", tuple(self.arguments))

    def __repr__(self) -> str:
        return (
            f"BackendCommand(argument_count={len(self.arguments)}, "
            f"output_format={self.output_format!r}, "
            f"uses_output_artifact={self.output_artifact_suffix is not None!r})"
        )


@dataclass(frozen=True, repr=False)
class BackendResult:
    returncode: int
    stdout: str
    stderr_summary: str = ""

    def __repr__(self) -> str:
        return (
            f"BackendResult(returncode={self.returncode}, "
            f"stdout_chars={len(self.stdout)}, "
            f"stderr_chars={len(self.stderr_summary)})"
        )


class DocumentBackend(ABC):
    backend_id: str

    @abstractmethod
    def capabilities(self) -> BackendCapability:
        raise NotImplementedError

    @abstractmethod
    def probe(self) -> BackendProbe:
        raise NotImplementedError

    @abstractmethod
    def convert_local_file(
        self,
        path: Union[str, Path],
        limits: DocumentLimits = DEFAULT_DOCUMENT_LIMITS,
    ) -> DocumentIR:
        raise NotImplementedError

    def version_info(self) -> BackendVersionInfo:
        probe = self.probe()
        return BackendVersionInfo(
            backend_id=probe.backend_id,
            available=probe.available,
            version=probe.version,
        )

    def health_check(self) -> BackendHealth:
        probe = self.probe()
        return BackendHealth(
            backend_id=probe.backend_id,
            healthy=probe.available,
            reason_code=probe.reason_code,
        )
