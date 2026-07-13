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
    font-size: 18px;
    font-weight: 700;
}

QLabel#ProductSubtitle {
    color: #9CA3AF;
    font-size: 13px;
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

QWidget#CardMakerPanel QLabel[role="subsectionTitle"] {
    color: #D1D5DB;
    font-size: 13px;
    font-weight: 600;
    padding-top: 3px;
}

QWidget#CardMakerPanel QLabel[role="status"],
QWidget#CardMakerPanel QLabel[role="success"],
QWidget#CardMakerPanel QLabel[role="warning"],
QWidget#CardMakerPanel QLabel[role="error"] {
    border-radius: 5px;
    padding: 5px 8px;
    font-size: 12px;
    font-weight: 500;
}

QWidget#CardMakerPanel QLabel[role="status"] {
    color: #CBD5E1;
    background-color: #24272B;
    border: 1px solid #353A42;
}

QWidget#CardMakerPanel QLabel[role="success"] {
    color: #86EFAC;
    background-color: #163224;
    border: 1px solid #245C3A;
}

QWidget#CardMakerPanel QLabel[role="warning"] {
    color: #FCD34D;
    background-color: #332B14;
    border: 1px solid #5D4A1C;
}

QWidget#CardMakerPanel QLabel[role="error"] {
    color: #FCA5A5;
    background-color: #351C20;
    border: 1px solid #6B2A32;
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
    border-radius: 8px;
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
    border-radius: 8px;
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

QWidget#CardMakerPanel QTextEdit#MaterialDropArea {
    background-color: #1C2025;
    border: 1px dashed #596273;
    border-radius: 8px;
    padding: 10px;
}

QWidget#CardMakerPanel QTextEdit#MaterialDropArea:focus {
    border: 1px solid #3B82F6;
    background-color: #1F2329;
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
    border-radius: 8px;
    padding: 7px 13px;
    min-height: 29px;
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
    border-radius: 8px;
    padding: 8px 22px;
    min-height: 38px;
    font-size: 13px;
    font-weight: 700;
}

QWidget#CardMakerPanel QPushButton[role="primary"]:hover {
    background-color: #2563EB;
    border-color: #2563EB;
}

QWidget#CardMakerPanel QPushButton[role="primary"]:disabled {
    background-color: #334155;
    color: #94A3B8;
    border-color: #475569;
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
    background-color: #25292E;
    color: #D1D5DB;
    border: 1px solid #4B4F57;
    border-radius: 17px;
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
