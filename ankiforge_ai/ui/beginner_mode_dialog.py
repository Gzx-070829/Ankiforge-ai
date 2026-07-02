"""In-memory Qt guide for the beginner mode."""

from aqt.qt import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from .beginner_ai_card_drafts import (
    BEGINNER_AI_GENERATING_COPY,
    BEGINNER_AI_PROVIDER_DISCLOSURE_COPY,
    BEGINNER_AI_SETTINGS_HELP_COPY,
    BeginnerAICardDraftGenerator,
    BeginnerAIProviderRuntimeSettings,
)
from .beginner_flow_models import (
    BEGINNER_FLOW_STEP_ORDER,
    BEGINNER_FUTURE_CONDITIONS,
    BEGINNER_GUIDE_SAFETY_COPY,
    BEGINNER_GUIDE_STEP_NOTES,
    BEGINNER_KNOWLEDGE_SELECTION_GUIDANCE,
    BEGINNER_MATERIAL_EMPTY_HINT,
    BEGINNER_NO_CANDIDATE_PREVIEWS_COPY,
    BEGINNER_NO_SELECTED_KNOWLEDGE_COPY,
    BEGINNER_PREWRITE_SUMMARY,
    BEGINNER_PREWRITE_INCOMPLETE_REVIEW_COPY,
    BEGINNER_RECOGNITION_EMPTY_MATERIAL_COPY,
    BEGINNER_RECOGNITION_NO_RESULTS_COPY,
    BEGINNER_REVIEW_CHOICE_GUIDANCE,
    BEGINNER_REVIEW_DECISION_COPY,
    BEGINNER_REVIEW_SAFETY_NOTE,
    BEGINNER_STEP_COPY,
    BEGINNER_TECHNICAL_DETAILS_COPY,
    COMPLETION_TITLE,
    BeginnerArtifactState,
    BeginnerFlowSession,
    BeginnerFlowStep,
    BeginnerReviewDecision,
)
from .read_only_anki_targets import (
    ANKI_MAPPING_PREVIEW_SAFETY_COPY,
    BeginnerAnkiReadState,
    ReadOnlyAnkiTargetAdapter,
    build_beginner_field_mapping_preview,
)
from .read_only_duplicate_check import (
    DUPLICATE_CHECK_SCOPE_COPY,
    BeginnerDuplicatePreviewState,
    BeginnerDuplicateStatus,
    ReadOnlyDuplicateCheckAdapter,
)


class BeginnerModeDialog(QDialog):
    """Guide one disposable session without starting pipeline work."""

    def __init__(self, parent=None, collection=None):
        super().__init__(parent)
        self.session = BeginnerFlowSession()
        self.anki_target_adapter = ReadOnlyAnkiTargetAdapter(collection)
        self.duplicate_check_adapter = ReadOnlyDuplicateCheckAdapter(collection)
        self.anki_target_snapshot = None
        self.anki_field_snapshot = None
        self.anki_mapping_preview = None
        self.duplicate_check_preview = None
        self.setWindowTitle("新手模式（只读演练）")
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

        safety_group = QGroupBox("新手模式安全状态")
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

        self.ai_provider_group = QGroupBox("真实 AI 候选卡草稿（可选）")
        ai_layout = QVBoxLayout(self.ai_provider_group)
        ai_disclosure = QLabel(BEGINNER_AI_PROVIDER_DISCLOSURE_COPY)
        ai_disclosure.setWordWrap(True)
        ai_disclosure.setStyleSheet("font-weight: bold;")
        ai_layout.addWidget(ai_disclosure)
        ai_form = QFormLayout()
        self.ai_provider_name_input = QLineEdit("OpenAI-compatible")
        ai_form.addRow("Provider:", self.ai_provider_name_input)
        self.ai_base_url_input = QLineEdit()
        self.ai_base_url_input.setPlaceholderText("https://example.com/v1")
        ai_form.addRow("Base URL:", self.ai_base_url_input)
        self.ai_model_input = QLineEdit()
        self.ai_model_input.setPlaceholderText("本次会话使用的模型")
        ai_form.addRow("Model:", self.ai_model_input)
        self.ai_api_key_input = QLineEdit()
        password_mode = (
            QLineEdit.EchoMode.Password
            if hasattr(QLineEdit, "EchoMode")
            else QLineEdit.Password
        )
        self.ai_api_key_input.setEchoMode(password_mode)
        self.ai_api_key_input.setPlaceholderText("只用于当前窗口")
        ai_form.addRow("本次会话 API key:", self.ai_api_key_input)
        self.ai_timeout_input = QSpinBox()
        self.ai_timeout_input.setRange(1, 300)
        self.ai_timeout_input.setValue(60)
        ai_form.addRow("Timeout 秒:", self.ai_timeout_input)
        ai_layout.addLayout(ai_form)
        self.ai_send_consent = QCheckBox(
            "我知道本次会联网，并把当前材料发送给所选 AI Provider。"
        )
        ai_layout.addWidget(self.ai_send_consent)
        ai_action_row = QHBoxLayout()
        self.ai_status_label = QLabel()
        self.ai_status_label.setWordWrap(True)
        self.ai_generate_btn = QPushButton("用 AI 生成候选卡")
        self.ai_generate_btn.clicked.connect(self._generate_ai_candidate_drafts)
        self.ai_retry_btn = QPushButton("重新生成")
        self.ai_retry_btn.clicked.connect(self._generate_ai_candidate_drafts)
        ai_action_row.addWidget(self.ai_status_label, 1)
        ai_action_row.addWidget(self.ai_generate_btn)
        ai_action_row.addWidget(self.ai_retry_btn)
        ai_layout.addLayout(ai_action_row)
        layout.addWidget(self.ai_provider_group)

        for widget in (
            self.ai_provider_name_input,
            self.ai_base_url_input,
            self.ai_model_input,
            self.ai_api_key_input,
        ):
            widget.textChanged.connect(self._on_ai_runtime_settings_changed)
        self.ai_timeout_input.valueChanged.connect(
            self._on_ai_runtime_settings_changed
        )
        self.ai_send_consent.stateChanged.connect(self._update_ai_action_state)

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
        self.prewrite_review_hint = QLabel(BEGINNER_PREWRITE_INCOMPLETE_REVIEW_COPY)
        self.prewrite_review_hint.setWordWrap(True)
        prewrite_layout.addWidget(self.prewrite_review_hint)
        for index, condition in enumerate(BEGINNER_FUTURE_CONDITIONS, start=1):
            condition_label = QLabel(
                f"{index}. {condition.title}｜{condition.status}\n"
                f"{condition.explanation}"
            )
            condition_label.setWordWrap(True)
            prewrite_layout.addWidget(condition_label)

        self.anki_target_group = QGroupBox("未来写入设置预览")
        anki_target_layout = QVBoxLayout(self.anki_target_group)
        anki_target_safety = QLabel(ANKI_MAPPING_PREVIEW_SAFETY_COPY)
        anki_target_safety.setWordWrap(True)
        anki_target_safety.setStyleSheet("font-weight: bold;")
        anki_target_layout.addWidget(anki_target_safety)
        anki_read_row = QHBoxLayout()
        self.read_anki_targets_btn = QPushButton("读取 Anki 结构")
        self.read_anki_targets_btn.clicked.connect(self._read_anki_targets)
        self.reload_anki_targets_btn = QPushButton("重新读取")
        self.reload_anki_targets_btn.clicked.connect(self._read_anki_targets)
        self.anki_target_status_label = QLabel()
        self.anki_target_status_label.setWordWrap(True)
        anki_read_row.addWidget(self.read_anki_targets_btn)
        anki_read_row.addWidget(self.reload_anki_targets_btn)
        anki_read_row.addWidget(self.anki_target_status_label, 1)
        anki_target_layout.addLayout(anki_read_row)

        anki_target_form = QFormLayout()
        self.anki_deck_combo = QComboBox()
        self.anki_deck_combo.setEnabled(False)
        self.anki_deck_combo.currentIndexChanged.connect(
            self._on_anki_deck_changed
        )
        anki_target_form.addRow("选择目标牌组:", self.anki_deck_combo)
        self.anki_note_type_combo = QComboBox()
        self.anki_note_type_combo.setEnabled(False)
        self.anki_note_type_combo.currentIndexChanged.connect(
            self._on_anki_note_type_changed
        )
        anki_target_form.addRow("选择笔记类型:", self.anki_note_type_combo)
        self.anki_front_field_combo = QComboBox()
        self.anki_back_field_combo = QComboBox()
        self.anki_source_field_combo = QComboBox()
        for combo in (
            self.anki_front_field_combo,
            self.anki_back_field_combo,
            self.anki_source_field_combo,
        ):
            combo.setEnabled(False)
            combo.currentIndexChanged.connect(self._on_anki_mapping_changed)
        anki_target_form.addRow("候选卡正面 →", self.anki_front_field_combo)
        anki_target_form.addRow("候选卡背面 →", self.anki_back_field_combo)
        anki_target_form.addRow("候选卡来源 →", self.anki_source_field_combo)
        anki_target_layout.addLayout(anki_target_form)
        self.anki_mapping_preview_label = QLabel(ANKI_MAPPING_PREVIEW_SAFETY_COPY)
        self.anki_mapping_preview_label.setWordWrap(True)
        anki_target_layout.addWidget(self.anki_mapping_preview_label)

        duplicate_group = QGroupBox("重复检查只读预览")
        duplicate_layout = QVBoxLayout(duplicate_group)
        duplicate_scope = QLabel(DUPLICATE_CHECK_SCOPE_COPY)
        duplicate_scope.setWordWrap(True)
        duplicate_layout.addWidget(duplicate_scope)
        duplicate_button_row = QHBoxLayout()
        self.duplicate_check_btn = QPushButton("检查是否可能重复")
        self.duplicate_check_btn.clicked.connect(self._run_duplicate_check)
        self.duplicate_recheck_btn = QPushButton("重新检查")
        self.duplicate_recheck_btn.clicked.connect(self._run_duplicate_check)
        duplicate_button_row.addWidget(self.duplicate_check_btn)
        duplicate_button_row.addWidget(self.duplicate_recheck_btn)
        duplicate_button_row.addStretch()
        duplicate_layout.addLayout(duplicate_button_row)
        self.duplicate_check_result_label = QLabel(DUPLICATE_CHECK_SCOPE_COPY)
        self.duplicate_check_result_label.setWordWrap(True)
        duplicate_layout.addWidget(self.duplicate_check_result_label)
        anki_target_layout.addWidget(duplicate_group)
        prewrite_layout.addWidget(self.anki_target_group)
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

    def _on_ai_runtime_settings_changed(self, *unused):
        self.session.mark_ai_runtime_settings_changed()
        self.ai_status_label.clear()
        self._update_ai_action_state()

    def _generate_ai_candidate_drafts(self):
        if not self._ai_request_ready():
            self.ai_status_label.setText(BEGINNER_AI_SETTINGS_HELP_COPY)
            return
        try:
            settings = BeginnerAIProviderRuntimeSettings(
                provider_name=self.ai_provider_name_input.text(),
                base_url=self.ai_base_url_input.text(),
                model=self.ai_model_input.text(),
                api_key=self.ai_api_key_input.text(),
                timeout_seconds=self.ai_timeout_input.value(),
            )
        except ValueError:
            self.ai_status_label.setText(BEGINNER_AI_SETTINGS_HELP_COPY)
            return

        self.session.begin_ai_candidate_generation()
        self.ai_generate_btn.setEnabled(False)
        self.ai_retry_btn.setEnabled(False)
        self.ai_status_label.setText(BEGINNER_AI_GENERATING_COPY)
        QApplication.processEvents()
        result = BeginnerAICardDraftGenerator().generate(
            settings=settings,
            material_text=self.session.material_text,
        )
        if result.success:
            self.session.apply_ai_candidate_card_drafts(result.drafts)
        else:
            self.session.record_ai_card_draft_error(
                result.state,
                result.error_code.value,
            )
        self.ai_status_label.setText(result.user_message)
        self._render_current_step()

    def _read_anki_targets(self):
        self.session.clear_anki_target_selection()
        self.anki_mapping_preview = None
        self.anki_field_snapshot = None
        self._clear_duplicate_display()
        snapshot = self.anki_target_adapter.read_targets()
        self.anki_target_snapshot = snapshot
        self.anki_target_status_label.setText(snapshot.user_message)
        self._populate_anki_target_combos(snapshot)
        self.anki_mapping_preview_label.setText(
            ANKI_MAPPING_PREVIEW_SAFETY_COPY
        )

    def _populate_anki_target_combos(self, snapshot):
        for combo in (self.anki_deck_combo, self.anki_note_type_combo):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("请选择", None)
        for deck in snapshot.decks:
            self.anki_deck_combo.addItem(deck.name, deck.id)
        for note_type in snapshot.note_types:
            self.anki_note_type_combo.addItem(note_type.name, note_type.id)
        for combo in (self.anki_deck_combo, self.anki_note_type_combo):
            combo.setCurrentIndex(0)
            combo.setEnabled(combo.count() > 1)
            combo.blockSignals(False)
        self._clear_anki_field_combos()

    def _on_anki_deck_changed(self, index):
        self._clear_duplicate_display()
        deck = self._selected_anki_deck()
        if deck is None:
            self.session.clear_anki_deck_selection()
            self.anki_mapping_preview = None
            self.anki_mapping_preview_label.setText(
                ANKI_MAPPING_PREVIEW_SAFETY_COPY
            )
            return
        self.session.select_anki_deck(deck.id, deck.name)
        self._update_anki_mapping_preview()

    def _on_anki_note_type_changed(self, index):
        self._clear_duplicate_display()
        note_type = self._selected_anki_note_type()
        if note_type is None:
            self.session.clear_anki_note_type_selection()
            self._clear_anki_field_combos()
            self.anki_mapping_preview = None
            self.anki_mapping_preview_label.setText(
                ANKI_MAPPING_PREVIEW_SAFETY_COPY
            )
            return
        field_snapshot = self.anki_target_adapter.read_fields(note_type.id)
        self.anki_field_snapshot = field_snapshot
        self.anki_target_status_label.setText(field_snapshot.user_message)
        if field_snapshot.state is not BeginnerAnkiReadState.SUCCESS:
            self._clear_anki_field_combos()
            return
        self.session.select_anki_note_type(
            note_type.id,
            note_type.name,
            field_snapshot.fields,
        )
        self._populate_anki_field_combos(field_snapshot.fields)
        self._update_anki_mapping_preview()

    def _populate_anki_field_combos(self, fields):
        for combo in (
            self.anki_front_field_combo,
            self.anki_back_field_combo,
            self.anki_source_field_combo,
        ):
            combo.blockSignals(True)
            combo.clear()
        self.anki_front_field_combo.addItem("请选择", None)
        self.anki_back_field_combo.addItem("请选择", None)
        self.anki_source_field_combo.addItem("不映射来源", None)
        for field_name in fields:
            self.anki_front_field_combo.addItem(field_name, field_name)
            self.anki_back_field_combo.addItem(field_name, field_name)
            self.anki_source_field_combo.addItem(field_name, field_name)
        self._select_matching_field(self.anki_front_field_combo, ("front",))
        self._select_matching_field(self.anki_back_field_combo, ("back",))
        self._select_matching_field(
            self.anki_source_field_combo,
            ("source", "extra"),
        )
        for combo in (
            self.anki_front_field_combo,
            self.anki_back_field_combo,
            self.anki_source_field_combo,
        ):
            combo.setEnabled(True)
            combo.blockSignals(False)

    def _clear_anki_field_combos(self):
        for combo in (
            self.anki_front_field_combo,
            self.anki_back_field_combo,
            self.anki_source_field_combo,
        ):
            combo.blockSignals(True)
            combo.clear()
            combo.setEnabled(False)
            combo.blockSignals(False)

    @staticmethod
    def _select_matching_field(combo, candidates):
        for index in range(combo.count()):
            value = combo.itemData(index)
            if isinstance(value, str) and value.casefold() in candidates:
                combo.setCurrentIndex(index)
                return

    def _on_anki_mapping_changed(self, index):
        self._update_anki_mapping_preview()

    def _update_anki_mapping_preview(self):
        self._clear_duplicate_display()
        deck = self._selected_anki_deck()
        note_type = self._selected_anki_note_type()
        if (
            deck is None
            or note_type is None
            or self.anki_field_snapshot is None
            or self.anki_field_snapshot.state is not BeginnerAnkiReadState.SUCCESS
        ):
            return
        front_field = self.anki_front_field_combo.currentData()
        back_field = self.anki_back_field_combo.currentData()
        source_field = self.anki_source_field_combo.currentData()
        if not front_field or not back_field:
            self.session.clear_anki_field_mapping()
            self.anki_mapping_preview = None
            self.anki_mapping_preview_label.setText(
                ANKI_MAPPING_PREVIEW_SAFETY_COPY
            )
            return
        self.session.set_anki_field_mapping(
            front_field,
            back_field,
            source_field,
        )
        preview = build_beginner_field_mapping_preview(
            deck=deck,
            note_type=note_type,
            available_fields=self.anki_field_snapshot.fields,
            front_field=front_field,
            back_field=back_field,
            source_field=source_field,
        )
        self.anki_mapping_preview = preview
        self.anki_mapping_preview_label.setText(
            "\n".join(preview.summary_lines)
        )
        self._update_duplicate_action_state()

    def _run_duplicate_check(self):
        self.session.begin_duplicate_check()
        preview = self.duplicate_check_adapter.check(
            self.session.candidate_card_previews,
            self.anki_mapping_preview,
        )
        self.duplicate_check_preview = preview
        if preview.state is BeginnerDuplicatePreviewState.SUCCESS:
            possible_count = sum(
                item.status is BeginnerDuplicateStatus.POSSIBLE_DUPLICATE
                for item in preview.results
            )
            self.session.apply_duplicate_check_preview(
                len(preview.results),
                possible_count,
            )
        elif preview.state is BeginnerDuplicatePreviewState.ERROR:
            self.session.record_duplicate_check_error("collection_read_failed")
        else:
            self.session.clear_duplicate_check_preview()
        self._render_duplicate_check_preview(preview)

    def _render_duplicate_check_preview(self, preview):
        lines = [preview.user_message]
        for index, result in enumerate(preview.results, start=1):
            lines.append(f"候选卡 {index}：{result.status_copy}")
            if result.status is BeginnerDuplicateStatus.POSSIBLE_DUPLICATE:
                lines.append(f"匹配字段：{', '.join(result.matched_fields)}")
                lines.append(f"匹配 note id：{result.matched_note_id}")
                if result.matched_field_preview:
                    lines.append(
                        f"字段预览：{result.matched_field_preview}"
                    )
        self.duplicate_check_result_label.setText("\n".join(lines))
        self._update_duplicate_action_state()

    def _clear_duplicate_display(self):
        self.duplicate_check_preview = None
        self.duplicate_check_result_label.setText(DUPLICATE_CHECK_SCOPE_COPY)
        self._update_duplicate_action_state()

    def _update_duplicate_action_state(self):
        enabled = bool(
            self.session.candidate_card_previews
            and self.anki_mapping_preview is not None
        )
        self.duplicate_check_btn.setEnabled(enabled)
        self.duplicate_recheck_btn.setEnabled(enabled)

    def _selected_anki_deck(self):
        if self.anki_target_snapshot is None:
            return None
        selected_id = self.anki_deck_combo.currentData()
        return next(
            (item for item in self.anki_target_snapshot.decks if item.id == selected_id),
            None,
        )

    def _selected_anki_note_type(self):
        if self.anki_target_snapshot is None:
            return None
        selected_id = self.anki_note_type_combo.currentData()
        return next(
            (
                item
                for item in self.anki_target_snapshot.note_types
                if item.id == selected_id
            ),
            None,
        )

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
            self.session.view_prewrite_conditions()
        elif self.session.current_step is BeginnerFlowStep.CHECK_BEFORE_WRITE:
            self.session.finish_prewrite_walkthrough()
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
        self.ai_provider_group.setVisible(is_material_step)
        self.preview_group.setVisible(is_preview_step)
        self.knowledge_group.setVisible(is_knowledge_step)
        self.candidate_group.setVisible(is_candidate_step)
        self.prewrite_group.setVisible(is_prewrite_step)
        self.prewrite_review_hint.setVisible(
            is_prewrite_step and not self.session.candidate_review_complete
        )
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
        if (
            is_prewrite_step
            and self.session.duplicate_check_preview_state
            is not BeginnerArtifactState.CURRENT
            and self.session.duplicate_check_error_code is None
            and self.duplicate_check_preview is not None
        ):
            self._clear_duplicate_display()
        self._update_primary_action_state()
        self._update_ai_action_state()
        self._update_duplicate_action_state()

    def _render_recognition_results(self):
        self._clear_layout(self.recognition_list_layout)
        if not self.session.recognized_knowledge_points:
            empty_copy = (
                BEGINNER_RECOGNITION_EMPTY_MATERIAL_COPY
                if not self.session.material_text.strip()
                else BEGINNER_RECOGNITION_NO_RESULTS_COPY
            )
            self.recognition_list_layout.addWidget(
                QLabel(empty_copy)
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
        guidance_label = QLabel(BEGINNER_KNOWLEDGE_SELECTION_GUIDANCE)
        guidance_label.setWordWrap(True)
        self.knowledge_layout.addWidget(guidance_label)
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
        if self.session.candidate_origin == "real_ai_draft":
            source_copy = (
                "这些只读候选卡草稿来自你刚才主动调用的 AI Provider。"
                "请逐张核对；当前不会写入 Anki。"
            )
        else:
            source_copy = "这些候选卡来自你刚才选择的知识点。"
        source_note = QLabel(source_copy)
        source_note.setWordWrap(True)
        self.candidate_layout.addWidget(source_note)
        safety_note = QLabel(BEGINNER_REVIEW_SAFETY_NOTE)
        safety_note.setWordWrap(True)
        self.candidate_layout.addWidget(safety_note)
        if not self.session.candidate_card_previews:
            empty_copy = (
                BEGINNER_NO_SELECTED_KNOWLEDGE_COPY
                if not self.session.selected_knowledge_point_ids
                else BEGINNER_NO_CANDIDATE_PREVIEWS_COPY
            )
            empty_label = QLabel(
                empty_copy
            )
            empty_label.setWordWrap(True)
            self.candidate_layout.addWidget(empty_label)
            return
        review_guidance = QLabel(BEGINNER_REVIEW_CHOICE_GUIDANCE)
        review_guidance.setWordWrap(True)
        self.candidate_layout.addWidget(review_guidance)
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
        if reviewed == total:
            copy = f"已选择 {reviewed}/{total} 张，可以继续查看下一步。"
        else:
            copy = (
                f"已选择 {reviewed}/{total} 张。你可以继续选择，"
                "也可以先查看下一步说明。"
            )
        self.review_progress_label.setText(copy)

    def _update_primary_action_state(self):
        step = self.session.current_step
        if step is BeginnerFlowStep.SELECT_MATERIAL:
            enabled = bool(self.session.material_text.strip())
        else:
            enabled = True
        self.next_btn.setEnabled(enabled)

    def _ai_request_ready(self):
        return all(
            (
                self.session.material_text.strip(),
                self.ai_provider_name_input.text().strip(),
                self.ai_base_url_input.text().strip(),
                self.ai_model_input.text().strip(),
                self.ai_api_key_input.text().strip(),
                self.ai_send_consent.isChecked(),
            )
        )

    def _update_ai_action_state(self, *unused):
        enabled = self._ai_request_ready()
        self.ai_generate_btn.setEnabled(enabled)
        self.ai_retry_btn.setEnabled(enabled)

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
        self.ai_api_key_input.blockSignals(True)
        self.ai_api_key_input.clear()
        self.ai_api_key_input.blockSignals(False)
        self.anki_target_snapshot = None
        self.anki_field_snapshot = None
        self.anki_mapping_preview = None
        self.duplicate_check_preview = None
        self.session.close()

    def reject(self):
        self._discard_session()
        super().reject()

    def closeEvent(self, event):
        self._discard_session()
        super().closeEvent(event)
