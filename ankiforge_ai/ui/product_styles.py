"""Scoped product styles for the simple Create → Review → Write workflow."""

from .style_tokens import product_palette


_STYLE_TEMPLATE = """
QDialog#AnkiForgeMainDialog {
    background-color: @app_bg@;
    color: @text_primary@;
}

QDialog#AnkiForgeMainDialog QLabel {
    color: @text_primary@;
    font-size: 13px;
}

QLabel#ProductTitle {
    color: @text_primary@;
    font-size: 18px;
    font-weight: 700;
}

QLabel#ProductSubtitle {
    color: @text_muted@;
    font-size: 13px;
}

QWidget#CardMakerPanel {
    background: transparent;
}

QFrame[workflowPanel="true"] {
    background-color: @surface@;
    border: 1px solid @border_subtle@;
    border-radius: 12px;
}

QWidget#CardMakerPanel QLabel[role="panelTitle"] {
    color: @text_primary@;
    font-size: 16px;
    font-weight: 600;
}

QWidget#CardMakerPanel QLabel[role="sectionTitle"] {
    color: @text_secondary@;
    font-size: 13px;
    font-weight: 600;
    padding: 0;
}

QWidget#CardMakerPanel QLabel[role="secondary"] {
    color: @text_secondary@;
    font-size: 13px;
}

QWidget#CardMakerPanel QLabel[role="muted"],
QDialog#AiSettingsDialog QLabel[role="muted"] {
    color: @text_muted@;
    font-size: 12px;
}

QWidget#CardMakerPanel QLabel[role="fieldLabel"],
QDialog#AiSettingsDialog QLabel[role="fieldLabel"] {
    color: @text_secondary@;
    font-size: 13px;
    font-weight: 500;
}

QWidget#CardMakerPanel QFrame[sectionBody="true"] {
    background: transparent;
    border: none;
}

QWidget#CardMakerPanel QFrame[sectionCard="true"] {
    background-color: @surface_elevated@;
    border: none;
    border-radius: 10px;
}

QFrame#WriteFooter {
    background-color: @surface_elevated@;
    border: 1px solid @border_subtle@;
    border-radius: 10px;
}

QWidget#CardMakerPanel QLabel[role="status"],
QWidget#CardMakerPanel QLabel[role="success"],
QWidget#CardMakerPanel QLabel[role="warning"],
QWidget#CardMakerPanel QLabel[role="error"],
QDialog#AiSettingsDialog QLabel[role="error"] {
    border-radius: 7px;
    padding: 5px 8px;
    font-size: 12px;
    font-weight: 500;
}

QWidget#CardMakerPanel QLabel[role="status"] {
    color: @text_secondary@;
    background-color: @surface_elevated@;
    border: 1px solid @border_subtle@;
}

QWidget#CardMakerPanel QLabel[role="success"] {
    color: @success_text@;
    background-color: @success_bg@;
    border: 1px solid @success_border@;
}

QWidget#CardMakerPanel QLabel[role="warning"] {
    color: @warning_text@;
    background-color: @warning_bg@;
    border: 1px solid @warning_border@;
}

QWidget#CardMakerPanel QLabel[role="error"],
QDialog#AiSettingsDialog QLabel[role="error"] {
    color: @danger_text@;
    background-color: @danger_bg@;
    border: 1px solid @danger_border@;
}

QWidget#CardsEmptyState {
    background-color: @input_bg@;
    border: 1px dashed @border_subtle@;
    border-radius: 10px;
}

QLabel#EmptyStateTitle {
    color: @text_secondary@;
    font-size: 16px;
    font-weight: 600;
}

QLabel#EmptyStateHelp {
    color: @text_muted@;
    font-size: 12px;
}

QWidget#CardsList {
    background: transparent;
}

QWidget#CardMakerPanel QGroupBox[cardItem="true"] {
    background-color: @surface_elevated@;
    border: 1px solid @border_subtle@;
    border-radius: 10px;
    margin-top: 13px;
    padding: 10px;
    color: @text_primary@;
}

QWidget#CardMakerPanel QGroupBox[cardItem="true"]::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: @text_secondary@;
    background: transparent;
    font-weight: 600;
}

QWidget#CardMakerPanel QTextEdit,
QWidget#CardMakerPanel QLineEdit,
QWidget#CardMakerPanel QComboBox,
QWidget#CardMakerPanel QSpinBox,
QDialog#AiSettingsDialog QLineEdit,
QDialog#AiSettingsDialog QComboBox,
QDialog#AiSettingsDialog QSpinBox {
    background-color: @input_bg@;
    color: @text_primary@;
    border: 1px solid @border_subtle@;
    border-radius: 10px;
    padding: 6px 9px;
    selection-background-color: @accent@;
    selection-color: @app_bg@;
    min-height: 28px;
}

QWidget#CardMakerPanel QTextEdit:focus,
QWidget#CardMakerPanel QLineEdit:focus,
QWidget#CardMakerPanel QComboBox:focus,
QWidget#CardMakerPanel QSpinBox:focus,
QDialog#AiSettingsDialog QLineEdit:focus,
QDialog#AiSettingsDialog QComboBox:focus,
QDialog#AiSettingsDialog QSpinBox:focus {
    border: 1px solid @accent@;
}

QWidget#CardMakerPanel QTextEdit#MaterialDropArea {
    background-color: @input_bg@;
    border: 1px solid @border_strong@;
    border-radius: 10px;
    padding: 12px;
}

QWidget#CardMakerPanel QTextEdit#MaterialDropArea:focus {
    border: 1px solid @accent@;
    background-color: @surface@;
}

QFrame#MaterialImportRow,
QFrame#GenerationSettingsDisclosure {
    background-color: @surface_elevated@;
    border: none;
    border-radius: 10px;
    padding: 8px 10px;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox:on {
    background-color: @hover_bg@;
    border-color: @accent_border@;
}

QComboBox QAbstractItemView {
    background-color: @surface_elevated@;
    color: @text_primary@;
    border: 1px solid @border_strong@;
    selection-background-color: @accent@;
    selection-color: @app_bg@;
}

QWidget#CardMakerPanel QPushButton,
QPushButton[role="secondary"],
QPushButton[role="dialogSecondary"] {
    background-color: @surface_elevated@;
    color: @text_secondary@;
    border: 1px solid @border_subtle@;
    border-radius: 10px;
    padding: 7px 13px;
    min-height: 28px;
}

QWidget#CardMakerPanel QPushButton:hover,
QPushButton[role="secondary"]:hover,
QPushButton[role="dialogSecondary"]:hover {
    background-color: @hover_bg@;
    border-color: @border_strong@;
}

QWidget#CardMakerPanel QPushButton:pressed,
QPushButton[role="secondary"]:pressed,
QPushButton[role="dialogSecondary"]:pressed {
    background-color: @input_bg@;
    border-color: @accent_border@;
    color: @text_primary@;
}

QWidget#CardMakerPanel QPushButton[role="primary"],
QPushButton[role="dialogPrimary"] {
    background-color: @accent@;
    color: @app_bg@;
    border: 1px solid @accent@;
    border-radius: 10px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 600;
}

QWidget#CardMakerPanel QPushButton[role="primary"]:hover,
QPushButton[role="dialogPrimary"]:hover {
    background-color: @accent_hover@;
    border-color: @accent_hover@;
}

QWidget#CardMakerPanel QPushButton[role="primary"]:pressed,
QPushButton[role="primary"]:pressed,
QPushButton[role="dialogPrimary"]:pressed {
    background-color: @accent_text@;
    border-color: @accent_text@;
}

QWidget#CardMakerPanel QPushButton[role="primary"]:disabled {
    background-color: @disabled_bg@;
    color: @disabled_text@;
    border-color: @disabled_border@;
}

QWidget#CardMakerPanel QPushButton[role="subtle"] {
    background: transparent;
    color: @text_muted@;
    border: none;
    padding: 4px 6px;
    min-height: 22px;
}

QWidget#CardMakerPanel QPushButton[role="subtle"]:hover {
    color: @text_secondary@;
    background-color: @hover_bg@;
}

QWidget#CardMakerPanel QPushButton[role="subtle"]:checked {
    color: @accent_text@;
    background-color: @accent_soft@;
}

QLabel#AiStatusChip {
    color: @text_muted@;
    background-color: @surface@;
    border: 1px solid @border_subtle@;
    border-radius: 10px;
    padding: 6px 10px;
    font-size: 12px;
}

QLabel#AiStatusChip[configured="true"] {
    color: @accent_text@;
    background-color: @accent_soft@;
    border-color: @accent_border@;
}

QPushButton#AiSettingsButton,
QPushButton#HelpButton,
QPushButton#LanguageToggle {
    background-color: @surface@;
    color: @text_secondary@;
    border: 1px solid @border_subtle@;
    border-radius: 10px;
    padding: 6px 12px;
    min-height: 24px;
    font-size: 13px;
}

QPushButton#AiSettingsButton:hover,
QPushButton#HelpButton:hover,
QPushButton#LanguageToggle:hover {
    color: @text_primary@;
    border-color: @border_strong@;
    background-color: @hover_bg@;
}

QPushButton#AiSettingsButton:pressed,
QPushButton#HelpButton:pressed,
QPushButton#LanguageToggle:pressed {
    color: @accent_text@;
    border-color: @accent_border@;
    background-color: @input_bg@;
}

QDialog#AiSettingsDialog {
    background: transparent;
}

QDialog#HelpDialog {
    background-color: @surface@;
    color: @text_primary@;
}

QDialog#HelpDialog QLabel[role="secondary"] {
    color: @text_secondary@;
    padding: 2px 0;
}

QLabel#HelpTitle {
    color: @text_primary@;
    font-size: 16px;
    font-weight: 600;
}

QFrame#AiSettingsSurface {
    background-color: @surface_elevated@;
    border: 1px solid @border_subtle@;
    border-radius: 12px;
}

QWidget#AiSettingsTitleBar {
    background: transparent;
}

QLabel#AiSettingsTitle {
    color: @text_primary@;
    font-size: 16px;
    font-weight: 600;
}

QPushButton#AiSettingsClose {
    background: transparent;
    color: @text_muted@;
    border: none;
    border-radius: 8px;
    font-size: 20px;
}

QPushButton#AiSettingsClose:hover {
    background-color: @hover_bg@;
    color: @text_primary@;
}

QPushButton#AiSettingsClose:pressed {
    background-color: @input_bg@;
    color: @accent_text@;
}

QDialog#DocumentCapabilitiesDialog,
QMessageBox {
    background-color: @surface@;
    color: @text_primary@;
}

QDialog#DocumentCapabilitiesDialog QLabel,
QMessageBox QLabel {
    color: @text_secondary@;
}

QDialog#DocumentCapabilitiesDialog QWidget[capabilityRow="true"] {
    background-color: @surface_elevated@;
    border: 1px solid @border_subtle@;
    border-radius: 10px;
}

QDialog#DocumentCapabilitiesDialog QLabel[role="fieldLabel"] {
    color: @text_primary@;
    font-weight: 600;
}

QDialog#DocumentCapabilitiesDialog QLabel[role="status"] {
    color: @accent_text@;
}

QDialog#DocumentCapabilitiesDialog QScrollArea {
    background: transparent;
    border: none;
}

QDialog#DocumentCapabilitiesDialog QRadioButton {
    color: @text_secondary@;
    spacing: 6px;
}

QMenu {
    background-color: @surface_elevated@;
    color: @text_secondary@;
    border: 1px solid @border_strong@;
    border-radius: 10px;
    padding: 6px;
}

QMenu::item {
    border-radius: 7px;
    padding: 8px 22px 8px 12px;
}

QMenu::item:selected {
    background-color: @hover_bg@;
    color: @text_primary@;
}

QMenu::item:pressed {
    background-color: @accent_soft@;
    color: @accent_text@;
}

QLabel#AiSettingsSessionNote {
    color: @text_muted@;
    font-size: 12px;
}

QPushButton#AdvancedDebugLink {
    background: transparent;
    color: @text_muted@;
    border: none;
    padding: 3px 5px;
    font-size: 11px;
}

QWidget#CardMakerPanel QRadioButton {
    color: @text_secondary@;
    spacing: 6px;
}

QWidget#CardMakerPanel QScrollArea {
    background: transparent;
    border: none;
}

QWidget#CardMakerPanel QScrollBar:vertical {
    background: @surface@;
    width: 9px;
    margin: 0;
}

QWidget#CardMakerPanel QScrollBar::handle:vertical {
    background: @border_strong@;
    border-radius: 4px;
    min-height: 24px;
}

QWidget#CardMakerPanel QScrollBar::add-line:vertical,
QWidget#CardMakerPanel QScrollBar::sub-line:vertical {
    height: 0;
}

QWidget#DocumentQueueRow {
    background-color: @input_bg@;
    border: 1px solid @border_subtle@;
    border-radius: 8px;
}

QWidget#DocumentQueueRow QPushButton {
    min-height: 28px;
    padding: 2px 8px;
}

QPushButton#SourceChip {
    min-height: 28px;
    border: 1px solid @accent_border@;
    border-radius: 10px;
    color: @accent_text@;
    background-color: @accent_soft@;
}

QLabel#StageProgress {
    color: @text_secondary@;
    padding: 4px 0;
}
"""


def _render_stylesheet(template: str) -> str:
    rendered = template
    for name, value in product_palette().items():
        rendered = rendered.replace(f"@{name}@", value)
    if "@" in rendered:
        raise RuntimeError("product stylesheet contains an unresolved token")
    return rendered


# Compatibility name retained for existing callers and add-on upgrades.
PRODUCT_DARK_STYLESHEET = _render_stylesheet(_STYLE_TEMPLATE)
