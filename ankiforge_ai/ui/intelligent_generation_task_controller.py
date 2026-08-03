"""Taskman adapter for the pure bounded intelligence lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
import re
from typing import Callable, Optional

from ..intelligence.generation_run import GenerationRun, supersede_run
from ..intelligence.recovery import create_failed_chunk_retry
from ..workbench.generation_lifecycle import (
    GenerationLifecycleResult,
    IntelligentGenerationProgress,
    apply_coverage_supplement,
    execute_failed_retry_lifecycle,
    execute_generation_lifecycle,
    failed_generation_retry_is_available,
    failed_generation_run,
    generation_callback_is_grouped,
)


_SAFE_REASON = re.compile(r"^[a-z][a-z0-9_]{0,119}$")

# Temporary compatibility aliases for existing callers and tests.
_WorkerResult = GenerationLifecycleResult
_execute_lifecycle = execute_generation_lifecycle
_execute_failed_retry_lifecycle = execute_failed_retry_lifecycle
_apply_coverage_supplement = apply_coverage_supplement
_is_grouped_generator = generation_callback_is_grouped
_failed_run = failed_generation_run


@dataclass(frozen=True, repr=False)
class IntelligentGenerationRequestSnapshot:
    request_id: int
    run: GenerationRun

    def __post_init__(self) -> None:
        if not isinstance(self.run, GenerationRun):
            raise TypeError("run must be a GenerationRun")
        if self.request_id != self.run.request_id:
            raise ValueError("request_id must match the run")

    def __repr__(self) -> str:
        return (
            "IntelligentGenerationRequestSnapshot("
            f"request_id={self.request_id}, run_id={self.run.run_id!r}, "
            f"chunks={len(self.run.chunks)})"
        )


@dataclass(frozen=True, repr=False)
class IntelligentGenerationTaskCompletion:
    request_id: int
    run: GenerationRun
    error_code: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.run, GenerationRun):
            raise TypeError("run must be a GenerationRun")
        if (
            isinstance(self.request_id, bool)
            or not isinstance(self.request_id, int)
            or self.request_id < 1
            or self.request_id != self.run.request_id
        ):
            raise ValueError("request_id must match the run identity")
        if self.error_code is not None and (
            not isinstance(self.error_code, str)
            or not _SAFE_REASON.fullmatch(self.error_code)
        ):
            raise ValueError("error_code must be a safe bounded code")

    @property
    def result(self) -> GenerationRun:
        return self.run

    def __repr__(self) -> str:
        return (
            "IntelligentGenerationTaskCompletion("
            f"request_id={self.request_id}, run_id={self.run.run_id!r}, "
            f"stage={self.run.stage.value!r}, status={self.run.status.value!r}, "
            f"cards={len(self.run.cards)}, calls={self.run.call_budget.call_count}, "
            f"error_code={self.error_code!r})"
        )


class IntelligentGenerationTaskController:
    """Execute only injected callbacks and silently discard stale UI delivery."""

    def __init__(
        self,
        taskman,
        *,
        planner_callback=None,
        generator_callback=None,
        critic_callback=None,
        repair_callback=None,
        supplement_callback=None,
    ):
        run_in_background = getattr(taskman, "run_in_background", None)
        if not callable(run_in_background):
            raise TypeError("taskman must provide run_in_background")
        for callback, name in (
            (planner_callback, "planner_callback"),
            (generator_callback, "generator_callback"),
            (critic_callback, "critic_callback"),
            (repair_callback, "repair_callback"),
            (supplement_callback, "supplement_callback"),
        ):
            if (
                callback is not None
                and not callable(callback)
                and not (
                    name == "generator_callback"
                    and generation_callback_is_grouped(callback)
                )
            ):
                raise TypeError(f"{name} must be callable")
        self._taskman = taskman
        self._default_planner = planner_callback
        self._default_generator = generator_callback
        self._default_critic = critic_callback
        self._default_repair = repair_callback
        self._default_supplement = supplement_callback
        self._lock = Lock()
        self._current_request_id = None
        self._highest_request_id = 0
        self._running = False
        self._alive = True

    @property
    def running(self) -> bool:
        with self._lock:
            return self._running

    @property
    def alive(self) -> bool:
        with self._lock:
            return self._alive

    @property
    def current_request_id(self):
        with self._lock:
            return self._current_request_id

    def submit(
        self,
        *,
        run_snapshot: GenerationRun,
        generator_callback=None,
        on_progress=None,
        on_complete: Callable[[IntelligentGenerationTaskCompletion], None],
        planner_callback=None,
        critic_callback=None,
        repair_callback=None,
        supplement_callback=None,
    ):
        if not isinstance(run_snapshot, GenerationRun):
            raise TypeError("run_snapshot must be a GenerationRun")
        generator = (
            self._default_generator
            if generator_callback is None
            else generator_callback
        )
        planner = (
            self._default_planner
            if planner_callback is None
            else planner_callback
        )
        critic = (
            self._default_critic
            if critic_callback is None
            else critic_callback
        )
        repair = (
            self._default_repair
            if repair_callback is None
            else repair_callback
        )
        supplement = (
            self._default_supplement
            if supplement_callback is None
            else supplement_callback
        )
        if not callable(generator) and not generation_callback_is_grouped(generator):
            raise TypeError("generator_callback must be callable")
        for callback, name in (
            (planner, "planner_callback"),
            (critic, "critic_callback"),
            (repair, "repair_callback"),
            (supplement, "supplement_callback"),
        ):
            if callback is not None and not callable(callback):
                raise TypeError(f"{name} must be callable")
        if not callable(on_complete):
            raise TypeError("on_complete must be callable")
        if on_progress is not None and not callable(on_progress):
            raise TypeError("on_progress must be callable or None")
        snapshot = IntelligentGenerationRequestSnapshot(
            request_id=run_snapshot.request_id,
            run=run_snapshot,
        )
        with self._lock:
            if not self._alive:
                return None
            if snapshot.request_id <= self._highest_request_id:
                raise ValueError("request_id must increase for each submission")
            self._highest_request_id = snapshot.request_id
            self._current_request_id = snapshot.request_id
            self._running = True

        def background_task():
            if not self._is_current(snapshot.request_id):
                return _WorkerResult(
                    supersede_run(snapshot.run),
                    "request_superseded",
                )
            def emit_progress(run, completed_groups=0, total_groups=0):
                if on_progress is None:
                    return
                self._schedule_progress(
                    IntelligentGenerationProgress(
                        request_id=snapshot.request_id,
                        run=run,
                        completed_groups=completed_groups,
                        total_groups=total_groups,
                    ),
                    on_progress,
                )

            return execute_generation_lifecycle(
                snapshot.run,
                planner_callback=planner,
                generator_callback=generator,
                critic_callback=critic,
                repair_callback=repair,
                supplement_callback=supplement,
                progress_callback=emit_progress,
                continue_if_current=lambda: self._is_current(
                    snapshot.request_id
                ),
            )

        def on_done(future):
            try:
                worker_result = future.result()
                completion = IntelligentGenerationTaskCompletion(
                    request_id=snapshot.request_id,
                    run=worker_result.run,
                    error_code=worker_result.error_code,
                )
            except Exception:
                completion = IntelligentGenerationTaskCompletion(
                    request_id=snapshot.request_id,
                    run=failed_generation_run(snapshot.run, "background_task_failed"),
                    error_code="background_task_failed",
                )
            self._finish_if_current(completion, on_complete)

        try:
            self._taskman.run_in_background(
                background_task,
                on_done,
                uses_collection=False,
            )
        except Exception:
            self._finish_if_current(
                IntelligentGenerationTaskCompletion(
                    request_id=snapshot.request_id,
                    run=failed_generation_run(
                        snapshot.run,
                        "background_task_submit_failed",
                    ),
                    error_code="background_task_submit_failed",
                ),
                on_complete,
            )
        return snapshot.request_id

    def invalidate(self) -> None:
        with self._lock:
            self._current_request_id = None
            self._running = False

    def retry_failed(
        self,
        *,
        run_snapshot: GenerationRun,
        retry_generator_callback,
        on_progress=None,
        on_complete: Callable[[IntelligentGenerationTaskCompletion], None],
    ):
        if not isinstance(run_snapshot, GenerationRun):
            raise TypeError("run_snapshot must be a GenerationRun")
        if not callable(retry_generator_callback):
            raise TypeError("retry_generator_callback must be callable")
        if not callable(on_complete):
            raise TypeError("on_complete must be callable")
        if on_progress is not None and not callable(on_progress):
            raise TypeError("on_progress must be callable or None")
        with self._lock:
            if not self._alive:
                return None
            if self._running:
                return None
            if run_snapshot.request_id != self._highest_request_id:
                raise ValueError("retry run is stale")
            if not failed_generation_retry_is_available(run_snapshot):
                return None
            retry = create_failed_chunk_retry(
                run_snapshot,
                retry_id=(
                    f"retry-{run_snapshot.request_id}-"
                    f"{run_snapshot.call_budget.call_count}"
                ),
            )
            self._current_request_id = run_snapshot.request_id
            self._running = True

        def background_task():
            def emit_progress(run, completed_groups=0, total_groups=0):
                if on_progress is None:
                    return
                self._schedule_progress(
                    IntelligentGenerationProgress(
                        request_id=run_snapshot.request_id,
                        run=run,
                        completed_groups=completed_groups,
                        total_groups=total_groups,
                    ),
                    on_progress,
                )

            return execute_failed_retry_lifecycle(
                run_snapshot,
                retry,
                retry_generator_callback=retry_generator_callback,
                progress_callback=emit_progress,
                continue_if_current=lambda: self._is_current(
                    run_snapshot.request_id
                ),
            )

        def on_done(future):
            try:
                worker_result = future.result()
                completion = IntelligentGenerationTaskCompletion(
                    request_id=run_snapshot.request_id,
                    run=worker_result.run,
                    error_code=worker_result.error_code,
                )
            except Exception:
                completion = IntelligentGenerationTaskCompletion(
                    request_id=run_snapshot.request_id,
                    run=failed_generation_run(
                        run_snapshot,
                        "background_task_failed",
                    ),
                    error_code="background_task_failed",
                )
            self._finish_if_current(completion, on_complete)

        try:
            self._taskman.run_in_background(
                background_task,
                on_done,
                uses_collection=False,
            )
        except Exception:
            self._finish_if_current(
                IntelligentGenerationTaskCompletion(
                    request_id=run_snapshot.request_id,
                    run=failed_generation_run(
                        run_snapshot,
                        "background_task_submit_failed",
                    ),
                    error_code="background_task_submit_failed",
                ),
                on_complete,
            )
        return run_snapshot.request_id

    def close(self) -> None:
        with self._lock:
            self._alive = False
            self._current_request_id = None
            self._running = False

    def _is_current(self, request_id: int) -> bool:
        with self._lock:
            return (
                self._alive
                and self._running
                and self._current_request_id == request_id
            )

    def _finish_if_current(self, completion, on_complete) -> None:
        with self._lock:
            if (
                not self._alive
                or completion.request_id != self._current_request_id
            ):
                return
            self._current_request_id = None
            self._running = False
        try:
            on_complete(completion)
        except Exception:
            # UI wrappers may have been deleted or adapters may fail. The
            # controller owns cleanup; callback exceptions never escape.
            return

    def _schedule_progress(self, progress, on_progress) -> None:
        run_on_main = getattr(self._taskman, "run_on_main", None)
        if not callable(run_on_main):
            return

        def deliver():
            if not self._is_current(progress.request_id):
                return
            try:
                on_progress(progress)
            except Exception:
                return

        try:
            run_on_main(deliver)
        except Exception:
            return
