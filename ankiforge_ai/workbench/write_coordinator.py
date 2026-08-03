"""Dependency-injected orchestration for the explicit Anki write workflow."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, repr=False)
class PreparedWrite:
    final_preview: object = field(repr=False)
    preparation: object = field(repr=False)

    def __repr__(self) -> str:
        return "PreparedWrite(final_preview=True, preparation=True)"


class WorkbenchWriteCoordinator:
    """Coordinate existing boundaries without owning a collection or thread."""

    def __init__(
        self,
        *,
        target_adapter,
        duplicate_adapter,
        writer,
        final_preview_builder,
        write_preparer,
        confirmed_executor,
    ):
        for adapter, method_names, label in (
            (
                target_adapter,
                ("read_targets", "read_fields"),
                "target_adapter",
            ),
            (duplicate_adapter, ("check",), "duplicate_adapter"),
        ):
            if any(
                not callable(getattr(adapter, name, None))
                for name in method_names
            ):
                raise TypeError(
                    f"{label} does not satisfy its required interface"
                )
        for callback, label in (
            (final_preview_builder, "final_preview_builder"),
            (write_preparer, "write_preparer"),
            (confirmed_executor, "confirmed_executor"),
        ):
            if not callable(callback):
                raise TypeError(f"{label} must be callable")
        self.target_adapter = target_adapter
        self.duplicate_adapter = duplicate_adapter
        self.writer = writer
        self._final_preview_builder = final_preview_builder
        self._write_preparer = write_preparer
        self._confirmed_executor = confirmed_executor

    def read_targets(self):
        return self.target_adapter.read_targets()

    def read_fields(self, note_type_id: int):
        return self.target_adapter.read_fields(note_type_id)

    def check_duplicates(self, candidates, mapping):
        return self.duplicate_adapter.check(candidates, mapping)

    def prepare(self, session, mapping, duplicate_preview) -> PreparedWrite:
        final_preview = self._final_preview_builder(
            session,
            mapping,
            duplicate_preview,
        )
        preparation = self._write_preparer(
            session,
            final_preview,
            mapping,
            duplicate_preview,
        )
        return PreparedWrite(final_preview, preparation)

    def execute_if_confirmed(self, confirmed: bool, command):
        return self._confirmed_executor(confirmed, self.writer, command)

    def __repr__(self) -> str:
        return (
            "WorkbenchWriteCoordinator("
            "target_adapter=True, duplicate_adapter=True, writer=True)"
        )


__all__ = ["PreparedWrite", "WorkbenchWriteCoordinator"]
