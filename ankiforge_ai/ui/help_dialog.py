"""Compact product onboarding dialog with no background network behavior."""

from aqt.qt import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from .product_i18n import DEFAULT_PRODUCT_LANGUAGE, product_text
from .style_tokens import SPACING_MD, SPACING_XL


class HelpDialog(QDialog):
    COPY_KEYS = (
        "help_addon_identity",
        "help_own_material",
        "help_provider",
        "help_session_key",
        "help_review",
        "help_confirmation",
        "help_test_deck",
        "help_pdf",
    )

    def __init__(self, parent=None, language=DEFAULT_PRODUCT_LANGUAGE):
        super().__init__(parent)
        self.language = language
        self.use_example_requested = False
        self.setObjectName("HelpDialog")
        self.setWindowTitle(self.t("help"))
        self.setMinimumWidth(520)
        self._build_ui()

    def t(self, key):
        return product_text(self.language, key)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_XL, 20, SPACING_XL, 20)
        layout.setSpacing(SPACING_MD)
        title = QLabel(self.t("help_title"))
        title.setObjectName("HelpTitle")
        layout.addWidget(title)
        for key in self.COPY_KEYS:
            label = QLabel("• " + self.t(key))
            label.setWordWrap(True)
            label.setProperty("role", "secondary")
            layout.addWidget(label)
        buttons = QHBoxLayout()
        buttons.addStretch()
        example_btn = QPushButton(self.t("help_use_example"))
        example_btn.setProperty("role", "secondary")
        example_btn.clicked.connect(self._request_example)
        close_btn = QPushButton(self.t("help_close"))
        close_btn.setProperty("role", "dialogPrimary")
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(example_btn)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

    def _request_example(self):
        self.use_example_requested = True
        self.accept()
