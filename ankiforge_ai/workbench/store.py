"""Tiny in-memory holder for immutable workbench state snapshots."""

from __future__ import annotations

from typing import Optional

from .legacy_bridge import project_legacy_session
from .models import WorkbenchSessionState
from .transitions import close_session


def _target_fingerprint(session: object) -> tuple[object, object]:
    return (
        getattr(session, "selected_anki_deck_id", None),
        getattr(session, "selected_anki_note_type_id", None),
    )


def _mapping_fingerprint(session: object) -> tuple[object, object, object]:
    return (
        getattr(session, "mapped_front_field", ""),
        getattr(session, "mapped_back_field", ""),
        getattr(session, "mapped_source_field", None),
    )


def _fingerprint_is_non_empty(fingerprint: tuple[object, ...]) -> bool:
    return any(value not in {None, ""} for value in fingerprint)


class WorkbenchSessionStore:
    """Own the latest immutable projection for one disposable UI session."""

    def __init__(
        self,
        state: WorkbenchSessionState,
        *,
        target_fingerprint: tuple[object, object],
        mapping_fingerprint: tuple[object, object, object],
    ):
        if not isinstance(state, WorkbenchSessionState):
            raise TypeError("state must be a WorkbenchSessionState")
        self._state = state
        self._target_fingerprint = target_fingerprint
        self._mapping_fingerprint = mapping_fingerprint
        self._target_revision = state.write.target_revision
        self._mapping_revision = state.write.mapping_revision
        self._closed = state.closed

    @classmethod
    def from_legacy(cls, session: object) -> "WorkbenchSessionStore":
        target = _target_fingerprint(session)
        mapping = _mapping_fingerprint(session)
        target_revision = 1 if _fingerprint_is_non_empty(target) else 0
        mapping_revision = 1 if _fingerprint_is_non_empty(mapping) else 0
        state = project_legacy_session(
            session,
            target_revision=target_revision,
            mapping_revision=mapping_revision,
        )
        return cls(
            state,
            target_fingerprint=target,
            mapping_fingerprint=mapping,
        )

    @property
    def state(self) -> WorkbenchSessionState:
        return self._state

    def synchronize(
        self,
        session: object,
        active_request_id: Optional[int] = None,
    ) -> WorkbenchSessionState:
        if self._closed:
            raise RuntimeError("closed workbench stores cannot be reused")
        target = _target_fingerprint(session)
        mapping = _mapping_fingerprint(session)
        if target != self._target_fingerprint:
            self._target_revision += 1
            self._target_fingerprint = target
        if mapping != self._mapping_fingerprint:
            self._mapping_revision += 1
            self._mapping_fingerprint = mapping
        self._state = project_legacy_session(
            session,
            active_request_id,
            target_revision=self._target_revision,
            mapping_revision=self._mapping_revision,
        )
        if self._state.closed:
            self._closed = True
        return self._state

    def close(self) -> WorkbenchSessionState:
        if not self._state.closed:
            self._state = close_session(self._state)
        self._closed = True
        self._target_fingerprint = (None, None)
        self._mapping_fingerprint = (None, None, None)
        return self._state

    def __repr__(self) -> str:
        return f"WorkbenchSessionStore(state={self._state!r})"
