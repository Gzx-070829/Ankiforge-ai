import unittest

import ankiforge_ai


class FakeSignal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self):
        for callback in tuple(self.callbacks):
            callback()


class FakeDialog:
    def __init__(self, *, minimized=False):
        self.minimized = minimized
        self.events = []
        self.destroyed = FakeSignal()

    def isMinimized(self):
        return self.minimized

    def show(self):
        self.events.append("show")

    def showNormal(self):
        self.events.append("showNormal")
        self.minimized = False

    def raise_(self):
        self.events.append("raise")

    def activateWindow(self):
        self.events.append("activate")


class WorkbenchWindowControllerTests(unittest.TestCase):
    def tearDown(self):
        ankiforge_ai._dialog_instance = None

    def test_first_open_shows_modeless_dialog_and_retains_singleton(self):
        dialog = FakeDialog()

        returned = ankiforge_ai._show_main_dialog(
            object(),
            lambda _parent: dialog,
        )

        self.assertIs(returned, dialog)
        self.assertEqual(dialog.events, ["show", "raise", "activate"])
        self.assertIs(ankiforge_ai._dialog_instance, dialog)
        self.assertEqual(len(dialog.destroyed.callbacks), 1)

    def test_repeat_open_restores_and_focuses_existing_minimized_dialog(self):
        dialog = FakeDialog(minimized=True)
        ankiforge_ai._dialog_instance = dialog

        returned = ankiforge_ai._show_main_dialog(
            object(),
            lambda _parent: self.fail("factory must not run"),
        )

        self.assertIs(returned, dialog)
        self.assertEqual(
            dialog.events,
            ["showNormal", "raise", "activate"],
        )

    def test_repeat_open_shows_hidden_existing_dialog_without_recreating_it(self):
        dialog = FakeDialog()
        ankiforge_ai._dialog_instance = dialog

        ankiforge_ai._show_main_dialog(
            object(),
            lambda _parent: self.fail("factory must not run"),
        )

        self.assertEqual(dialog.events, ["show", "raise", "activate"])

    def test_destroyed_dialog_releases_singleton(self):
        dialog = FakeDialog()
        ankiforge_ai._show_main_dialog(object(), lambda _parent: dialog)

        dialog.destroyed.emit()

        self.assertIsNone(ankiforge_ai._dialog_instance)

    def test_stale_destroy_signal_does_not_clear_newer_dialog(self):
        old_dialog = FakeDialog()
        ankiforge_ai._show_main_dialog(object(), lambda _parent: old_dialog)
        new_dialog = FakeDialog()
        ankiforge_ai._dialog_instance = new_dialog

        old_dialog.destroyed.emit()

        self.assertIs(ankiforge_ai._dialog_instance, new_dialog)

    def test_factory_failure_does_not_leave_a_singleton(self):
        def fail(_parent):
            raise RuntimeError("construction failed")

        with self.assertRaisesRegex(RuntimeError, "construction failed"):
            ankiforge_ai._show_main_dialog(object(), fail)

        self.assertIsNone(ankiforge_ai._dialog_instance)


if __name__ == "__main__":
    unittest.main()
