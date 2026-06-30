"""Qt editor for non-persistent Human Review decision drafts."""

from aqt.qt import (
    QApplication,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..pipeline.card_candidate_preview_adapter import CardCandidatePreviewItem
from .human_review_draft_helpers import (
    HumanReviewDecisionDraftInput,
    allowed_human_review_draft_decisions,
    build_human_review_decision_draft_view_data,
)


class HumanReviewDecisionDraftDialog(QDialog):
    """Edit local review drafts that disappear when this dialog closes."""

    def __init__(self, preview_items=None, parent=None):
        super().__init__(parent)
        self._preview_items = tuple(preview_items or ())
        if not all(
            isinstance(item, CardCandidatePreviewItem)
            for item in self._preview_items
        ):
            raise ValueError("preview_items must contain CardCandidatePreviewItem values.")
        candidate_ids = tuple(item.candidate_id for item in self._preview_items)
        if len(set(candidate_ids)) != len(candidate_ids):
            raise ValueError("preview_items must have unique candidate IDs.")

        self._drafts = {}
        self.setWindowTitle("Human Review 决策草稿")
        self._set_screen_bounded_size()

        layout = QVBoxLayout(self)
        notice = QLabel(
            "仅审核草稿；尚未形成正式 HumanReview；尚未计算写入授权；"
            "不生成 GeneratedCard；不修改 legacy 候选卡；不调用 writer；"
            "不写入 Anki；关闭后丢弃。"
        )
        notice.setWordWrap(True)
        notice.setStyleSheet("font-weight: bold;")
        layout.addWidget(notice)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)

        editor_group = QGroupBox("当前本地审核草稿")
        editor_form = QFormLayout(editor_group)
        self.candidate_combo = QComboBox()
        self.candidate_combo.addItems(candidate_ids)
        self.candidate_combo.currentIndexChanged.connect(
            self._on_candidate_changed
        )
        editor_form.addRow("Candidate:", self.candidate_combo)
        self.decision_combo = QComboBox()
        editor_form.addRow("Decision:", self.decision_combo)
        self.reviewer_note_input = QTextEdit()
        self.reviewer_note_input.setFixedHeight(100)
        editor_form.addRow("Reviewer note（仅本地）:", self.reviewer_note_input)
        content_layout.addWidget(editor_group)

        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        content_layout.addWidget(self.summary_label)

        candidate_group = QGroupBox("CardCandidate 安全摘要")
        self.candidate_form = QFormLayout(candidate_group)
        content_layout.addWidget(candidate_group)

        quality_group = QGroupBox("Quality Gate 状态与 Issues")
        self.quality_form = QFormLayout(quality_group)
        content_layout.addWidget(quality_group)

        safety_group = QGroupBox("审核草稿安全边界")
        self.safety_form = QFormLayout(safety_group)
        content_layout.addWidget(safety_group)
        content_layout.addStretch()

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area, 1)

        button_row = QHBoxLayout()
        button_row.addStretch()
        self.update_btn = QPushButton("更新审核草稿（仅本地）")
        self.update_btn.clicked.connect(self.update_local_draft)
        button_row.addWidget(self.update_btn)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.reject)
        button_row.addWidget(close_btn)
        layout.addLayout(button_row)

        self._on_candidate_changed(self.candidate_combo.currentIndex())

    def _set_screen_bounded_size(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            self.resize(920, 680)
            self.setMaximumHeight(720)
            return
        available = screen.availableGeometry()
        self.resize(
            min(920, max(1, available.width() - 80)),
            min(680, max(1, available.height() - 80)),
        )
        self.setMaximumHeight(available.height())

    def _on_candidate_changed(self, _index):
        candidate = self._current_candidate()
        if candidate is None:
            self.candidate_combo.setEnabled(False)
            self.decision_combo.setEnabled(False)
            self.reviewer_note_input.setEnabled(False)
            self.update_btn.setEnabled(False)
            self._render_view(
                build_human_review_decision_draft_view_data(None)
            )
            return

        stored = self._drafts.get(
            candidate.candidate_id,
            HumanReviewDecisionDraftInput(candidate_id=candidate.candidate_id),
        )
        view_data = build_human_review_decision_draft_view_data(candidate, stored)
        self._set_decision_choices(view_data, stored.decision)
        self.reviewer_note_input.setPlainText(stored.reviewer_note)
        self._render_view(view_data)

    def update_local_draft(self):
        candidate = self._current_candidate()
        if candidate is None:
            return
        draft = HumanReviewDecisionDraftInput(
            candidate_id=candidate.candidate_id,
            decision=self.decision_combo.currentText(),
            reviewer_note=self.reviewer_note_input.toPlainText(),
        )
        view_data = build_human_review_decision_draft_view_data(candidate, draft)
        if view_data.is_valid:
            self._drafts[candidate.candidate_id] = draft
        self._render_view(view_data)

    def _set_decision_choices(self, view_data, selected):
        decisions = allowed_human_review_draft_decisions(view_data)
        self.decision_combo.blockSignals(True)
        self.decision_combo.clear()
        self.decision_combo.addItems(decisions)
        self.decision_combo.setCurrentText(
            selected if selected in decisions else "pending"
        )
        self.decision_combo.blockSignals(False)

    def _render_view(self, view_data):
        self._clear_form(self.candidate_form)
        self._clear_form(self.quality_form)
        self._clear_form(self.safety_form)
        message = view_data.summary_message
        if view_data.validation_errors:
            message += "\n" + "\n".join(
                f"• {error}" for error in view_data.validation_errors
            )
        self.summary_label.setText(message)
        self._add_rows(self.candidate_form, view_data.candidate_rows)
        self._add_rows(self.quality_form, view_data.quality_rows)
        self._add_rows(self.safety_form, view_data.safety_rows)

    def _current_candidate(self):
        index = self.candidate_combo.currentIndex()
        if index < 0 or index >= len(self._preview_items):
            return None
        return self._preview_items[index]

    @staticmethod
    def _add_rows(form, rows):
        for row in rows:
            value_label = QLabel(row.value)
            value_label.setWordWrap(True)
            form.addRow(f"{row.label}:", value_label)

    @staticmethod
    def _clear_form(form):
        while form.count():
            item = form.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
