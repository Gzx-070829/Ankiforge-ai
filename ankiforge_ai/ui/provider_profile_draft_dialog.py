"""Qt editor for one non-persistent, non-sensitive provider profile draft."""

from aqt.qt import (
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from .provider_profile_draft_helpers import (
    PROVIDER_PROFILE_DRAFT_TARGET_STAGE,
    ProviderProfileDraftInput,
    build_provider_profile_draft_view_data,
)
from .provider_profile_draft_preview_adapter import (
    build_provider_profile_draft_read_only_preview,
)


class ProviderProfileDraftDialog(QDialog):
    """Edit and preview a draft that is discarded when the dialog closes."""

    def __init__(self, draft=None, parent=None):
        super().__init__(parent)
        if draft is not None and not isinstance(draft, ProviderProfileDraftInput):
            raise ValueError("draft must be ProviderProfileDraftInput or None.")

        initial = draft or ProviderProfileDraftInput()
        self.setWindowTitle("新 Pipeline Provider 本地草稿预览")
        self.resize(760, 620)

        layout = QVBoxLayout(self)
        notice = QLabel(
            "仅本地草稿：不保存设置；不接收 API key；不发送资料；"
            "不调用 provider；不生成卡片；不写入 Anki；关闭后丢弃。"
        )
        notice.setWordWrap(True)
        notice.setStyleSheet("font-weight: bold;")
        layout.addWidget(notice)

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
        layout.addWidget(form_group)

        preview_group = QGroupBox("Provider 安全信息")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_status_label = QLabel()
        self.preview_status_label.setWordWrap(True)
        preview_layout.addWidget(self.preview_status_label)
        self.profile_preview_form = QFormLayout()
        preview_layout.addLayout(self.profile_preview_form)
        layout.addWidget(preview_group)

        safety_group = QGroupBox("草稿安全状态")
        self.safety_form = QFormLayout(safety_group)
        layout.addWidget(safety_group)

        button_row = QHBoxLayout()
        button_row.addStretch()
        update_btn = QPushButton("更新本地预览（仅本地）")
        update_btn.clicked.connect(self.update_local_preview)
        button_row.addWidget(update_btn)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.reject)
        button_row.addWidget(close_btn)
        layout.addLayout(button_row)

        self._render_read_only_preview(
            self._adapt_draft_for_preview(initial)
        )

    def update_local_preview(self):
        draft = ProviderProfileDraftInput(
            provider=self.provider_input.text(),
            model=self.model_input.text(),
            base_url=self.base_url_input.text(),
            privacy_notice=self.privacy_notice_input.toPlainText(),
        )
        self._render_read_only_preview(
            self._adapt_draft_for_preview(draft)
        )

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

    @staticmethod
    def _clear_form(form):
        while form.count():
            item = form.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
