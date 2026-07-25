from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple


class SupportLevel(str, Enum):
    NATIVE_STRUCTURED = "native_structured"
    NATIVE_TEXT = "native_text"
    OPTIONAL_ADVANCED = "optional_advanced"
    FALLBACK_ONLY = "fallback_only"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class ImporterCapability:
    importer_id: str
    display_name_en: str
    display_name_zh: str
    support_level: SupportLevel
    supported_extensions: Tuple[str, ...]
    supports_structure: bool
    supports_tables: bool
    supports_images: bool
    supports_formulas: bool
    external_dependencies: Tuple[str, ...] = ()
    unavailable_reason_key: Optional[str] = None
    security_notes: Tuple[str, ...] = ()
    fallback_importer_ids: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.importer_id, str) or not self.importer_id:
            raise ValueError("importer_id must be a non-empty string")
        for name in ("display_name_en", "display_name_zh"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f"{name} must be a non-empty string")
        try:
            level = SupportLevel(self.support_level)
        except (TypeError, ValueError) as exc:
            raise ValueError("unknown support level") from exc
        object.__setattr__(self, "support_level", level)
        for name in (
            "supported_extensions",
            "external_dependencies",
            "security_notes",
            "fallback_importer_ids",
        ):
            values = tuple(getattr(self, name))
            if not all(isinstance(value, str) and value for value in values):
                raise ValueError(f"{name} must contain non-empty strings")
            object.__setattr__(self, name, values)
        for extension in self.supported_extensions:
            if not extension.startswith(".") or extension != extension.lower():
                raise ValueError("supported extensions must be lowercase")

    def to_safe_dict(self) -> Dict[str, object]:
        return {
            "importer_id": self.importer_id,
            "display_name_en": self.display_name_en,
            "display_name_zh": self.display_name_zh,
            "support_level": self.support_level.value,
            "supported_extensions": list(self.supported_extensions),
            "supports_structure": self.supports_structure,
            "supports_tables": self.supports_tables,
            "supports_images": self.supports_images,
            "supports_formulas": self.supports_formulas,
            "external_dependencies": list(self.external_dependencies),
            "unavailable_reason_key": self.unavailable_reason_key,
            "security_notes": list(self.security_notes),
            "fallback_importer_ids": list(self.fallback_importer_ids),
        }
