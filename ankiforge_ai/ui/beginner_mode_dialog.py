"""In-memory Qt guide for the v0.9 beginner mode."""

from aqt.qt import (
    QCheckBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from .beginner_flow_models import (
    BEGINNER_FLOW_STEP_ORDER,
    BEGINNER_GUIDE_SAFETY_COPY,
    BEGINNER_GUIDE_STEP_NOTES,
    BEGINNER_STEP_COPY,
    COMPLETION_TITLE,
    BeginnerFlowSession,
    BeginnerFlowStep,
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
        self.material_input = QTextEdit()
        self.material_input.setPlaceholderText("在这里输入或粘贴学习材料")
        self.material_input.textChanged.connect(self._on_material_changed)
        material_layout.addWidget(self.material_input)
        material_footer = QHBoxLayout()
        self.material_count_label = QLabel("0 字符")
        self.clear_material_btn = QPushButton("清空材料")
        self.clear_material_btn.clicked.connect(self._clear_material)
        material_footer.addWidget(self.material_count_label)
        material_footer.addStretch()
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
        self.candidate_review_checkboxes = {}
        layout.addWidget(self.candidate_group)

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

    def _continue_guide(self):
        if self.session.current_step is BeginnerFlowStep.COMPLETED_NO_WRITE:
            self.reject()
            return
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
            self.session.change_review_decision(
                len(self.session.candidate_review_decisions)
            )
        elif self.session.current_step is BeginnerFlowStep.CHECK_BEFORE_WRITE:
            self.session.mark_prewrite_check_inspected()
        else:
            self.session.advance_guide()
        self._render_current_step()

    def _go_back(self):
        current_index = BEGINNER_FLOW_STEP_ORDER.index(self.session.current_step)
        if current_index <= 0:
            return
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
        is_complete = step is BeginnerFlowStep.COMPLETED_NO_WRITE
        self.material_group.setVisible(is_material_step)
        self.preview_group.setVisible(is_preview_step)
        self.knowledge_group.setVisible(is_knowledge_step)
        self.candidate_group.setVisible(is_candidate_step)
        self.completion_group.setVisible(is_complete)
        self.clear_material_btn.setEnabled(bool(self.session.material_text))
        self.back_btn.setEnabled(not is_material_step)
        self.next_btn.setEnabled(
            not is_material_step or bool(self.session.material_text.strip())
        )
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
        self.candidate_review_checkboxes = {}
        source_note = QLabel("这些候选卡来自你刚才选择的知识点。")
        source_note.setWordWrap(True)
        self.candidate_layout.addWidget(source_note)
        if not self.session.candidate_card_previews:
            empty_label = QLabel(
                "还没有选择知识点。请先回到上一步选择你想制卡的内容。"
            )
            empty_label.setWordWrap(True)
            self.candidate_layout.addWidget(empty_label)
            return
        for candidate in self.session.candidate_card_previews:
            card_group = QGroupBox("候选卡预览")
            card_layout = QVBoxLayout(card_group)
            content = QLabel(
                f"问题预览：{candidate.front_preview}\n"
                f"回答预览：{candidate.back_preview}\n"
                f"材料来源：{candidate.source_excerpt}"
            )
            content.setWordWrap(True)
            card_layout.addWidget(content)
            reviewed = QCheckBox("我已检查这张候选卡")
            reviewed.setChecked(
                candidate.id in self.session.candidate_review_decisions
            )
            reviewed.stateChanged.connect(
                lambda state, candidate_id=candidate.id: (
                    self._on_candidate_review_changed(candidate_id, bool(state))
                )
            )
            self.candidate_review_checkboxes[candidate.id] = reviewed
            card_layout.addWidget(reviewed)
            self.candidate_layout.addWidget(card_group)

    def _on_candidate_review_changed(self, candidate_id, checked):
        self.session.set_candidate_review_decision(
            candidate_id,
            "reviewed" if checked else None,
        )

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
