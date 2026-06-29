"""Qt renderer for the new pipeline's read-only provider preview."""

from aqt.qt import (
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .provider_preview_helpers import build_provider_preview_view_data


class ReadOnlyProviderPreviewDialog(QDialog):
    """Display an injected safe projection without settings or execution controls."""

    def __init__(self, preview=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新 Pipeline Provider 只读预览")
        self.resize(760, 600)

        view_data = build_provider_preview_view_data(preview)
        layout = QVBoxLayout(self)

        notice = QLabel(
            "只读预览：不保存设置、不发送资料、不生成卡片、不写入 Anki。"
        )
        notice.setWordWrap(True)
        notice.setStyleSheet("font-weight: bold;")
        layout.addWidget(notice)

        if view_data.is_empty:
            empty_label = QLabel(view_data.empty_state_message)
            empty_label.setWordWrap(True)
            layout.addWidget(empty_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)

        self._add_rows(content_layout, "Provider 安全信息", view_data.provider_rows)
        self._add_rows(content_layout, "安全边界", view_data.safety_rows)
        self._add_rows(content_layout, "Dry-run 摘要", view_data.dry_run_rows)

        if view_data.source_excerpt_preview:
            excerpt_group = QGroupBox("将发送的短预览（只读，最多 500 字符）")
            excerpt_layout = QVBoxLayout(excerpt_group)
            excerpt_label = QLabel(view_data.source_excerpt_preview)
            excerpt_label.setWordWrap(True)
            excerpt_layout.addWidget(excerpt_label)
            content_layout.addWidget(excerpt_group)

        self._add_rows(content_layout, "安全错误信息", view_data.error_rows)
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        button_row = QHBoxLayout()
        button_row.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        button_row.addWidget(close_btn)
        layout.addLayout(button_row)

    @staticmethod
    def _add_rows(parent_layout, title, rows):
        if not rows:
            return
        group = QGroupBox(title)
        form = QFormLayout(group)
        for row in rows:
            value_label = QLabel(row.value)
            value_label.setWordWrap(True)
            form.addRow(f"{row.label}:", value_label)
        parent_layout.addWidget(group)
