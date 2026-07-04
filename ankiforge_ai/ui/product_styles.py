"""Scoped dark product styles for the single-screen card maker."""


PRODUCT_DARK_STYLESHEET = """
QDialog#AnkiForgeMainDialog {
    background-color: #202124;
    color: #F4F4F5;
}

QDialog#AnkiForgeMainDialog QLabel {
    color: #F4F4F5;
    font-size: 14px;
}

QLabel#ProductTitle {
    color: #F8FAFC;
    font-size: 30px;
    font-weight: 700;
}

QLabel#ProductSubtitle {
    color: #9CA3AF;
    font-size: 16px;
}

QWidget#CardMakerPanel {
    background: transparent;
}

QWidget#CardMakerPanel QLabel[role="secondary"] {
    color: #9CA3AF;
    font-size: 13px;
    font-weight: 400;
}

QWidget#CardMakerPanel QLabel[role="muted"] {
    color: #6B7280;
    font-size: 12px;
    font-weight: 400;
}

QWidget#CardMakerPanel QLabel[role="sectionTitle"] {
    color: #F8FAFC;
    font-size: 16px;
    font-weight: 600;
    padding: 0;
}

QWidget#CardMakerPanel QLabel[role="fieldLabel"] {
    color: #D1D5DB;
    font-size: 13px;
    font-weight: 500;
}

QLabel#EmptyStateTitle {
    color: #E5E7EB;
    font-size: 19px;
    font-weight: 600;
}

QLabel#EmptyStateHelp {
    color: #6B7280;
    font-size: 13px;
    font-weight: 400;
}

QWidget#CardMakerPanel QFrame[sectionCard="true"] {
    background-color: #2B2D30;
    border: 1px solid #3F4248;
    border-radius: 10px;
    color: #F4F4F5;
}

QWidget#CardMakerPanel QGroupBox[cardItem="true"] {
    background-color: #25272A;
    border: 1px solid #3F4248;
    border-radius: 7px;
    margin-top: 13px;
    padding: 10px;
    color: #F4F4F5;
}

QWidget#CardMakerPanel QGroupBox[cardItem="true"]::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: #D1D5DB;
    background: transparent;
    font-weight: 600;
}

QWidget#CardsEmptyState {
    background-color: #1F2023;
    border: 1px dashed #3F4248;
    border-radius: 7px;
}

QWidget#CardsList {
    background: transparent;
}

QWidget#CardMakerPanel QTextEdit,
QWidget#CardMakerPanel QLineEdit,
QWidget#CardMakerPanel QComboBox,
QWidget#CardMakerPanel QSpinBox {
    background-color: #1F2023;
    color: #F4F4F5;
    border: 1px solid #3F4248;
    border-radius: 6px;
    padding: 6px 8px;
    selection-background-color: #2563EB;
    min-height: 30px;
}

QWidget#CardMakerPanel QTextEdit:focus,
QWidget#CardMakerPanel QLineEdit:focus,
QWidget#CardMakerPanel QComboBox:focus,
QWidget#CardMakerPanel QSpinBox:focus {
    border: 1px solid #3B82F6;
}

QWidget#CardMakerPanel QComboBox::drop-down {
    border: none;
    width: 24px;
}

QWidget#CardMakerPanel QComboBox QAbstractItemView {
    background-color: #2B2D30;
    color: #F4F4F5;
    border: 1px solid #3F4248;
    selection-background-color: #2563EB;
}

QWidget#CardMakerPanel QPushButton,
QPushButton[role="secondary"] {
    background-color: #32343A;
    color: #E5E7EB;
    border: 1px solid #4B4F57;
    border-radius: 6px;
    padding: 6px 12px;
    min-height: 28px;
}

QWidget#CardMakerPanel QPushButton:hover,
QPushButton[role="secondary"]:hover {
    background-color: #3A3D42;
    border-color: #60656F;
}

QWidget#CardMakerPanel QPushButton[role="primary"] {
    background-color: #3B82F6;
    color: #FFFFFF;
    border: 1px solid #3B82F6;
    border-radius: 7px;
    padding: 8px 22px;
    min-height: 38px;
    font-size: 14px;
    font-weight: 700;
}

QWidget#CardMakerPanel QPushButton[role="primary"]:hover {
    background-color: #2563EB;
    border-color: #2563EB;
}

QWidget#CardMakerPanel QPushButton[role="primary"]:disabled {
    background-color: #3A3D42;
    color: #7A7F87;
    border-color: #3A3D42;
}

QWidget#CardMakerPanel QPushButton[role="subtle"] {
    background: transparent;
    color: #9CA3AF;
    border: none;
    padding: 4px 6px;
    min-height: 22px;
}

QWidget#CardMakerPanel QPushButton[role="subtle"]:hover {
    color: #D1D5DB;
    background-color: #32343A;
}

QPushButton#LanguageToggle {
    background-color: #2B2D30;
    color: #D1D5DB;
    border: 1px solid #4B4F57;
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 13px;
}

QPushButton#LanguageToggle:hover {
    color: #FFFFFF;
    border-color: #6B7280;
    background-color: #32343A;
}

QPushButton#AdvancedDebugLink {
    background: transparent;
    color: #6B7280;
    border: none;
    padding: 3px 5px;
    font-size: 11px;
}

QPushButton#AdvancedDebugLink:hover {
    color: #9CA3AF;
}

QWidget#CardMakerPanel QRadioButton {
    color: #D1D5DB;
    spacing: 6px;
}

QWidget#CardMakerPanel QScrollArea {
    background: transparent;
    border: none;
}

QWidget#CardMakerPanel QScrollBar:vertical {
    background: #25272A;
    width: 9px;
    margin: 0;
}

QWidget#CardMakerPanel QScrollBar::handle:vertical {
    background: #4B4F57;
    border-radius: 4px;
    min-height: 24px;
}

QWidget#CardMakerPanel QScrollBar::add-line:vertical,
QWidget#CardMakerPanel QScrollBar::sub-line:vertical {
    height: 0;
}
"""
