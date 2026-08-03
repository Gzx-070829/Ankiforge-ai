"""Small, defensive Anki entry-point helpers for the public workbench."""

from __future__ import annotations

from typing import Any, Callable


HOME_COMMAND = "ankiforge-ai:open"
HOME_MARKER = "ankiforge-ai-home-entry"
_registered_gui_hook_objects = globals().get(
    "_registered_gui_hook_objects",
    [],
)


def _launcher_markup() -> str:
    return (
        f'\n<div id="{HOME_MARKER}" '
        'style="margin-top:12px;text-align:center">'
        f'<a href="#" onclick="pycmd(\'{HOME_COMMAND}\'); return false;" '
        'aria-label="Open AnkiForge AI">AnkiForge AI</a>'
        "</div>"
    )


def append_deck_browser_launcher(deck_browser: Any, content: Any) -> None:
    """Append one native-looking launcher without replacing Anki content."""

    del deck_browser
    current = getattr(content, "stats", None)
    if not isinstance(current, str) or HOME_MARKER in current:
        return
    content.stats = current + _launcher_markup()


def handle_webview_message(
    handled: tuple[bool, Any],
    message: str,
    context: Any,
    open_workbench: Callable[[], Any],
) -> tuple[bool, Any]:
    """Handle only the add-on's namespaced launcher command."""

    del context
    if message != HOME_COMMAND:
        return handled
    open_workbench()
    return (True, None)


def register_home_entry(gui_hooks: Any, open_workbench: Callable[[], Any]) -> bool:
    """Register the two official hooks once for a GUI-hook collection."""

    if not callable(open_workbench):
        raise TypeError("open_workbench must be callable")
    render_hook = getattr(
        gui_hooks,
        "deck_browser_will_render_content",
        None,
    )
    message_hook = getattr(
        gui_hooks,
        "webview_did_receive_js_message",
        None,
    )
    if not callable(getattr(render_hook, "append", None)) or not callable(
        getattr(message_hook, "append", None)
    ):
        return False
    if any(
        registered is gui_hooks
        for registered in _registered_gui_hook_objects
    ):
        return False

    def on_render(deck_browser, content):
        append_deck_browser_launcher(deck_browser, content)

    def on_message(handled, message, context):
        return handle_webview_message(
            handled,
            message,
            context,
            open_workbench,
        )

    render_hook.append(on_render)
    message_hook.append(on_message)
    _registered_gui_hook_objects.append(gui_hooks)
    return True
