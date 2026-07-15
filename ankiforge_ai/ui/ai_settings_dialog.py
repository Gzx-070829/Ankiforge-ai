"""Session-only AI provider settings dialog for the product workflow."""

from aqt.qt import (
    QColor,
    QComboBox,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    Qt,
    QVBoxLayout,
    QWidget,
)

from ..pipeline.provider_endpoint_safety import (
    DEFAULT_OFFICIAL_PROVIDER_HOSTS,
    assess_provider_endpoint,
    endpoint_confirmation_key,
)
from .beginner_ai_card_drafts import BeginnerAIProviderRuntimeSettings
from .product_i18n import DEFAULT_PRODUCT_LANGUAGE, product_text
from .style_tokens import (
    FORM_LABEL_WIDTH,
    FORM_ROW_GAP as ROW_GAP,
    INPUT_HEIGHT as CONTROL_HEIGHT,
    SPACING_LG as FORM_HORIZONTAL_GAP,
    SPACING_XS as HINT_TOP_MARGIN,
)


class _DialogTitleBar(QWidget):
    """Small draggable title bar that keeps close behavior obvious."""

    def __init__(self, dialog, title, close_text):
        super().__init__(dialog)
        self._dialog = dialog
        self._drag_offset = None
        self.setObjectName("AiSettingsTitleBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        title_label = QLabel(title)
        title_label.setObjectName("AiSettingsTitle")
        self.close_btn = QPushButton("×")
        self.close_btn.setObjectName("AiSettingsClose")
        self.close_btn.setToolTip(close_text)
        self.close_btn.setFixedSize(32, 32)
        self.close_btn.clicked.connect(dialog.reject)
        layout.addWidget(title_label)
        layout.addStretch()
        layout.addWidget(self.close_btn)

    @staticmethod
    def _global_position(event):
        if hasattr(event, "globalPosition"):
            return event.globalPosition().toPoint()
        return event.globalPos()

    def mousePressEvent(self, event):
        left_button = (
            Qt.MouseButton.LeftButton
            if hasattr(Qt, "MouseButton")
            else Qt.LeftButton
        )
        if event.button() == left_button:
            self._drag_offset = self._global_position(event) - self._dialog.pos()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        left_button = (
            Qt.MouseButton.LeftButton
            if hasattr(Qt, "MouseButton")
            else Qt.LeftButton
        )
        if self._drag_offset is not None and event.buttons() & left_button:
            self._dialog.move(self._global_position(event) - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
        super().mouseReleaseEvent(event)


class AiSettingsDialog(QDialog):
    """Edit one in-memory provider configuration without persistence."""

    PROVIDERS = (
        ("DeepSeek", "https://api.deepseek.com", "deepseek-v4-flash"),
        ("OpenAI", "https://api.openai.com/v1", "gpt-4o-mini"),
        ("OpenAI-compatible", "", ""),
    )

    def __init__(
        self,
        parent=None,
        language=DEFAULT_PRODUCT_LANGUAGE,
        settings=None,
        confirmed_endpoint_keys=(),
    ):
        super().__init__(parent)
        self.language = language
        self._accepted_settings = None
        self._accepted_endpoint_confirmation_key = None
        self._confirmed_endpoint_keys = frozenset(confirmed_endpoint_keys)
        self.setObjectName("AiSettingsDialog")
        self.setModal(True)
        self.setFixedWidth(480)
        self._configure_window()
        self._build_ui()
        self._load_settings(settings)

    def t(self, key, **values):
        return product_text(self.language, key, **values)

    def _configure_window(self):
        window_type = getattr(Qt, "WindowType", Qt)
        self.setWindowFlags(
            window_type.FramelessWindowHint | window_type.Dialog
        )
        widget_attribute = getattr(Qt, "WidgetAttribute", Qt)
        translucent = getattr(
            widget_attribute,
            "WA_TranslucentBackground",
            None,
        )
        if translucent is not None:
            self.setAttribute(translucent, True)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)

        self.surface = QFrame()
        self.surface.setObjectName("AiSettingsSurface")
        layout = QVBoxLayout(self.surface)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(ROW_GAP)
        outer.addWidget(self.surface)

        self.title_bar = _DialogTitleBar(
            self,
            self.t("ai_settings"),
            self.t("close"),
        )
        layout.addWidget(self.title_bar)

        self.provider_combo = QComboBox()
        for provider in self.PROVIDERS:
            self.provider_combo.addItem(provider[0], provider)
        self.provider_combo.currentIndexChanged.connect(
            self._on_provider_changed
        )
        layout.addLayout(
            self._make_form_row(
                self.t("provider"),
                self.provider_combo,
            )
        )

        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText(self.t("model_placeholder"))
        layout.addLayout(
            self._make_form_row(self.t("model"), self.model_input)
        )

        self.api_key_input = QLineEdit()
        password_mode = (
            QLineEdit.EchoMode.Password
            if hasattr(QLineEdit, "EchoMode")
            else QLineEdit.Password
        )
        self.api_key_input.setEchoMode(password_mode)
        self.api_key_input.setPlaceholderText(self.t("api_key_placeholder"))
        api_key_field = QWidget()
        api_key_layout = QVBoxLayout(api_key_field)
        api_key_layout.setContentsMargins(0, 0, 0, 0)
        api_key_layout.setSpacing(HINT_TOP_MARGIN)
        api_key_layout.addWidget(self.api_key_input)
        self.api_key_help_label = QLabel(self.t("api_key_help"))
        self.api_key_help_label.setProperty("role", "muted")
        api_key_layout.addWidget(self.api_key_help_label)
        layout.addLayout(
            self._make_form_row(self.t("api_key"), api_key_field)
        )

        self.connection_container = QWidget()
        connection_layout = QVBoxLayout(self.connection_container)
        connection_layout.setContentsMargins(0, 0, 0, 0)
        connection_layout.setSpacing(ROW_GAP)
        self.base_url_input = QLineEdit()
        connection_layout.addLayout(
            self._make_form_row(self.t("base_url"), self.base_url_input)
        )
        self.timeout_input = QSpinBox()
        self.timeout_input.setRange(1, 300)
        self.timeout_input.setValue(60)
        connection_layout.addLayout(
            self._make_form_row(self.t("timeout"), self.timeout_input)
        )
        self.connection_container.setVisible(False)
        layout.addWidget(self.connection_container)

        self.error_label = QLabel()
        self.error_label.setProperty("role", "error")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.cancel_btn = QPushButton(self.t("cancel"))
        self.cancel_btn.setProperty("role", "dialogSecondary")
        self.cancel_btn.setMinimumHeight(36)
        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn = QPushButton(self.t("save_session_settings"))
        self.save_btn.setProperty("role", "dialogPrimary")
        self.save_btn.setMinimumHeight(36)
        self.save_btn.clicked.connect(self._save)
        buttons.addWidget(self.cancel_btn)
        buttons.addWidget(self.save_btn)
        layout.addLayout(buttons)

        try:
            shadow = QGraphicsDropShadowEffect(self.surface)
            shadow.setBlurRadius(28)
            shadow.setOffset(0, 8)
            shadow.setColor(QColor(0, 0, 0, 120))
            self.surface.setGraphicsEffect(shadow)
        except (AttributeError, RuntimeError):
            pass

    @staticmethod
    def _configure_control(widget):
        widget.setMinimumHeight(CONTROL_HEIGHT)
        return widget

    def _make_form_row(self, label_text, control):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(FORM_HORIZONTAL_GAP)
        label = QLabel(label_text)
        label.setProperty("role", "fieldLabel")
        label.setFixedWidth(FORM_LABEL_WIDTH)
        label.setMinimumHeight(CONTROL_HEIGHT)
        label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self._configure_control(control)
        row.addWidget(label, 0, Qt.AlignmentFlag.AlignTop)
        row.addWidget(control, 1, Qt.AlignmentFlag.AlignTop)
        return row

    def _load_settings(self, settings):
        if settings is None:
            self.provider_combo.setCurrentIndex(0)
            self.model_input.setText(self.PROVIDERS[0][2])
            self.base_url_input.setText(self.PROVIDERS[0][1])
            self.api_key_input.clear()
            self.timeout_input.setValue(60)
            self._on_provider_changed(0)
            return
        if not isinstance(settings, BeginnerAIProviderRuntimeSettings):
            raise TypeError(
                "settings must be BeginnerAIProviderRuntimeSettings or None"
            )
        provider_index = next(
            (
                index
                for index, provider in enumerate(self.PROVIDERS)
                if provider[0] == settings.provider_name
            ),
            2,
        )
        self.provider_combo.setCurrentIndex(provider_index)
        self.model_input.setText(settings.model)
        self.api_key_input.setText(settings.api_key)
        self.base_url_input.setText(settings.base_url)
        self.timeout_input.setValue(int(settings.timeout_seconds))
        self._on_provider_changed(provider_index, preserve_values=True)

    def _on_provider_changed(self, _index, preserve_values=False):
        provider_name, base_url, suggested_model = (
            self.provider_combo.currentData()
        )
        self.connection_container.setVisible(
            provider_name == "OpenAI-compatible"
        )
        if preserve_values:
            return
        previous_model = self.model_input.text().strip()
        if previous_model in {"", "deepseek-v4-flash", "gpt-4o-mini"}:
            self.model_input.setText(suggested_model)
        self.base_url_input.setText(base_url)
        self.error_label.clear()
        self.error_label.setVisible(False)

    def _save(self):
        provider_name, preset_url, _suggested_model = (
            self.provider_combo.currentData()
        )
        base_url = (self.base_url_input.text() or preset_url).strip()
        try:
            settings = BeginnerAIProviderRuntimeSettings(
                provider_name=provider_name,
                base_url=base_url,
                model=self.model_input.text().strip(),
                api_key=self.api_key_input.text().strip(),
                timeout_seconds=self.timeout_input.value(),
            )
        except ValueError:
            self.error_label.setText(self.t("ai_settings_invalid"))
            self.error_label.setVisible(True)
            return
        decision = assess_provider_endpoint(
            base_url,
            official_hosts=DEFAULT_OFFICIAL_PROVIDER_HOSTS,
        )
        if decision.kind == "deny":
            self.error_label.setText(
                decision.user_message_zh
                if self.language == "zh"
                else decision.user_message_en
            )
            self.error_label.setVisible(True)
            return
        confirmation_key = None
        if decision.kind == "confirm":
            confirmation_key = endpoint_confirmation_key(base_url)
            if confirmation_key not in self._confirmed_endpoint_keys:
                buttons = getattr(QMessageBox, "StandardButton", QMessageBox)
                message = (
                    decision.user_message_zh
                    if self.language == "zh"
                    else decision.user_message_en
                )
                answer = QMessageBox.question(
                    self,
                    self.t("ai_settings"),
                    f"{message}\n\n{decision.display_endpoint}",
                    buttons.Yes | buttons.No,
                    buttons.No,
                )
                confirmed = answer == buttons.Yes
                if not confirmed:
                    return
        self._accepted_settings = settings
        self._accepted_endpoint_confirmation_key = confirmation_key
        self.accept()

    def runtime_settings(self):
        return self._accepted_settings

    def endpoint_confirmation_key(self):
        return self._accepted_endpoint_confirmation_key

    def clear_sensitive_data(self):
        self.api_key_input.clear()
        self._accepted_settings = None
        self._accepted_endpoint_confirmation_key = None

    def reject(self):
        self.clear_sensitive_data()
        super().reject()

    def keyPressEvent(self, event):
        key_escape = (
            Qt.Key.Key_Escape if hasattr(Qt, "Key") else Qt.Key_Escape
        )
        if event.key() == key_escape:
            self.reject()
            return
        super().keyPressEvent(event)
