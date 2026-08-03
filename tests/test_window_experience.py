import unittest

from ankiforge_ai.ui.window_experience import (
    capture_window_state,
    configure_workbench_window,
    focus_when_ready,
    restore_window_geometry,
)
from ankiforge_ai.workbench.window_state import WorkbenchWindowState


class FakeWindowType:
    Window = 1
    WindowTitleHint = 2
    WindowSystemMenuHint = 4
    WindowMinMaxButtonsHint = 8
    WindowCloseButtonHint = 16
    WindowMaximized = 32


class FakeWidgetAttribute:
    WA_DeleteOnClose = 64


class FakeQt:
    WindowType = FakeWindowType
    WidgetAttribute = FakeWidgetAttribute


class RecordingWindow:
    def __init__(
        self,
        *,
        geometry=b"geometry",
        maximized=False,
        restore_result=True,
    ):
        self.geometry = geometry
        self.maximized = maximized
        self.restore_result = restore_result
        self.enabled_flags = []
        self.attributes = []
        self.restored_geometry = None
        self.window_state = 128
        self.assigned_window_state = None

    def setWindowFlag(self, flag, enabled):
        if enabled:
            self.enabled_flags.append(flag)

    def setAttribute(self, attribute, enabled):
        self.attributes.append((attribute, enabled))

    def saveGeometry(self):
        return self.geometry

    def isMaximized(self):
        return self.maximized

    def restoreGeometry(self, value):
        self.restored_geometry = bytes(value)
        return self.restore_result

    def windowState(self):
        return self.window_state

    def setWindowState(self, value):
        self.assigned_window_state = value


class FakeTimer:
    delay = None
    callback = None

    @classmethod
    def singleShot(cls, delay, callback):
        cls.delay = delay
        cls.callback = callback


class FocusTarget:
    def __init__(self):
        self.focused = False

    def setFocus(self):
        self.focused = True


class WindowExperienceTests(unittest.TestCase):
    def tearDown(self):
        FakeTimer.delay = None
        FakeTimer.callback = None

    def test_standard_controls_and_delete_on_close_are_applied(self):
        dialog = RecordingWindow()

        configure_workbench_window(dialog, FakeQt)

        self.assertEqual(
            dialog.enabled_flags,
            [1, 2, 4, 8, 16],
        )
        self.assertEqual(dialog.attributes, [(64, True)])

    def test_capture_returns_only_geometry_and_maximized_state(self):
        dialog = RecordingWindow(
            geometry=b"geometry",
            maximized=True,
        )

        state = capture_window_state(dialog)

        self.assertEqual(
            state,
            WorkbenchWindowState(
                geometry="Z2VvbWV0cnk=",
                maximized=True,
            ),
        )

    def test_valid_geometry_is_restored_and_maximized_without_showing(self):
        dialog = RecordingWindow()
        state = WorkbenchWindowState(
            geometry="Z2VvbWV0cnk=",
            maximized=True,
        )

        restored = restore_window_geometry(
            dialog,
            state,
            bytes,
            FakeWindowType,
        )

        self.assertTrue(restored)
        self.assertEqual(dialog.restored_geometry, b"geometry")
        self.assertEqual(dialog.assigned_window_state, 128 | 32)

    def test_empty_or_unrestorable_geometry_leaves_window_default(self):
        for state, restore_result in (
            (WorkbenchWindowState.defaults(), True),
            (
                WorkbenchWindowState(
                    geometry="Z2VvbWV0cnk=",
                    maximized=True,
                ),
                False,
            ),
        ):
            with self.subTest(state=state, restore_result=restore_result):
                dialog = RecordingWindow(restore_result=restore_result)

                restored = restore_window_geometry(
                    dialog,
                    state,
                    bytes,
                    FakeWindowType,
                )

                self.assertFalse(restored)
                self.assertIsNone(dialog.assigned_window_state)

    def test_focus_is_requested_after_the_window_enters_the_event_loop(self):
        target = FocusTarget()

        focus_when_ready(FakeTimer, target)

        self.assertEqual(FakeTimer.delay, 0)
        self.assertFalse(target.focused)
        FakeTimer.callback()
        self.assertTrue(target.focused)


if __name__ == "__main__":
    unittest.main()
