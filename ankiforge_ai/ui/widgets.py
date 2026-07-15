"""Small PyQt presentation helpers; no state or business decisions live here."""

from aqt.qt import QLabel, QPushButton

from .style_tokens import BUTTON_HEIGHT, PRIMARY_BUTTON_HEIGHT


def make_role_label(text: str = "", role: str = "secondary") -> QLabel:
    label = QLabel(text)
    label.setProperty("role", role)
    return label


def make_action_button(
    text: str,
    *,
    role: str = "secondary",
    primary: bool = False,
) -> QPushButton:
    button = QPushButton(text)
    button.setProperty("role", "primary" if primary else role)
    button.setMinimumHeight(PRIMARY_BUTTON_HEIGHT if primary else BUTTON_HEIGHT)
    return button
