from pathlib import Path
from typing import Callable, Dict, Optional, Tuple, Union

from .capabilities import ImporterCapability, SupportLevel
from .detection import detect_file_type
from .errors import DocumentImportError
from .importers.base import DocumentImporter
from .limits import DEFAULT_DOCUMENT_LIMITS, DocumentLimits
from .models import DocumentIR


ImporterFactory = Callable[[], DocumentImporter]
_LEVEL_ORDER = {
    SupportLevel.NATIVE_STRUCTURED: 0,
    SupportLevel.NATIVE_TEXT: 1,
    SupportLevel.OPTIONAL_ADVANCED: 2,
    SupportLevel.FALLBACK_ONLY: 3,
    SupportLevel.UNSUPPORTED: 4,
}
_FILE_TYPE_EXTENSIONS = {
    "text": (".txt", ".log"),
    "markdown": (".md", ".markdown"),
    "rst": (".rst",),
    "org": (".org",),
    "latex": (".tex", ".latex"),
    "yaml": (".yaml", ".yml"),
    "csv": (".csv",),
    "tsv": (".tsv",),
    "json": (".json",),
    "jsonl": (".jsonl",),
    "ipynb": (".ipynb",),
    "xml": (".xml",),
    "html": (".html", ".htm", ".xhtml"),
    "srt": (".srt",),
    "vtt": (".vtt",),
    "python": (".py",),
    "javascript": (".js",),
    "typescript": (".ts",),
    "java": (".java",),
    "c": (".c", ".h"),
    "cpp": (".cpp", ".cc", ".hpp"),
    "rust": (".rs",),
    "go": (".go",),
    "sql": (".sql",),
    "shell": (".sh",),
    "powershell": (".ps1",),
    "docx": (".docx",),
    "pptx": (".pptx",),
    "xlsx": (".xlsx",),
    "epub": (".epub",),
    "pdf": (".pdf",),
    "zip": (".zip",),
}
_TEXT_LIKE_FILE_TYPES = frozenset(
    {
        "text",
        "markdown",
        "rst",
        "org",
        "latex",
        "yaml",
        "csv",
        "tsv",
        "jsonl",
        "xml",
        "html",
        "srt",
        "vtt",
        "python",
        "javascript",
        "typescript",
        "java",
        "c",
        "cpp",
        "rust",
        "go",
        "sql",
        "shell",
        "powershell",
    }
)


def _registry_error(code: str, importer_id: str) -> DocumentImportError:
    return DocumentImportError(
        code=code,
        message_key=f"document.error.{code}",
        action_key="document.action.choose_importer",
        safe_details={"importer_id": importer_id},
    )


def _capability_match_priority(
    capability: ImporterCapability,
    file_type: str,
    detected_extension: str,
    *,
    explicit: bool,
) -> Optional[int]:
    expected_extensions = _FILE_TYPE_EXTENSIONS.get(file_type)
    if expected_extensions is None:
        expected_extensions = (
            (detected_extension,) if detected_extension else ()
        )
    supported = set(capability.supported_extensions)
    if supported.intersection(expected_extensions):
        return 1
    allow_original_text_suffix = (
        explicit or capability.support_level is SupportLevel.NATIVE_TEXT
    )
    if (
        allow_original_text_suffix
        and file_type in _TEXT_LIKE_FILE_TYPES
        and detected_extension
        and detected_extension in supported
    ):
        return 0 if file_type == "text" else 2
    return None


def _execute_importer(
    importer: DocumentImporter,
    path: Union[str, Path],
    limits: DocumentLimits,
) -> DocumentIR:
    try:
        return importer.import_document(path, limits)
    except DocumentImportError:
        raise
    except Exception:
        raise _registry_error(
            "importer_execution_failed",
            importer.importer_id,
        ) from None


class DocumentImporterRegistry:
    def __init__(self) -> None:
        self._capabilities: Dict[str, ImporterCapability] = {}
        self._factories: Dict[str, ImporterFactory] = {}
        self._instances: Dict[str, DocumentImporter] = {}

    def register(
        self, capability: ImporterCapability, factory: ImporterFactory
    ) -> None:
        if not isinstance(capability, ImporterCapability):
            raise TypeError("capability must be an ImporterCapability")
        if not callable(factory):
            raise TypeError("factory must be callable")
        if capability.importer_id in self._capabilities:
            raise _registry_error("duplicate_importer", capability.importer_id)
        self._capabilities[capability.importer_id] = capability
        self._factories[capability.importer_id] = factory

    def capabilities(self) -> Tuple[ImporterCapability, ...]:
        return tuple(
            sorted(
                self._capabilities.values(),
                key=lambda item: (_LEVEL_ORDER[item.support_level], item.importer_id),
            )
        )

    def create_importer(self, importer_id: str) -> DocumentImporter:
        if importer_id not in self._factories:
            raise _registry_error("unknown_importer", importer_id)
        if importer_id in self._instances:
            return self._instances[importer_id]
        try:
            importer = self._factories[importer_id]()
            if not isinstance(importer, DocumentImporter):
                raise TypeError("factory returned an invalid importer")
            available = importer.availability()
        except Exception:
            raise _registry_error(
                "optional_importer_unavailable", importer_id
            ) from None
        if available is not True:
            raise _registry_error("optional_importer_unavailable", importer_id)
        if importer.importer_id != importer_id:
            raise _registry_error("invalid_importer", importer_id)
        self._instances[importer_id] = importer
        return importer

    def select_importer(
        self,
        path: Union[str, Path],
        limits: DocumentLimits = DEFAULT_DOCUMENT_LIMITS,
        *,
        importer_id: Optional[str] = None,
    ) -> DocumentImporter:
        detected = detect_file_type(path, limits)
        if importer_id is not None:
            capability = self._capabilities.get(importer_id)
            if capability is None:
                raise _registry_error("unknown_importer", importer_id)
            if capability.support_level is SupportLevel.UNSUPPORTED:
                raise _registry_error("unsupported_type", importer_id)
            if _capability_match_priority(
                capability,
                detected.file_type,
                detected.extension,
                explicit=True,
            ) is None:
                raise _registry_error("importer_does_not_support_type", importer_id)
            return self.create_importer(importer_id)

        native_levels = {
            SupportLevel.NATIVE_STRUCTURED,
            SupportLevel.NATIVE_TEXT,
        }
        candidates = []
        for capability in self.capabilities():
            priority = _capability_match_priority(
                capability,
                detected.file_type,
                detected.extension,
                explicit=False,
            )
            if capability.support_level in native_levels and priority is not None:
                candidates.append((priority, capability))
        candidates.sort(
            key=lambda item: (
                item[0],
                _LEVEL_ORDER[item[1].support_level],
                item[1].importer_id,
            )
        )
        for _priority, capability in candidates:
            try:
                return self.create_importer(capability.importer_id)
            except DocumentImportError as exc:
                if exc.code != "optional_importer_unavailable":
                    raise
        raise DocumentImportError(
            code="unsupported_type",
            message_key="document.error.unsupported_type",
            action_key="document.action.choose_importer",
            safe_details={"file_type": detected.file_type},
        )

    def import_document(
        self,
        path: Union[str, Path],
        limits: DocumentLimits = DEFAULT_DOCUMENT_LIMITS,
        *,
        importer_id: Optional[str] = None,
        fallback_importer_id: Optional[str] = None,
    ) -> DocumentIR:
        importer = self.select_importer(path, limits, importer_id=importer_id)
        primary_id = importer.importer_id
        try:
            return _execute_importer(importer, path, limits)
        except DocumentImportError:
            if fallback_importer_id is None:
                raise
            capability = self._capabilities[primary_id]
            if fallback_importer_id not in capability.fallback_importer_ids:
                raise _registry_error("fallback_not_allowed", fallback_importer_id)
            fallback = self.select_importer(
                path, limits, importer_id=fallback_importer_id
            )
            return _execute_importer(fallback, path, limits)
