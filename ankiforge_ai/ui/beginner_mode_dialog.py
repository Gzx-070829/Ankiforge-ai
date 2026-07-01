"""In-memory Qt guide for the v0.9 beginner mode."""

from aqt.qt import (
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

        self.preview_group = QGroupBox("材料预览")
        preview_layout = QVBoxLayout(self.preview_group)
        self.material_preview_label = QLabel()
        self.material_preview_label.setWordWrap(True)
        preview_layout.addWidget(self.material_preview_label)
        layout.addWidget(self.preview_group)

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
        is_complete = step is BeginnerFlowStep.COMPLETED_NO_WRITE
        self.material_group.setVisible(is_material_step)
        self.preview_group.setVisible(is_preview_step)
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
