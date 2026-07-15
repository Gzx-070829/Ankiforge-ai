"""Product-grade main window for the Create → Review → Write workflow."""

from aqt import mw
from aqt.qt import QDialog, QHBoxLayout, QLabel, QPushButton, Qt, QVBoxLayout

from ..pipeline.provider_preview import ReadOnlyProviderPreview
from .ai_settings_dialog import AiSettingsDialog
from .card_maker_panel import CardMakerPanel
from .help_dialog import HelpDialog
from .product_i18n import DEFAULT_PRODUCT_LANGUAGE, product_text
from .product_styles import PRODUCT_DARK_STYLESHEET
from .style_tokens import SPACING_SM, SPACING_XL


class MainDialog(QDialog):
    """The only public workbench surface; legacy debug tools are not mounted."""

    def __init__(self, parent=None, provider_preview=None):
        super().__init__(parent)
        self.ui_language = DEFAULT_PRODUCT_LANGUAGE
        self.setObjectName("AnkiForgeMainDialog")
        self.setStyleSheet(PRODUCT_DARK_STYLESHEET)
        if provider_preview is not None and not isinstance(
            provider_preview,
            ReadOnlyProviderPreview,
        ):
            raise ValueError(
                "provider_preview must be ReadOnlyProviderPreview or None."
            )
        self._provider_preview = provider_preview
        self.setWindowTitle(self.t("title"))
        self.resize(1280, 960)
        self._build_ui()

    def t(self, key, **values):
        return product_text(self.ui_language, key, **values)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_XL, 18, SPACING_XL, 14)
        layout.setSpacing(SPACING_SM)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel(self.t("title"))
        self.title_label.setObjectName("ProductTitle")
        self.ai_status_label = QLabel(self.t("ai_not_configured"))
        self.ai_status_label.setObjectName("AiStatusChip")
        self.ai_settings_btn = QPushButton(self.t("ai_settings"))
        self.ai_settings_btn.setObjectName("AiSettingsButton")
        self.ai_settings_btn.clicked.connect(self._open_ai_settings)
        self.help_btn = QPushButton(self.t("help"))
        self.help_btn.setObjectName("HelpButton")
        self.help_btn.clicked.connect(self._open_help)
        self.language_toggle_btn = QPushButton(self.t("language_toggle"))
        self.language_toggle_btn.setObjectName("LanguageToggle")
        self.language_toggle_btn.setFixedSize(96, 35)
        self.language_toggle_btn.setFlat(True)
        self.language_toggle_btn.clicked.connect(self.toggle_language)

        header_row.addWidget(self.title_label)
        header_row.addStretch()
        header_row.addWidget(self.ai_status_label)
        header_row.addWidget(self.ai_settings_btn)
        header_row.addWidget(self.help_btn)
        header_row.addWidget(self.language_toggle_btn)
        header_row.setAlignment(
            self.language_toggle_btn,
            Qt.AlignmentFlag.AlignVCenter,
        )
        layout.addLayout(header_row)

        self.subtitle_label = QLabel(self.t("subtitle"))
        self.subtitle_label.setObjectName("ProductSubtitle")
        self.subtitle_label.setContentsMargins(2, 0, 0, 8)
        layout.addWidget(self.subtitle_label)

        collection = getattr(mw, "col", None)
        self.card_maker_panel = CardMakerPanel(
            parent=self,
            collection=collection,
            language=self.ui_language,
        )
        panel_row = QHBoxLayout()
        panel_row.addStretch()
        panel_row.addWidget(self.card_maker_panel, 1)
        panel_row.addStretch()
        layout.addLayout(panel_row, 1)
        self._refresh_ai_status()

    def toggle_language(self):
        self.ui_language = "en" if self.ui_language == "zh" else "zh"
        self.setWindowTitle(self.t("title"))
        self.title_label.setText(self.t("title"))
        self.subtitle_label.setText(self.t("subtitle"))
        self.language_toggle_btn.setText(self.t("language_toggle"))
        self.ai_settings_btn.setText(self.t("ai_settings"))
        self.help_btn.setText(self.t("help"))
        self.card_maker_panel.set_language(self.ui_language)
        self._refresh_ai_status()

    def _open_ai_settings(self):
        dialog = AiSettingsDialog(
            parent=self,
            language=self.ui_language,
            settings=self.card_maker_panel.ai_runtime_settings(),
        )
        accepted = (
            QDialog.DialogCode.Accepted
            if hasattr(QDialog, "DialogCode")
            else QDialog.Accepted
        )
        if dialog.exec() != accepted:
            return
        settings = dialog.runtime_settings()
        if settings is None:
            return
        self.card_maker_panel.set_ai_runtime_settings(settings)
        self._refresh_ai_status()

    def _open_help(self):
        dialog = HelpDialog(parent=self, language=self.ui_language)
        dialog.exec()
        if dialog.use_example_requested:
            self.card_maker_panel._use_example_material()

    def _refresh_ai_status(self):
        settings = self.card_maker_panel.ai_runtime_settings()
        if settings is None:
            text = self.t("ai_not_configured")
            self.ai_status_label.setProperty("configured", False)
        else:
            text = self.t("ai_configured", provider=settings.provider_name)
            self.ai_status_label.setProperty("configured", True)
        self.ai_status_label.setText(text)
        self.ai_status_label.style().unpolish(self.ai_status_label)
        self.ai_status_label.style().polish(self.ai_status_label)

    def closeEvent(self, event):
        self.card_maker_panel.discard_session()
        super().closeEvent(event)
