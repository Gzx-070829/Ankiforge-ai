from __future__ import annotations

import posixpath
import re
import stat
import unicodedata
import zipfile
from pathlib import Path
from typing import Optional, Union
from urllib.parse import unquote, urlsplit

from .errors import DocumentImportError
from .limits import DEFAULT_DOCUMENT_LIMITS, DocumentLimits


def _error(code: str) -> DocumentImportError:
    return DocumentImportError(
        code=code,
        message_key=f"document.error.{code}",
        action_key="document.action.choose_another_file",
    )


def _normalized_member_name(value: str) -> str:
    decoded = unquote(value).replace("\\", "/")
    if (
        not decoded
        or decoded.startswith("/")
        or re.match(r"^[A-Za-z]:/", decoded)
        or any(part == ".." for part in decoded.split("/"))
    ):
        raise _error("unsafe_archive_member")
    normalized = posixpath.normpath(decoded)
    if normalized in {"", ".", ".."} or normalized.startswith("../"):
        raise _error("unsafe_archive_member")
    return normalized


def _canonical(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


class ValidatedArchive:
    def __init__(
        self,
        path: Union[str, Path],
        limits: DocumentLimits = DEFAULT_DOCUMENT_LIMITS,
    ) -> None:
        self.path = Path(path)
        self.limits = limits
        self._archive: Optional[zipfile.ZipFile] = None
        self._members = {}

    def __enter__(self) -> "ValidatedArchive":
        try:
            size = self.path.stat().st_size
            if not self.path.is_file():
                raise OSError
            if size > self.limits.max_source_file_bytes:
                raise _error("file_too_large")
            archive = zipfile.ZipFile(self.path, "r")
            self._archive = archive
            self._validate(archive)
            return self
        except DocumentImportError:
            self.close()
            raise
        except (OSError, zipfile.BadZipFile, RuntimeError, ValueError):
            self.close()
            raise _error("invalid_archive") from None

    def __exit__(self, *_args) -> None:
        self.close()

    def close(self) -> None:
        if self._archive is not None:
            self._archive.close()
            self._archive = None

    def _validate(self, archive: zipfile.ZipFile) -> None:
        infos = archive.infolist()
        if len(infos) > self.limits.max_archive_members:
            raise _error("archive_too_many_members")
        total = 0
        members = {}
        for info in infos:
            name = _normalized_member_name(info.filename)
            if stat.S_ISLNK(info.external_attr >> 16):
                raise _error("unsafe_archive_member")
            if info.flag_bits & 0x1:
                raise _error("encrypted_archive_member")
            if name.casefold().endswith("vbaproject.bin"):
                raise _error("office_macros_not_allowed")
            if info.file_size > self.limits.max_member_bytes:
                raise _error("archive_member_too_large")
            total += info.file_size
            if total > self.limits.max_archive_uncompressed_bytes:
                raise _error("archive_too_large")
            if info.file_size and (
                info.compress_size == 0
                or info.file_size / info.compress_size
                > self.limits.max_archive_compression_ratio
            ):
                raise _error("suspicious_archive_compression")
            key = _canonical(name)
            if key in members:
                raise _error("duplicate_archive_member")
            members[key] = (name, info)
        self._members = members

    @property
    def names(self):
        return tuple(value[0] for value in self._members.values())

    def contains(self, name: str) -> bool:
        try:
            normalized = _normalized_member_name(name)
        except DocumentImportError:
            return False
        return _canonical(normalized) in self._members

    def member_name(self, name: str) -> Optional[str]:
        normalized = _normalized_member_name(name)
        item = self._members.get(_canonical(normalized))
        return None if item is None else item[0]

    def read(self, name: str) -> bytes:
        if self._archive is None:
            raise RuntimeError("archive is not open")
        normalized = _normalized_member_name(name)
        item = self._members.get(_canonical(normalized))
        if item is None:
            raise _error("invalid_archive")
        actual, info = item
        try:
            with self._archive.open(info, "r") as stream:
                payload = stream.read(self.limits.max_member_bytes + 1)
        except (OSError, RuntimeError, zipfile.BadZipFile):
            raise _error("invalid_archive") from None
        if len(payload) != info.file_size or len(payload) > self.limits.max_member_bytes:
            raise _error("archive_member_too_large")
        if actual != item[0]:
            raise _error("invalid_archive")
        return payload

    def resolve(self, base_member: str, target: str) -> Optional[str]:
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
            return None
        decoded = unquote(parsed.path).replace("\\", "/")
        if decoded.startswith("/") or re.match(r"^[A-Za-z]:/", decoded):
            return None
        try:
            joined = _normalized_member_name(
                posixpath.join(posixpath.dirname(base_member), decoded)
            )
        except DocumentImportError:
            return None
        return self.member_name(joined)


def open_validated_archive(
    path: Union[str, Path],
    limits: DocumentLimits = DEFAULT_DOCUMENT_LIMITS,
) -> ValidatedArchive:
    return ValidatedArchive(path, limits)
