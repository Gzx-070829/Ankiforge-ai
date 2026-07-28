from __future__ import annotations

import importlib.metadata
import importlib.util
import os
import re
from pathlib import Path
from typing import Optional, Union

from .base import BackendProbe


_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def probe_python_module(
    backend_id: str,
    module_name: str,
    *,
    distribution_name: Optional[str] = None,
) -> BackendProbe:
    if not _SAFE_NAME.fullmatch(backend_id) or not _SAFE_NAME.fullmatch(module_name):
        raise ValueError("backend and module names must be safe identifiers")
    try:
        spec = importlib.util.find_spec(module_name)
    except (AttributeError, ImportError, ModuleNotFoundError, ValueError):
        spec = None
    if spec is None:
        return BackendProbe(
            backend_id=backend_id,
            available=False,
            reason_code="not_installed",
        )
    version = None
    try:
        version = importlib.metadata.version(distribution_name or module_name)
    except importlib.metadata.PackageNotFoundError:
        pass
    if version is not None:
        version = _safe_version(version)
    return BackendProbe(
        backend_id=backend_id,
        available=True,
        version=version,
    )


def probe_absolute_executable(
    backend_id: str,
    executable: Optional[Union[str, Path]],
) -> BackendProbe:
    if executable is None:
        return BackendProbe(
            backend_id=backend_id,
            available=False,
            reason_code="not_configured",
        )
    if not isinstance(executable, (str, Path)):
        return BackendProbe(
            backend_id=backend_id,
            available=False,
            reason_code="invalid_executable",
        )
    raw = str(executable)
    if "://" in raw or "\x00" in raw:
        return BackendProbe(
            backend_id=backend_id,
            available=False,
            reason_code="invalid_executable",
        )
    candidate = Path(raw)
    expected_names = {backend_id.casefold()}
    if os.name == "nt":
        expected_names.add(f"{backend_id.casefold()}.exe")
    try:
        if (
            not candidate.is_absolute()
            or not candidate.is_file()
            or candidate.is_symlink()
            or candidate.name.casefold() not in expected_names
            or (os.name != "nt" and not os.access(candidate, os.X_OK))
        ):
            raise OSError
    except OSError:
        return BackendProbe(
            backend_id=backend_id,
            available=False,
            reason_code="invalid_executable",
        )
    return BackendProbe(backend_id=backend_id, available=True)


def _safe_version(value: str) -> Optional[str]:
    candidate = str(value).strip()
    if (
        not candidate
        or len(candidate) > 128
        or any(character in candidate for character in "\r\n/\\")
    ):
        return None
    return candidate
