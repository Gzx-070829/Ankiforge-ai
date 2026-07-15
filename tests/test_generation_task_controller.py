from concurrent.futures import Future
from dataclasses import FrozenInstanceError
import unittest

from ankiforge_ai.pipeline.generation_settings import GenerationSettings
from ankiforge_ai.ui.beginner_ai_card_drafts import (
    BeginnerAIProviderRuntimeSettings,
)
from ankiforge_ai.ui.generation_task_controller import (
    GenerationRequestSnapshot,
    GenerationTaskController,
)


class DeferredTaskman:
    def __init__(self):
        self.pending = []

    def run_in_background(self, task, on_done, *, uses_collection=True):
        future = Future()
        self.pending.append((task, on_done, future, uses_collection))
        return future

    def complete(self, index=0):
        task, on_done, future, _uses_collection = self.pending[index]
        try:
            future.set_result(task())
        except Exception as error:
            future.set_exception(error)
        on_done(future)


class RecordingGenerator:
    def __init__(self, calls, result="generated", error=None):
        self.calls = calls
        self.result = result
        self.error = error

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.result


class MaterialEchoGenerator:
    def generate(self, **kwargs):
        return kwargs["material_text"]


class GenerationTaskControllerTests(unittest.TestCase):
    def settings(self, secret="fake-session-secret"):
        return BeginnerAIProviderRuntimeSettings(
            provider_name="OpenAI-compatible",
            base_url="https://provider.example/v1",
            model="model-a",
            api_key=secret,
        )

    def test_submit_is_deferred_and_uses_no_collection(self):
        taskman = DeferredTaskman()
        calls = []
        completions = []
        controller = GenerationTaskController(
            taskman,
            generator_factory=lambda: RecordingGenerator(calls),
        )

        request_id = controller.submit(
            material_text="original material",
            runtime_settings=self.settings(),
            generation_settings=GenerationSettings(),
            endpoint_confirmation_key="session-confirmation",
            on_complete=completions.append,
        )

        self.assertEqual(request_id, 1)
        self.assertTrue(controller.running)
        self.assertEqual(calls, [])
        self.assertEqual(len(taskman.pending), 1)
        self.assertFalse(taskman.pending[0][3])
        taskman.complete()
        self.assertEqual(len(calls), 1)
        self.assertEqual(completions[0].result, "generated")
        self.assertFalse(controller.running)

    def test_duplicate_submit_is_rejected_while_current_request_runs(self):
        taskman = DeferredTaskman()
        controller = GenerationTaskController(taskman)

        first = controller.submit(
            material_text="material",
            runtime_settings=self.settings(),
            generation_settings=GenerationSettings(),
            on_complete=lambda _completion: None,
        )
        second = controller.submit(
            material_text="material",
            runtime_settings=self.settings(),
            generation_settings=GenerationSettings(),
            on_complete=lambda _completion: None,
        )

        self.assertEqual(first, 1)
        self.assertIsNone(second)
        self.assertEqual(len(taskman.pending), 1)

    def test_stale_success_and_failure_are_silently_discarded(self):
        taskman = DeferredTaskman()
        calls = []
        completions = []
        generators = iter(
            (
                RecordingGenerator(calls, error=RuntimeError("old fake secret")),
                RecordingGenerator(calls, result="new result"),
            )
        )
        controller = GenerationTaskController(
            taskman,
            generator_factory=lambda: next(generators),
        )
        controller.submit(
            material_text="old",
            runtime_settings=self.settings(),
            generation_settings=GenerationSettings(card_mode="concept"),
            on_complete=completions.append,
        )
        controller.invalidate()
        controller.submit(
            material_text="new",
            runtime_settings=self.settings(),
            generation_settings=GenerationSettings(card_mode="exam"),
            on_complete=completions.append,
        )

        taskman.complete(0)
        self.assertEqual(completions, [])
        self.assertTrue(controller.running)
        taskman.complete(1)
        self.assertEqual([item.result for item in completions], ["new result"])

    def test_new_result_wins_when_requests_finish_in_reverse_order(self):
        taskman = DeferredTaskman()
        completions = []
        controller = GenerationTaskController(
            taskman,
            generator_factory=MaterialEchoGenerator,
        )
        controller.submit(
            material_text="old material",
            runtime_settings=self.settings(),
            generation_settings=GenerationSettings(),
            on_complete=completions.append,
        )
        controller.invalidate()
        controller.submit(
            material_text="new material",
            runtime_settings=self.settings(),
            generation_settings=GenerationSettings(),
            on_complete=completions.append,
        )

        taskman.complete(1)
        taskman.complete(0)

        self.assertEqual([item.result for item in completions], ["new material"])
        self.assertFalse(controller.running)

    def test_close_makes_late_completion_a_noop(self):
        taskman = DeferredTaskman()
        completions = []
        controller = GenerationTaskController(taskman)
        controller.submit(
            material_text="material",
            runtime_settings=self.settings(),
            generation_settings=GenerationSettings(),
            on_complete=completions.append,
        )

        controller.close()
        taskman.complete()

        self.assertFalse(controller.alive)
        self.assertFalse(controller.running)
        self.assertEqual(completions, [])

    def test_snapshot_is_frozen_and_background_uses_captured_values(self):
        taskman = DeferredTaskman()
        calls = []
        controller = GenerationTaskController(
            taskman,
            generator_factory=lambda: RecordingGenerator(calls),
        )
        original_settings = self.settings()
        original_generation = GenerationSettings(card_mode="concept")
        controller.submit(
            material_text="original",
            runtime_settings=original_settings,
            generation_settings=original_generation,
            endpoint_confirmation_key="confirmation",
            on_complete=lambda _completion: None,
        )

        original_settings = self.settings("different-secret")
        original_generation = GenerationSettings(card_mode="exam")
        taskman.complete()

        self.assertEqual(calls[0]["material_text"], "original")
        self.assertEqual(calls[0]["settings"].model, "model-a")
        self.assertEqual(calls[0]["generation_settings"].card_mode, "concept")
        snapshot = GenerationRequestSnapshot(
            request_id=9,
            material_text="private material",
            runtime_settings=self.settings("private-secret"),
            generation_settings=GenerationSettings(),
            endpoint_confirmation_key="private-confirmation",
        )
        with self.assertRaises(FrozenInstanceError):
            snapshot.request_id = 10
        rendered = repr(snapshot)
        self.assertNotIn("private material", rendered)
        self.assertNotIn("private-secret", rendered)
        self.assertNotIn("private-confirmation", rendered)

    def test_current_future_exception_becomes_safe_completion(self):
        taskman = DeferredTaskman()
        secret = "secret-from-exception"
        completions = []
        controller = GenerationTaskController(
            taskman,
            generator_factory=lambda: RecordingGenerator(
                [],
                error=RuntimeError(secret),
            ),
        )
        controller.submit(
            material_text="material",
            runtime_settings=self.settings(),
            generation_settings=GenerationSettings(),
            on_complete=completions.append,
        )

        taskman.complete()

        completion = completions[0]
        self.assertIsNone(completion.result)
        self.assertEqual(completion.error_code, "background_task_failed")
        self.assertNotIn(secret, repr(completion))


if __name__ == "__main__":
    unittest.main()
