"""Qt editor for one non-persistent, non-sensitive provider profile draft."""

from aqt.qt import (
    QApplication,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .provider_profile_draft_helpers import (
    PROVIDER_PROFILE_DRAFT_TARGET_STAGE,
    ProviderProfileDraftInput,
    build_provider_profile_draft_view_data,
)
from .provider_profile_draft_preview_adapter import (
    build_provider_profile_draft_read_only_preview,
)
from .provider_profile_draft_disclosure_adapter import (
    build_provider_profile_draft_send_disclosure,
)


class ProviderProfileDraftDialog(QDialog):
    """Edit and preview a draft that is discarded when the dialog closes."""

    def __init__(self, draft=None, parent=None):
        super().__init__(parent)
        if draft is not None and not isinstance(draft, ProviderProfileDraftInput):
            raise ValueError("draft must be ProviderProfileDraftInput or None.")

        initial = draft or ProviderProfileDraftInput()
        self.setWindowTitle("新 Pipeline Provider 本地草稿预览")
        self._set_screen_bounded_size()

        layout = QVBoxLayout(self)
        notice = QLabel(
            "仅本地草稿：不保存设置；不接收 API key；不发送资料；"
            "不调用 provider；不生成卡片；不写入 Anki；关闭后丢弃。"
        )
        notice.setWordWrap(True)
        notice.setStyleSheet("font-weight: bold;")
        layout.addWidget(notice)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)

        form_group = QGroupBox("非敏感 Provider 草稿")
        form = QFormLayout(form_group)

        self.provider_input = QLineEdit(initial.provider)
        form.addRow("Provider:", self.provider_input)

        self.model_input = QLineEdit(initial.model)
        form.addRow("Model:", self.model_input)

        self.base_url_input = QLineEdit(initial.base_url)
        form.addRow("Base URL:", self.base_url_input)

        self.privacy_notice_input = QTextEdit()
        self.privacy_notice_input.setPlainText(initial.privacy_notice)
        self.privacy_notice_input.setFixedHeight(100)
        form.addRow("Privacy notice:", self.privacy_notice_input)

        target_stage_label = QLabel(PROVIDER_PROFILE_DRAFT_TARGET_STAGE)
        target_stage_label.setStyleSheet("font-family: monospace;")
        form.addRow("Target stage（固定）:", target_stage_label)
        content_layout.addWidget(form_group)

        preview_group = QGroupBox("Provider 安全信息")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_status_label = QLabel()
        self.preview_status_label.setWordWrap(True)
        preview_layout.addWidget(self.preview_status_label)
        self.profile_preview_form = QFormLayout()
        preview_layout.addLayout(self.profile_preview_form)
        content_layout.addWidget(preview_group)

        safety_group = QGroupBox("草稿安全状态")
        self.safety_form = QFormLayout(safety_group)
        content_layout.addWidget(safety_group)

        self.disclosure_group = QGroupBox("未来发送披露（仅说明，不授权）")
        disclosure_layout = QVBoxLayout(self.disclosure_group)
        self.disclosure_summary_label = QLabel()
        self.disclosure_summary_label.setWordWrap(True)
        self.disclosure_summary_label.setStyleSheet("font-weight: bold;")
        disclosure_layout.addWidget(self.disclosure_summary_label)

        current_group = QGroupBox("当前本地操作")
        self.current_disclosure_form = QFormLayout(current_group)
        disclosure_layout.addWidget(current_group)

        future_group = QGroupBox("未来真实 Provider 流程")
        self.future_disclosure_form = QFormLayout(future_group)
        disclosure_layout.addWidget(future_group)
        self.disclosure_group.setVisible(False)
        content_layout.addWidget(self.disclosure_group)
        content_layout.addStretch()

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area, 1)

        button_row = QHBoxLayout()
        button_row.addStretch()
        update_btn = QPushButton("更新本地预览（仅本地）")
        update_btn.clicked.connect(self.update_local_preview)
        button_row.addWidget(update_btn)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.reject)
        button_row.addWidget(close_btn)
        layout.addLayout(button_row)

        self._render_draft(initial)

    def _set_screen_bounded_size(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            self.resize(900, 680)
            self.setMaximumHeight(720)
            return

        available = screen.availableGeometry()
        width = min(900, max(1, available.width() - 80))
        height = min(680, max(1, available.height() - 80))
        self.resize(width, height)
        self.setMaximumHeight(available.height())

    def update_local_preview(self):
        draft = ProviderProfileDraftInput(
            provider=self.provider_input.text(),
            model=self.model_input.text(),
            base_url=self.base_url_input.text(),
            privacy_notice=self.privacy_notice_input.toPlainText(),
        )
        self._render_draft(draft)

    def _render_draft(self, draft):
        preview = self._adapt_draft_for_preview(draft)
        disclosure = build_provider_profile_draft_send_disclosure(preview)
        self._render_read_only_preview(preview)
        self._render_send_disclosure(disclosure)

    @staticmethod
    def _adapt_draft_for_preview(draft):
        view_data = build_provider_profile_draft_view_data(draft)
        return build_provider_profile_draft_read_only_preview(view_data)

    def _render_read_only_preview(self, preview):
        self._clear_form(self.profile_preview_form)
        self._clear_form(self.safety_form)

        if preview.validation_errors:
            self.preview_status_label.setText(
                preview.summary_message
                + "\n"
                + "\n".join(
                    f"• {error.message}" for error in preview.validation_errors
                )
            )
        else:
            self.preview_status_label.setText(preview.summary_message)

        for row in preview.provider_rows:
            value_label = QLabel(row.value)
            value_label.setWordWrap(True)
            self.profile_preview_form.addRow(f"{row.label}:", value_label)
        for row in preview.status_rows:
            value_label = QLabel(row.value)
            value_label.setWordWrap(True)
            self.safety_form.addRow(f"{row.label}:", value_label)

    def _render_send_disclosure(self, disclosure):
        self._clear_form(self.current_disclosure_form)
        self._clear_form(self.future_disclosure_form)
        if disclosure is None:
            self.disclosure_summary_label.clear()
            self.disclosure_group.setVisible(False)
            return

        self.disclosure_summary_label.setText(disclosure.summary_message)
        for row in disclosure.current_rows:
            value_label = QLabel(row.value)
            value_label.setWordWrap(True)
            self.current_disclosure_form.addRow(f"{row.label}:", value_label)
        for row in disclosure.future_rows:
            value_label = QLabel(row.value)
            value_label.setWordWrap(True)
            self.future_disclosure_form.addRow(f"{row.label}:", value_label)
        self.disclosure_group.setVisible(True)

    @staticmethod
    def _clear_form(form):
        while form.count():
            item = form.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
