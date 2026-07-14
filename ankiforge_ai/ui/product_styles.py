"""Scoped v0.12.5 product styles for the linear card-making workflow."""


PRODUCT_DARK_STYLESHEET = """
QDialog#AnkiForgeMainDialog {
    background-color: #0D1117;
    color: #F8FAFC;
}

QDialog#AnkiForgeMainDialog QLabel {
    color: #F8FAFC;
    font-size: 13px;
}

QLabel#ProductTitle {
    color: #F8FAFC;
    font-size: 18px;
    font-weight: 700;
}

QLabel#ProductSubtitle {
    color: #7D8EA3;
    font-size: 13px;
}

QWidget#CardMakerPanel {
    background: transparent;
}

QFrame[workflowPanel="true"] {
    background-color: #111827;
    border: 1px solid #263241;
    border-radius: 12px;
}

QWidget#CardMakerPanel QLabel[role="panelTitle"] {
    color: #F8FAFC;
    font-size: 16px;
    font-weight: 600;
}

QWidget#CardMakerPanel QLabel[role="sectionTitle"] {
    color: #CBD5E1;
    font-size: 13px;
    font-weight: 600;
    padding: 0;
}

QWidget#CardMakerPanel QLabel[role="secondary"] {
    color: #CBD5E1;
    font-size: 13px;
}

QWidget#CardMakerPanel QLabel[role="muted"],
QDialog#AiSettingsDialog QLabel[role="muted"] {
    color: #7D8EA3;
    font-size: 12px;
}

QWidget#CardMakerPanel QLabel[role="fieldLabel"],
QDialog#AiSettingsDialog QLabel[role="fieldLabel"] {
    color: #CBD5E1;
    font-size: 13px;
    font-weight: 500;
}

QWidget#CardMakerPanel QFrame[sectionBody="true"] {
    background: transparent;
    border: none;
}

QWidget#CardMakerPanel QFrame[sectionCard="true"],
QFrame#WriteFooter {
    background-color: #161B22;
    border: 1px solid #263241;
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
    color: #CBD5E1;
    background-color: #161B22;
    border: 1px solid #263241;
}

QWidget#CardMakerPanel QLabel[role="success"] {
    color: #86EFAC;
    background-color: #102A1B;
    border: 1px solid #1F5A36;
}

QWidget#CardMakerPanel QLabel[role="warning"] {
    color: #FCD34D;
    background-color: #2B220E;
    border: 1px solid #5B4316;
}

QWidget#CardMakerPanel QLabel[role="error"],
QDialog#AiSettingsDialog QLabel[role="error"] {
    color: #FCA5A5;
    background-color: #30171B;
    border: 1px solid #6A2730;
}

QWidget#CardsEmptyState {
    background-color: #0F141B;
    border: 1px dashed #263241;
    border-radius: 10px;
}

QLabel#EmptyStateGlyph {
    color: #7C5CFF;
    font-size: 24px;
    font-weight: 600;
}

QLabel#EmptyStateTitle {
    color: #CBD5E1;
    font-size: 16px;
    font-weight: 600;
}

QLabel#EmptyStateHelp {
    color: #7D8EA3;
    font-size: 12px;
}

QWidget#CardsList {
    background: transparent;
}

QWidget#CardMakerPanel QGroupBox[cardItem="true"] {
    background-color: #161B22;
    border: 1px solid #263241;
    border-radius: 10px;
    margin-top: 13px;
    padding: 10px;
    color: #F8FAFC;
}

QWidget#CardMakerPanel QGroupBox[cardItem="true"]::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: #CBD5E1;
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
    background-color: #0F141B;
    color: #F8FAFC;
    border: 1px solid #263241;
    border-radius: 10px;
    padding: 6px 9px;
    selection-background-color: #7C5CFF;
    min-height: 28px;
}

QWidget#CardMakerPanel QTextEdit:focus,
QWidget#CardMakerPanel QLineEdit:focus,
QWidget#CardMakerPanel QComboBox:focus,
QWidget#CardMakerPanel QSpinBox:focus,
QDialog#AiSettingsDialog QLineEdit:focus,
QDialog#AiSettingsDialog QComboBox:focus,
QDialog#AiSettingsDialog QSpinBox:focus {
    border: 1px solid #7C5CFF;
}

QWidget#CardMakerPanel QTextEdit#MaterialDropArea {
    background-color: #0F141B;
    border: 1px dashed #334155;
    border-radius: 10px;
    padding: 12px;
}

QWidget#CardMakerPanel QTextEdit#MaterialDropArea:focus {
    border: 1px solid #7C5CFF;
    background-color: #111821;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #161B22;
    color: #F8FAFC;
    border: 1px solid #334155;
    selection-background-color: #7C5CFF;
}

QWidget#CardMakerPanel QPushButton,
QPushButton[role="secondary"],
QPushButton[role="dialogSecondary"] {
    background-color: #161B22;
    color: #CBD5E1;
    border: 1px solid #263241;
    border-radius: 10px;
    padding: 7px 13px;
    min-height: 28px;
}

QWidget#CardMakerPanel QPushButton:hover,
QPushButton[role="secondary"]:hover,
QPushButton[role="dialogSecondary"]:hover {
    background-color: #1C2430;
    border-color: #334155;
}

QWidget#CardMakerPanel QPushButton[role="primary"],
QPushButton[role="dialogPrimary"] {
    background-color: #7C5CFF;
    color: #FFFFFF;
    border: 1px solid #7C5CFF;
    border-radius: 10px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 600;
}

QWidget#CardMakerPanel QPushButton[role="primary"]:hover,
QPushButton[role="dialogPrimary"]:hover {
    background-color: #8B73FF;
    border-color: #8B73FF;
}

QWidget#CardMakerPanel QPushButton[role="primary"]:disabled {
    background-color: #292347;
    color: #8F83C7;
    border-color: #3C3266;
}

QWidget#CardMakerPanel QPushButton[role="subtle"] {
    background: transparent;
    color: #7D8EA3;
    border: none;
    padding: 4px 6px;
    min-height: 22px;
}

QWidget#CardMakerPanel QPushButton[role="subtle"]:hover {
    color: #CBD5E1;
    background-color: #1C2430;
}

QLabel#AiStatusChip {
    color: #7D8EA3;
    background-color: #111827;
    border: 1px solid #263241;
    border-radius: 10px;
    padding: 6px 10px;
    font-size: 12px;
}

QLabel#AiStatusChip[configured="true"] {
    color: #A99AFF;
    background-color: rgba(124, 92, 255, 0.12);
    border-color: #4B3A8F;
}

QPushButton#AiSettingsButton,
QPushButton#LanguageToggle {
    background-color: #111827;
    color: #CBD5E1;
    border: 1px solid #263241;
    border-radius: 10px;
    padding: 6px 12px;
    min-height: 24px;
    font-size: 13px;
}

QPushButton#AiSettingsButton:hover,
QPushButton#LanguageToggle:hover {
    color: #FFFFFF;
    border-color: #334155;
    background-color: #1C2430;
}

QDialog#AiSettingsDialog {
    background: transparent;
}

QFrame#AiSettingsSurface {
    background-color: #161B22;
    border: 1px solid #263241;
    border-radius: 12px;
}

QWidget#AiSettingsTitleBar {
    background: transparent;
}

QLabel#AiSettingsTitle {
    color: #F8FAFC;
    font-size: 16px;
    font-weight: 600;
}

QPushButton#AiSettingsClose {
    background: transparent;
    color: #7D8EA3;
    border: none;
    border-radius: 8px;
    font-size: 20px;
}

QPushButton#AiSettingsClose:hover {
    background-color: #1C2430;
    color: #F8FAFC;
}

QLabel#AiSettingsSessionNote {
    color: #7D8EA3;
    font-size: 12px;
}

QPushButton#AdvancedDebugLink {
    background: transparent;
    color: #7D8EA3;
    border: none;
    padding: 3px 5px;
    font-size: 11px;
}

QWidget#CardMakerPanel QRadioButton {
    color: #CBD5E1;
    spacing: 6px;
}

QWidget#CardMakerPanel QScrollArea {
    background: transparent;
    border: none;
}

QWidget#CardMakerPanel QScrollBar:vertical {
    background: #111827;
    width: 9px;
    margin: 0;
}

QWidget#CardMakerPanel QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 4px;
    min-height: 24px;
}

QWidget#CardMakerPanel QScrollBar::add-line:vertical,
QWidget#CardMakerPanel QScrollBar::sub-line:vertical {
    height: 0;
}
"""
