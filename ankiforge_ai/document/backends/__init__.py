from .base import (
    BackendCapability,
    BackendCommand,
    BackendHealth,
    BackendProbe,
    BackendResult,
    BackendVersionInfo,
    DocumentBackend,
)
from .companion_protocol import (
    PROTOCOL_VERSION,
    CompanionProgress,
    CompanionRequest,
    CompanionResponse,
)
from .command_runner import SafeCommandRunner
__all__ = [
    "BackendCapability",
    "BackendCommand",
    "BackendHealth",
    "BackendProbe",
    "BackendResult",
    "BackendVersionInfo",
    "CompanionProgress",
    "CompanionRequest",
    "CompanionResponse",
    "DoclingBackend",
    "DocumentBackend",
    "MarkItDownBackend",
    "PROTOCOL_VERSION",
    "PandocBackend",
    "SafeCommandRunner",
]


def __getattr__(name):
    """Load optional adapter modules only after an explicit attribute request."""

    if name == "DoclingBackend":
        from .docling_adapter import DoclingBackend

        return DoclingBackend
    if name == "MarkItDownBackend":
        from .markitdown_adapter import MarkItDownBackend

        return MarkItDownBackend
    if name == "PandocBackend":
        from .pandoc_adapter import PandocBackend

        return PandocBackend
    raise AttributeError(name)
