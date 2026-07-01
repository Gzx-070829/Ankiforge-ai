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
from .human_review_preview_adapter import build_local_human_review_preview
from .write_eligibility_preview_adapter import build_write_eligibility_preview
from .write_plan_preview_adapter import build_read_only_write_plan_preview


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

        self.local_preview_group = QGroupBox("本地 HumanReview 预览（不写入）")
        local_preview_layout = QVBoxLayout(self.local_preview_group)
        self.local_preview_summary_label = QLabel()
        self.local_preview_summary_label.setWordWrap(True)
        local_preview_layout.addWidget(self.local_preview_summary_label)
        self.local_preview_form = QFormLayout()
        local_preview_layout.addLayout(self.local_preview_form)
        self.local_preview_group.setVisible(False)
        content_layout.addWidget(self.local_preview_group)

        self.eligibility_group = QGroupBox(
            "Write Eligibility 只读摘要（不写入）"
        )
        eligibility_layout = QVBoxLayout(self.eligibility_group)
        self.eligibility_summary_label = QLabel()
        self.eligibility_summary_label.setWordWrap(True)
        eligibility_layout.addWidget(self.eligibility_summary_label)
        self.eligibility_form = QFormLayout()
        eligibility_layout.addLayout(self.eligibility_form)
        self.eligibility_group.setVisible(False)
        content_layout.addWidget(self.eligibility_group)

        self.write_plan_group = QGroupBox("只读 Write Plan 预览（不写入）")
        write_plan_layout = QVBoxLayout(self.write_plan_group)
        self.write_plan_summary_label = QLabel()
        self.write_plan_summary_label.setWordWrap(True)
        write_plan_layout.addWidget(self.write_plan_summary_label)
        self.write_plan_form = QFormLayout()
        write_plan_layout.addLayout(self.write_plan_form)
        self.write_plan_group.setVisible(False)
        content_layout.addWidget(self.write_plan_group)
        content_layout.addStretch()

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area, 1)

        button_row = QHBoxLayout()
        button_row.addStretch()
        self.update_btn = QPushButton("更新审核草稿（仅本地）")
        self.update_btn.clicked.connect(self.update_local_draft)
        button_row.addWidget(self.update_btn)
        self.preview_btn = QPushButton("生成本地 HumanReview 预览（不写入）")
        self.preview_btn.clicked.connect(self.generate_local_human_review_preview)
        button_row.addWidget(self.preview_btn)
        layout.addLayout(button_row)

        advanced_button_row = QHBoxLayout()
        advanced_button_row.addStretch()
        self.eligibility_btn = QPushButton(
            "生成 Write Eligibility 只读摘要（不写入）"
        )
        self.eligibility_btn.clicked.connect(
            self.generate_write_eligibility_preview
        )
        advanced_button_row.addWidget(self.eligibility_btn)
        self.write_plan_btn = QPushButton("生成只读 Write Plan 预览（不写入）")
        self.write_plan_btn.clicked.connect(self.generate_read_only_write_plan_preview)
        advanced_button_row.addWidget(self.write_plan_btn)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.reject)
        advanced_button_row.addWidget(close_btn)
        layout.addLayout(advanced_button_row)

        self.decision_combo.currentTextChanged.connect(
            self._on_draft_widget_changed
        )
        self.reviewer_note_input.textChanged.connect(
            self._on_draft_widget_changed
        )

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
            self.preview_btn.setEnabled(False)
            self.eligibility_btn.setEnabled(False)
            self.write_plan_btn.setEnabled(False)
            self._render_view(
                build_human_review_decision_draft_view_data(None)
            )
            self._render_local_human_review_preview(None)
            self._render_write_eligibility_preview(None)
            self._render_write_plan_preview(None)
            return

        stored = self._drafts.get(
            candidate.candidate_id,
            HumanReviewDecisionDraftInput(candidate_id=candidate.candidate_id),
        )
        view_data = build_human_review_decision_draft_view_data(candidate, stored)
        self._set_decision_choices(view_data, stored.decision)
        self.reviewer_note_input.setPlainText(stored.reviewer_note)
        self._render_view(view_data)
        self._render_local_human_review_preview(None)
        self._render_write_eligibility_preview(None)
        self._render_write_plan_preview(None)

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
        self._render_local_human_review_preview(None)
        self._render_write_eligibility_preview(None)
        self._render_write_plan_preview(None)

    def generate_local_human_review_preview(self):
        candidate = self._current_candidate()
        if candidate is None:
            return
        draft = HumanReviewDecisionDraftInput(
            candidate_id=candidate.candidate_id,
            decision=self.decision_combo.currentText(),
            reviewer_note=self.reviewer_note_input.toPlainText(),
        )
        view_data = build_human_review_decision_draft_view_data(candidate, draft)
        preview = build_local_human_review_preview(view_data, draft)
        if view_data.is_valid:
            self._drafts[candidate.candidate_id] = draft
        self._render_view(view_data)
        self._render_local_human_review_preview(preview)
        self._render_write_eligibility_preview(None)
        self._render_write_plan_preview(None)

    def generate_write_eligibility_preview(self):
        candidate = self._current_candidate()
        if candidate is None:
            return
        draft = HumanReviewDecisionDraftInput(
            candidate_id=candidate.candidate_id,
            decision=self.decision_combo.currentText(),
            reviewer_note=self.reviewer_note_input.toPlainText(),
        )
        view_data = build_human_review_decision_draft_view_data(candidate, draft)
        review_preview = build_local_human_review_preview(view_data, draft)
        eligibility = build_write_eligibility_preview(review_preview)
        if view_data.is_valid:
            self._drafts[candidate.candidate_id] = draft
        self._render_view(view_data)
        self._render_local_human_review_preview(review_preview)
        self._render_write_eligibility_preview(eligibility)
        self._render_write_plan_preview(None)

    def generate_read_only_write_plan_preview(self):
        candidate = self._current_candidate()
        if candidate is None:
            return
        draft = HumanReviewDecisionDraftInput(
            candidate_id=candidate.candidate_id,
            decision=self.decision_combo.currentText(),
            reviewer_note=self.reviewer_note_input.toPlainText(),
        )
        view_data = build_human_review_decision_draft_view_data(candidate, draft)
        review_preview = build_local_human_review_preview(view_data, draft)
        eligibility = build_write_eligibility_preview(review_preview)
        write_plan = build_read_only_write_plan_preview(eligibility)
        if view_data.is_valid:
            self._drafts[candidate.candidate_id] = draft
        self._render_view(view_data)
        self._render_local_human_review_preview(review_preview)
        self._render_write_eligibility_preview(eligibility)
        self._render_write_plan_preview(write_plan)

    def _on_draft_widget_changed(self, *_args):
        self._render_local_human_review_preview(None)
        self._render_write_eligibility_preview(None)
        self._render_write_plan_preview(None)

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

    def _render_local_human_review_preview(self, preview):
        self._clear_form(self.local_preview_form)
        if preview is None:
            self.local_preview_summary_label.clear()
            self.local_preview_group.setVisible(False)
            return

        if preview.validation_errors:
            summary = "本地 HumanReview 预览无效。\n" + "\n".join(
                f"• {error}" for error in preview.validation_errors
            )
        else:
            summary = "这是本地 HumanReview 预览；不会形成写入授权。"
        self.local_preview_summary_label.setText(summary)
        values = (
            ("Candidate ID", preview.candidate_id),
            ("Review decision", preview.review_decision),
            ("Reviewer note excerpt", preview.reviewer_note_excerpt or "（空）"),
            ("Reviewer note length", str(preview.reviewer_note_length)),
            ("Quality status", preview.quality_status),
            ("Locally valid", "是" if preview.is_locally_valid else "否"),
        )
        for label, value in values:
            value_label = QLabel(value)
            value_label.setWordWrap(True)
            self.local_preview_form.addRow(f"{label}:", value_label)
        self._add_rows(self.local_preview_form, preview.safety_rows)
        self.local_preview_group.setVisible(True)

    def _render_write_eligibility_preview(self, preview):
        self._clear_form(self.eligibility_form)
        if preview is None:
            self.eligibility_summary_label.clear()
            self.eligibility_group.setVisible(False)
            return

        self.eligibility_summary_label.setText(preview.summary_message)
        reasons = ", ".join(preview.blocking_reasons) or "无"
        values = (
            ("Candidate ID", preview.candidate_id or "（无）"),
            ("Review decision", preview.review_decision or "（无）"),
            ("Quality status", preview.quality_status or "（未知）"),
            ("Review valid", "是" if preview.review_valid else "否"),
            ("Eligibility status", preview.eligibility_status),
            ("Blocking reasons", reasons),
        )
        for label, value in values:
            value_label = QLabel(value)
            value_label.setWordWrap(True)
            self.eligibility_form.addRow(f"{label}:", value_label)
        self._add_rows(self.eligibility_form, preview.safety_rows)
        self.eligibility_group.setVisible(True)

    def _render_write_plan_preview(self, preview):
        self._clear_form(self.write_plan_form)
        if preview is None:
            self.write_plan_summary_label.clear()
            self.write_plan_group.setVisible(False)
            return

        self.write_plan_summary_label.setText(preview.summary_message)
        reasons = ", ".join(preview.blocking_reasons) or "无"
        mappings = ", ".join(
            f"{item.source_field} -> {item.target_field}"
            for item in preview.field_mappings
        )
        values = (
            ("Candidate ID", preview.candidate_id or "（无）"),
            ("Eligibility status", preview.eligibility_status),
            ("Review decision", preview.review_decision or "（无）"),
            ("Quality status", preview.quality_status or "（未知）"),
            ("Plan status", preview.plan_status),
            ("Blocking reasons", reasons),
            ("Target note type", preview.target_note_type_preview),
            ("Target deck", preview.target_deck_preview),
            ("Field mapping", mappings),
            ("Tag preview", " ".join(preview.tag_preview)),
        )
        for label, value in values:
            value_label = QLabel(value)
            value_label.setWordWrap(True)
            self.write_plan_form.addRow(f"{label}:", value_label)
        self._add_rows(self.write_plan_form, preview.safety_rows)
        self.write_plan_group.setVisible(True)

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
