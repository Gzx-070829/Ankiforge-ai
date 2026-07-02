"""In-memory Qt guide for the beginner mode."""

from aqt.qt import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
)

from .beginner_flow_models import (
    BEGINNER_FLOW_STEP_ORDER,
    BEGINNER_FUTURE_CONDITIONS,
    BEGINNER_GUIDE_SAFETY_COPY,
    BEGINNER_GUIDE_STEP_NOTES,
    BEGINNER_MATERIAL_EMPTY_HINT,
    BEGINNER_PREWRITE_SUMMARY,
    BEGINNER_REVIEW_DECISION_COPY,
    BEGINNER_REVIEW_SAFETY_NOTE,
    BEGINNER_STEP_COPY,
    BEGINNER_TECHNICAL_DETAILS_COPY,
    COMPLETION_TITLE,
    BeginnerFlowSession,
    BeginnerFlowStep,
    BeginnerReviewDecision,
)


class BeginnerModeDialog(QDialog):
    """Guide one disposable session without starting pipeline work."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.session = BeginnerFlowSession()
        self.setWindowTitle("新手模式（离线只读演练）")
        self.resize(760, 680)

        layout = QVBoxLayout(self)

        welcome_group = QGroupBox("欢迎使用新手模式")
        welcome_layout = QVBoxLayout(welcome_group)
        welcome = QLabel(
            "这里会带你看懂从学习材料到候选卡审核的五步流程。"
            "你可以输入自己的材料，所有内容仅保留在当前窗口。"
        )
        welcome.setWordWrap(True)
        welcome_layout.addWidget(welcome)
        layout.addWidget(welcome_group)

        safety_group = QGroupBox("离线只读安全状态")
        safety_layout = QHBoxLayout(safety_group)
        for status in BEGINNER_GUIDE_SAFETY_COPY:
            status_label = QLabel(status)
            status_label.setWordWrap(True)
            safety_layout.addWidget(status_label)
        layout.addWidget(safety_group)

        navigation_group = QGroupBox("五步流程导航")
        navigation_layout = QHBoxLayout(navigation_group)
        self.step_labels = {}
        self.guide_steps = tuple(
            step
            for step in BEGINNER_FLOW_STEP_ORDER
            if step is not BeginnerFlowStep.COMPLETED_NO_WRITE
        )
        for index, step in enumerate(self.guide_steps, start=1):
            step_label = QLabel(f"{index}. {BEGINNER_STEP_COPY[step].title}")
            step_label.setWordWrap(True)
            self.step_labels[step] = step_label
            navigation_layout.addWidget(step_label)
        layout.addWidget(navigation_group)

        current_group = QGroupBox("当前步骤说明")
        current_layout = QVBoxLayout(current_group)
        self.current_title_label = QLabel()
        self.current_title_label.setStyleSheet("font-weight: bold;")
        self.current_description_label = QLabel()
        self.current_description_label.setWordWrap(True)
        self.current_note_label = QLabel()
        self.current_note_label.setWordWrap(True)
        current_layout.addWidget(self.current_title_label)
        current_layout.addWidget(self.current_description_label)
        current_layout.addWidget(self.current_note_label)
        layout.addWidget(current_group)

        self.material_group = QGroupBox("材料输入页")
        material_layout = QVBoxLayout(self.material_group)
        material_hint = QLabel(BEGINNER_MATERIAL_EMPTY_HINT)
        material_hint.setWordWrap(True)
        material_layout.addWidget(material_hint)
        self.material_input = QTextEdit()
        self.material_input.setPlaceholderText("在这里输入或粘贴学习材料")
        self.material_input.textChanged.connect(self._on_material_changed)
        material_layout.addWidget(self.material_input)
        material_footer = QHBoxLayout()
        self.material_count_label = QLabel("0 字符")
        self.example_material_btn = QPushButton("使用示例材料")
        self.example_material_btn.clicked.connect(self._use_example_material)
        self.clear_material_btn = QPushButton("清空材料")
        self.clear_material_btn.clicked.connect(self._clear_material)
        material_footer.addWidget(self.material_count_label)
        material_footer.addStretch()
        material_footer.addWidget(self.example_material_btn)
        material_footer.addWidget(self.clear_material_btn)
        material_layout.addLayout(material_footer)
        layout.addWidget(self.material_group)

        self.preview_group = QGroupBox("材料预览与离线识别")
        preview_layout = QVBoxLayout(self.preview_group)
        self.material_preview_label = QLabel()
        self.material_preview_label.setWordWrap(True)
        preview_layout.addWidget(self.material_preview_label)
        self.recognition_list_layout = QVBoxLayout()
        preview_layout.addLayout(self.recognition_list_layout)
        layout.addWidget(self.preview_group)

        self.knowledge_group = QGroupBox("选择要制卡的知识点")
        self.knowledge_layout = QVBoxLayout(self.knowledge_group)
        self.knowledge_checkboxes = {}
        layout.addWidget(self.knowledge_group)

        self.candidate_group = QGroupBox("审核候选卡")
        self.candidate_layout = QVBoxLayout(self.candidate_group)
        self.candidate_review_controls = {}
        self.candidate_review_button_groups = {}
        self.review_progress_label = None
        layout.addWidget(self.candidate_group)

        self.prewrite_group = QGroupBox("未来真正写入前还需要")
        prewrite_layout = QVBoxLayout(self.prewrite_group)
        prewrite_summary = QLabel(BEGINNER_PREWRITE_SUMMARY)
        prewrite_summary.setWordWrap(True)
        prewrite_layout.addWidget(prewrite_summary)
        for index, condition in enumerate(BEGINNER_FUTURE_CONDITIONS, start=1):
            condition_label = QLabel(
                f"{index}. {condition.title}｜{condition.status}\n"
                f"{condition.explanation}"
            )
            condition_label.setWordWrap(True)
            prewrite_layout.addWidget(condition_label)
        layout.addWidget(self.prewrite_group)

        self.technical_details_expanded = False
        self.technical_toggle_btn = QPushButton("查看技术详情")
        self.technical_toggle_btn.setFlat(True)
        self.technical_toggle_btn.clicked.connect(self._toggle_technical_details)
        layout.addWidget(self.technical_toggle_btn)
        self.technical_details_group = QGroupBox("技术详情（可选）")
        technical_layout = QVBoxLayout(self.technical_details_group)
        for detail in BEGINNER_TECHNICAL_DETAILS_COPY:
            detail_label = QLabel(detail)
            detail_label.setWordWrap(True)
            technical_layout.addWidget(detail_label)
        layout.addWidget(self.technical_details_group)

        self.completion_group = QGroupBox("本次演练终点")
        completion_layout = QVBoxLayout(self.completion_group)
        completion_label = QLabel(COMPLETION_TITLE)
        completion_label.setWordWrap(True)
        completion_label.setStyleSheet("font-weight: bold;")
        completion_layout.addWidget(completion_label)
        layout.addWidget(self.completion_group)

        button_row = QHBoxLayout()
        self.back_btn = QPushButton("上一步")
        self.back_btn.clicked.connect(self._go_back)
        self.next_btn = QPushButton("继续")
        self.next_btn.setDefault(True)
        self.next_btn.clicked.connect(self._continue_guide)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.reject)
        button_row.addWidget(self.back_btn)
        button_row.addStretch()
        button_row.addWidget(self.next_btn)
        button_row.addWidget(close_btn)
        layout.addLayout(button_row)

        self._render_current_step()

    def _on_material_changed(self):
        self.session.update_material(self.material_input.toPlainText())
        self._render_current_step()

    def _clear_material(self):
        self.material_input.blockSignals(True)
        self.material_input.clear()
        self.material_input.blockSignals(False)
        self.session.clear_material()
        self._render_current_step()

    def _use_example_material(self):
        self.session.load_example_material()
        self.material_input.blockSignals(True)
        self.material_input.setPlainText(self.session.material_text)
        self.material_input.blockSignals(False)
        self._render_current_step()

    def _continue_guide(self):
        if self.session.current_step is BeginnerFlowStep.COMPLETED_NO_WRITE:
            self.reject()
            return
        self._collapse_technical_details()
        if self.session.current_step is BeginnerFlowStep.SELECT_MATERIAL:
            self.session.select_material()
        elif self.session.current_step is BeginnerFlowStep.INSPECT_RECOGNITION:
            self.session.mark_recognition_inspected()
        elif self.session.current_step is BeginnerFlowStep.CHOOSE_KNOWLEDGE_POINTS:
            selected_ids = tuple(
                point_id
                for point_id, checkbox in self.knowledge_checkboxes.items()
                if checkbox.isChecked()
            )
            self.session.select_knowledge_points(selected_ids)
            self.session.build_candidate_previews_from_selection()
        elif self.session.current_step is BeginnerFlowStep.REVIEW_CANDIDATE_CARDS:
            self.session.complete_candidate_review()
        elif self.session.current_step is BeginnerFlowStep.CHECK_BEFORE_WRITE:
            self.session.mark_prewrite_check_inspected()
        else:
            self.session.advance_guide()
        self._render_current_step()

    def _go_back(self):
        current_index = BEGINNER_FLOW_STEP_ORDER.index(self.session.current_step)
        if current_index <= 0:
            return
        self._collapse_technical_details()
        self.session.go_back(BEGINNER_FLOW_STEP_ORDER[current_index - 1])
        self._render_current_step()

    def _render_current_step(self):
        step = self.session.current_step
        copy = BEGINNER_STEP_COPY[step]
        self.current_title_label.setText(copy.title)
        self.current_description_label.setText(copy.description)
        self.current_note_label.setText(BEGINNER_GUIDE_STEP_NOTES[step])
        self.material_count_label.setText(
            f"{self.session.material_char_count} 字符"
        )

        for nav_step, label in self.step_labels.items():
            nav_index = self.guide_steps.index(nav_step)
            current_index = BEGINNER_FLOW_STEP_ORDER.index(step)
            if step is BeginnerFlowStep.COMPLETED_NO_WRITE or nav_index < current_index:
                prefix = "✓"
                style = "color: gray;"
            elif nav_step is step:
                prefix = "→"
                style = "font-weight: bold;"
            else:
                prefix = "•"
                style = "color: gray;"
            label.setText(f"{prefix} {nav_index + 1}. {BEGINNER_STEP_COPY[nav_step].title}")
            label.setStyleSheet(style)

        is_material_step = step is BeginnerFlowStep.SELECT_MATERIAL
        is_preview_step = step is BeginnerFlowStep.INSPECT_RECOGNITION
        is_knowledge_step = step is BeginnerFlowStep.CHOOSE_KNOWLEDGE_POINTS
        is_candidate_step = step is BeginnerFlowStep.REVIEW_CANDIDATE_CARDS
        is_prewrite_step = step is BeginnerFlowStep.CHECK_BEFORE_WRITE
        is_complete = step is BeginnerFlowStep.COMPLETED_NO_WRITE
        self.material_group.setVisible(is_material_step)
        self.preview_group.setVisible(is_preview_step)
        self.knowledge_group.setVisible(is_knowledge_step)
        self.candidate_group.setVisible(is_candidate_step)
        self.prewrite_group.setVisible(is_prewrite_step)
        show_technical_option = is_candidate_step or is_prewrite_step
        self.technical_toggle_btn.setVisible(show_technical_option)
        self.technical_details_group.setVisible(
            show_technical_option and self.technical_details_expanded
        )
        self.completion_group.setVisible(is_complete)
        self.clear_material_btn.setEnabled(bool(self.session.material_text))
        self.back_btn.setEnabled(not is_material_step)
        self.next_btn.setText("结束演练" if is_complete else "继续")

        if is_preview_step:
            preview = self.session.material_preview() or "（材料为空）"
            self.material_preview_label.setText(
                f"共 {self.session.material_char_count} 字符\n\n{preview}"
            )
            self._render_recognition_results()
        if is_knowledge_step:
            self._render_knowledge_selection()
        if is_candidate_step:
            self._render_candidate_previews()
        self._update_primary_action_state()

    def _render_recognition_results(self):
        self._clear_layout(self.recognition_list_layout)
        if not self.session.recognized_knowledge_points:
            self.recognition_list_layout.addWidget(
                QLabel("当前材料没有识别出可展示的知识点。")
            )
            return
        for index, point in enumerate(
            self.session.recognized_knowledge_points,
            start=1,
        ):
            label = QLabel(
                f"{index}. {point.title}\n"
                f"说明：{point.explanation}\n"
                f"材料片段：{point.source_excerpt}"
            )
            label.setWordWrap(True)
            self.recognition_list_layout.addWidget(label)

    def _render_knowledge_selection(self):
        self._clear_layout(self.knowledge_layout)
        self.knowledge_checkboxes = {}
        if not self.session.recognized_knowledge_points:
            empty_label = QLabel(
                BEGINNER_STEP_COPY[
                    BeginnerFlowStep.CHOOSE_KNOWLEDGE_POINTS
                ].empty_state
            )
            empty_label.setWordWrap(True)
            self.knowledge_layout.addWidget(empty_label)
            return
        selected_ids = set(self.session.selected_knowledge_point_ids)
        for point in self.session.recognized_knowledge_points:
            checkbox = QCheckBox(f"{point.title}\n{point.explanation}")
            checkbox.setChecked(point.id in selected_ids)
            self.knowledge_checkboxes[point.id] = checkbox
            self.knowledge_layout.addWidget(checkbox)

    def _render_candidate_previews(self):
        self._clear_layout(self.candidate_layout)
        self.candidate_review_controls = {}
        self.candidate_review_button_groups = {}
        self.review_progress_label = None
        source_note = QLabel("这些候选卡来自你刚才选择的知识点。")
        source_note.setWordWrap(True)
        self.candidate_layout.addWidget(source_note)
        safety_note = QLabel(BEGINNER_REVIEW_SAFETY_NOTE)
        safety_note.setWordWrap(True)
        self.candidate_layout.addWidget(safety_note)
        if not self.session.candidate_card_previews:
            empty_label = QLabel(
                "还没有候选卡。请先回到上一步选择知识点。"
            )
            empty_label.setWordWrap(True)
            self.candidate_layout.addWidget(empty_label)
            return
        for candidate in self.session.candidate_card_previews:
            card_group = QGroupBox("候选卡预览")
            card_layout = QVBoxLayout(card_group)
            content = QLabel(
                f"正面预览：{candidate.front_preview}\n"
                f"背面预览：{candidate.back_preview}\n"
                f"来源片段：{candidate.source_excerpt}"
            )
            content.setWordWrap(True)
            card_layout.addWidget(content)
            choice_label = QLabel("审核选择")
            choice_label.setStyleSheet("font-weight: bold;")
            card_layout.addWidget(choice_label)
            choice_row = QHBoxLayout()
            button_group = QButtonGroup(card_group)
            controls = {}
            current_decision = self.session.candidate_review_decisions.get(
                candidate.id
            )
            for decision, label in BEGINNER_REVIEW_DECISION_COPY.items():
                option = QRadioButton(label)
                option.setChecked(current_decision is decision)
                option.toggled.connect(
                    lambda checked, candidate_id=candidate.id, value=decision: (
                        self._on_candidate_review_changed(
                            candidate_id,
                            value,
                            checked,
                        )
                    )
                )
                button_group.addButton(option)
                controls[decision] = option
                choice_row.addWidget(option)
            self.candidate_review_controls[candidate.id] = controls
            self.candidate_review_button_groups[candidate.id] = button_group
            card_layout.addLayout(choice_row)
            self.candidate_layout.addWidget(card_group)

        self.review_progress_label = QLabel()
        self.candidate_layout.addWidget(self.review_progress_label)
        self._update_review_progress()

    def _on_candidate_review_changed(self, candidate_id, decision, checked):
        if not checked:
            return
        self.session.set_candidate_review_decision(candidate_id, decision)
        self._update_review_progress()
        self._update_primary_action_state()

    def _update_review_progress(self):
        if self.review_progress_label is None:
            return
        reviewed = len(self.session.candidate_review_decisions)
        total = len(self.session.candidate_card_previews)
        self.review_progress_label.setText(f"已选择 {reviewed}/{total} 张")

    def _update_primary_action_state(self):
        step = self.session.current_step
        if step is BeginnerFlowStep.SELECT_MATERIAL:
            enabled = bool(self.session.material_text.strip())
        elif step is BeginnerFlowStep.REVIEW_CANDIDATE_CARDS:
            total = len(self.session.candidate_card_previews)
            enabled = total > 0 and len(
                self.session.candidate_review_decisions
            ) == total
        else:
            enabled = True
        self.next_btn.setEnabled(enabled)

    def _toggle_technical_details(self):
        self.technical_details_expanded = not self.technical_details_expanded
        self.technical_details_group.setVisible(self.technical_details_expanded)
        self.technical_toggle_btn.setText(
            "隐藏技术详情"
            if self.technical_details_expanded
            else "查看技术详情"
        )

    def _collapse_technical_details(self):
        self.technical_details_expanded = False
        self.technical_details_group.setVisible(False)
        self.technical_toggle_btn.setText("查看技术详情")

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _discard_session(self):
        self.material_input.blockSignals(True)
        self.material_input.clear()
        self.material_input.blockSignals(False)
        self.session.close()

    def reject(self):
        self._discard_session()
        super().reject()

    def closeEvent(self, event):
        self._discard_session()
        super().closeEvent(event)
