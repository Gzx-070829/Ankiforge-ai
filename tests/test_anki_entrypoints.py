import types
import unittest

from ankiforge_ai.ui.anki_entrypoints import (
    HOME_COMMAND,
    HOME_MARKER,
    append_deck_browser_launcher,
    handle_webview_message,
    register_home_entry,
)


class RecordingHook:
    def __init__(self):
        self.callbacks = []

    def append(self, callback):
        self.callbacks.append(callback)


class AnkiEntryPointTests(unittest.TestCase):
    def test_deck_browser_launcher_is_added_once(self):
        content = types.SimpleNamespace(stats="<p>stats</p>")

        append_deck_browser_launcher(object(), content)
        append_deck_browser_launcher(object(), content)

        self.assertEqual(content.stats.count(HOME_MARKER), 1)
        self.assertEqual(content.stats.count(HOME_COMMAND), 1)
        self.assertIn("AnkiForge AI", content.stats)

    def test_launcher_does_not_replace_existing_deck_browser_stats(self):
        content = types.SimpleNamespace(stats="<p>existing stats</p>")

        append_deck_browser_launcher(object(), content)

        self.assertTrue(content.stats.startswith("<p>existing stats</p>"))

    def test_only_namespaced_message_opens_workbench(self):
        opened = []

        result = handle_webview_message(
            (False, "previous"),
            HOME_COMMAND,
            object(),
            lambda: opened.append(True),
        )

        self.assertEqual(result, (True, None))
        self.assertEqual(opened, [True])

    def test_foreign_message_is_returned_untouched(self):
        handled = (False, "previous")
        opened = []

        result = handle_webview_message(
            handled,
            "other-addon:open",
            object(),
            lambda: opened.append(True),
        )

        self.assertIs(result, handled)
        self.assertEqual(opened, [])

    def test_registration_adds_one_callback_to_each_required_hook(self):
        gui_hooks = types.SimpleNamespace(
            deck_browser_will_render_content=RecordingHook(),
            webview_did_receive_js_message=RecordingHook(),
        )
        opened = []

        first = register_home_entry(
            gui_hooks,
            lambda: opened.append(True),
        )
        second = register_home_entry(
            gui_hooks,
            lambda: opened.append(False),
        )

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(
            len(gui_hooks.deck_browser_will_render_content.callbacks),
            1,
        )
        self.assertEqual(
            len(gui_hooks.webview_did_receive_js_message.callbacks),
            1,
        )

        content = types.SimpleNamespace(stats="")
        gui_hooks.deck_browser_will_render_content.callbacks[0](
            object(),
            content,
        )
        result = gui_hooks.webview_did_receive_js_message.callbacks[0](
            (False, None),
            HOME_COMMAND,
            object(),
        )
        self.assertEqual(result, (True, None))
        self.assertEqual(opened, [True])
        self.assertIn(HOME_MARKER, content.stats)

    def test_missing_official_hook_fails_closed_without_partial_registration(self):
        render_hook = RecordingHook()
        gui_hooks = types.SimpleNamespace(
            deck_browser_will_render_content=render_hook,
        )

        self.assertFalse(register_home_entry(gui_hooks, lambda: None))
        self.assertEqual(render_hook.callbacks, [])


if __name__ == "__main__":
    unittest.main()
