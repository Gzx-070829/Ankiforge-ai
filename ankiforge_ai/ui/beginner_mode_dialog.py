"""Read-only Qt overview for the v0.9 beginner mode entry."""

from aqt.qt import (
    QDialog,
    QGroupBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from .beginner_flow_models import (
    BEGINNER_FLOW_STEP_ORDER,
    BEGINNER_SAFETY_STATUS_COPY,
    BEGINNER_STEP_COPY,
    COMPLETION_TITLE,
    BeginnerFlowStep,
)


class BeginnerModeDialog(QDialog):
    """Explain the future walkthrough without starting any pipeline work."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新手模式（离线只读演练）")
        self.resize(620, 520)

        layout = QVBoxLayout(self)
        intro = QLabel(
            "先看懂流程，再决定后续操作。本窗口只展示说明，不处理学习材料。"
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        steps_group = QGroupBox("五步流程概览")
        steps_layout = QVBoxLayout(steps_group)
        overview_steps = tuple(
            step
            for step in BEGINNER_FLOW_STEP_ORDER
            if step is not BeginnerFlowStep.COMPLETED_NO_WRITE
        )
        for index, step in enumerate(overview_steps, start=1):
            copy = BEGINNER_STEP_COPY[step]
            step_label = QLabel(f"{index}. {copy.title}\n{copy.description}")
            step_label.setWordWrap(True)
            steps_layout.addWidget(step_label)
        layout.addWidget(steps_group)

        safety_group = QGroupBox("当前安全状态")
        safety_layout = QVBoxLayout(safety_group)
        for status in BEGINNER_SAFETY_STATUS_COPY:
            status_label = QLabel(f"• {status}")
            status_label.setWordWrap(True)
            safety_layout.addWidget(status_label)
        layout.addWidget(safety_group)

        completion_label = QLabel(COMPLETION_TITLE)
        completion_label.setWordWrap(True)
        completion_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(completion_label)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)
