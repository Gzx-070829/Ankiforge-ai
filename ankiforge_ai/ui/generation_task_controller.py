"""Pure-Python lifecycle controller for explicit background card generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from ..pipeline.generation_settings import GenerationSettings
from .beginner_ai_card_drafts import (
    BeginnerAICardDraftGenerator,
    BeginnerAIProviderRuntimeSettings,
)


@dataclass(frozen=True)
class GenerationRequestSnapshot:
    request_id: int
    material_text: str = field(repr=False)
    runtime_settings: BeginnerAIProviderRuntimeSettings = field(repr=False)
    generation_settings: GenerationSettings
    endpoint_confirmation_key: Optional[str] = field(default=None, repr=False)


@dataclass(frozen=True)
class GenerationTaskCompletion:
    request_id: int
    result: object = field(default=None, repr=False)
    error_code: Optional[str] = None


class GenerationTaskController:
    """Submit immutable snapshots and silently reject stale Future callbacks."""

    def __init__(self, taskman, generator_factory=None):
        run_in_background = getattr(taskman, "run_in_background", None)
        if not callable(run_in_background):
            raise TypeError("taskman must provide run_in_background")
        self._taskman = taskman
        self._generator_factory = (
            BeginnerAICardDraftGenerator
            if generator_factory is None
            else generator_factory
        )
        if not callable(self._generator_factory):
            raise TypeError("generator_factory must be callable")
        self._next_request_id = 0
        self._current_request_id = None
        self._running = False
        self._alive = True

    @property
    def running(self) -> bool:
        return self._running

    @property
    def alive(self) -> bool:
        return self._alive

    @property
    def current_request_id(self):
        return self._current_request_id

    def submit(
        self,
        *,
        material_text: str,
        runtime_settings: BeginnerAIProviderRuntimeSettings,
        generation_settings: GenerationSettings,
        on_complete: Callable[[GenerationTaskCompletion], None],
        endpoint_confirmation_key: Optional[str] = None,
    ):
        if not self._alive or self._running:
            return None
        if not isinstance(runtime_settings, BeginnerAIProviderRuntimeSettings):
            raise TypeError("runtime_settings must be provider runtime settings")
        if not isinstance(generation_settings, GenerationSettings):
            raise TypeError("generation_settings must be GenerationSettings")
        if not isinstance(material_text, str):
            raise TypeError("material_text must be a string")
        if not callable(on_complete):
            raise TypeError("on_complete must be callable")

        self._next_request_id += 1
        request_id = self._next_request_id
        snapshot = GenerationRequestSnapshot(
            request_id=request_id,
            material_text=material_text,
            runtime_settings=runtime_settings,
            generation_settings=generation_settings,
            endpoint_confirmation_key=endpoint_confirmation_key,
        )
        self._current_request_id = request_id
        self._running = True
        generator_factory = self._generator_factory

        def background_task():
            generator = generator_factory()
            return generator.generate(
                settings=snapshot.runtime_settings,
                material_text=snapshot.material_text,
                generation_settings=snapshot.generation_settings,
                endpoint_confirmation_key=snapshot.endpoint_confirmation_key,
            )

        def on_done(future):
            try:
                result = future.result()
                completion = GenerationTaskCompletion(
                    request_id=request_id,
                    result=result,
                )
            except Exception:
                completion = GenerationTaskCompletion(
                    request_id=request_id,
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
                GenerationTaskCompletion(
                    request_id=request_id,
                    error_code="background_task_submit_failed",
                ),
                on_complete,
            )
        return request_id

    def invalidate(self) -> None:
        self._current_request_id = None
        self._running = False

    def close(self) -> None:
        self._alive = False
        self.invalidate()

    def _finish_if_current(self, completion, on_complete) -> None:
        if (
            not self._alive
            or completion.request_id != self._current_request_id
        ):
            return
        self._current_request_id = None
        self._running = False
        try:
            on_complete(completion)
        except RuntimeError:
            # A deleted Qt wrapper is an expected late-lifecycle condition.
            return
