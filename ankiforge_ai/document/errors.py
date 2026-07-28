import re
from types import MappingProxyType
from typing import Mapping, Optional

from .models import (
    SafeScalar,
    _freeze_metadata,
    _is_absolute_or_traversal,
    _validate_identifier,
)


_UNSAFE_DETAIL_KEY = re.compile(
    r"(?:path|body|traceback|environment|raw.?output|api.?key|password|secret|token)",
    re.IGNORECASE,
)


class DocumentImportError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message_key: str,
        action_key: str,
        severity: str = "error",
        safe_details: Optional[Mapping[str, SafeScalar]] = None,
    ) -> None:
        _validate_identifier(code, "error code")
        _validate_identifier(message_key, "message_key")
        _validate_identifier(action_key, "action_key")
        if severity not in {"info", "warning", "error"}:
            raise ValueError("error severity must be info, warning, or error")
        details = dict(_freeze_metadata(safe_details))
        for key, value in details.items():
            if _UNSAFE_DETAIL_KEY.search(key):
                raise ValueError("unsafe error detail key")
            if isinstance(value, str) and _is_absolute_or_traversal(value):
                raise ValueError("unsafe error detail value")
        self.code = code
        self.message_key = message_key
        self.action_key = action_key
        self.severity = severity
        self.safe_details = MappingProxyType(details)
        super().__init__(message_key)

    def __repr__(self) -> str:
        return (
            f"DocumentImportError(code={self.code!r}, "
            f"message_key={self.message_key!r}, severity={self.severity!r}, "
            f"detail_count={len(self.safe_details)})"
        )

    def __str__(self) -> str:
        return self.message_key
