"""Single-screen product panel for turning study material into Anki cards."""

from pathlib import Path

from aqt.qt import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..anki_writer.minimal_write import MinimalAnkiWriter
from .beginner_ai_card_drafts import (
    BeginnerAICardDraftGenerator,
    BeginnerAIProviderRuntimeSettings,
)
from .beginner_final_confirmation import (
    build_beginner_final_confirmation_preview,
)
from .beginner_flow_models import (
    BeginnerAICardDraft,
    BeginnerFlowSession,
    BeginnerReviewDecision,
    BeginnerWriteState,
)
from .beginner_real_write import (
    execute_beginner_write_if_confirmed,
    prepare_beginner_write,
)
from .read_only_anki_targets import (
    BeginnerAnkiReadState,
    ReadOnlyAnkiTargetAdapter,
    build_beginner_field_mapping_preview,
)
from .read_only_duplicate_check import (
    BeginnerDuplicatePreviewState,
    BeginnerDuplicateStatus,
    ReadOnlyDuplicateCheckAdapter,
)


GENERATION_FAILURE_COPY = "生成失败，请检查 API key、模型或网络后重试。"
WRITE_FAILURE_COPY = "写入失败，请检查牌组、笔记类型或字段映射后重试。"


class CardMakerPanel(QWidget):
    """One disposable, single-screen card-making session."""

    def __init__(self, parent=None, collection=None):
        super().__init__(parent)
        self.session = BeginnerFlowSession()
        self.anki_target_adapter = ReadOnlyAnkiTargetAdapter(collection)
        self.duplicate_check_adapter = ReadOnlyDuplicateCheckAdapter(collection)
        self.writer = MinimalAnkiWriter(collection)
        self.anki_target_snapshot = None
        self.anki_field_snapshot = None
        self.anki_mapping = None
        self.duplicate_results = None
        self.write_summary = None
        self.write_preparation = None
        self.write_command = None
        self.write_result = None
        self.card_button_groups = {}

        self.setMaximumWidth(920)
        self._build_ui()
        self._read_anki_targets()
        self._render_cards()
        self._refresh_product_state()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(16)

        columns = QHBoxLayout()
        columns.setSpacing(16)
        left = QWidget()
        left.setMinimumWidth(410)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(14)
        left_layout.addWidget(self._build_material_section(), 1)
        left_layout.addWidget(self._build_ai_section())

        right = QWidget()
        right.setMinimumWidth(410)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(14)
        right_layout.addWidget(self._build_cards_section(), 1)
        right_layout.addWidget(self._build_write_section())

        columns.addWidget(left, 1)
        columns.addWidget(right, 1)
        root.addLayout(columns)

    def _build_material_section(self):
        group = QGroupBox("学习材料")
        layout = QVBoxLayout(group)
        hint = QLabel("粘贴笔记、教材段落或复习资料。")
        hint.setStyleSheet("color: #666;")
        layout.addWidget(hint)

        self.material_input = QTextEdit()
        self.material_input.setPlaceholderText("在这里粘贴学习材料")
        self.material_input.setMinimumHeight(150)
        self.material_input.setMaximumHeight(230)
        self.material_input.textChanged.connect(self._on_material_changed)
        layout.addWidget(self.material_input)

        actions = QHBoxLayout()
        self.choose_markdown_btn = QPushButton("选择 Markdown 文件")
        self.choose_markdown_btn.clicked.connect(self._choose_markdown_file)
        self.example_btn = QPushButton("使用示例")
        self.example_btn.clicked.connect(self._use_example_material)
        self.material_count_label = QLabel("0 字符")
        self.material_count_label.setStyleSheet("color: #777;")
        actions.addWidget(self.choose_markdown_btn)
        actions.addWidget(self.example_btn)
        actions.addStretch()
        actions.addWidget(self.material_count_label)
        layout.addLayout(actions)
        return group

    def _build_ai_section(self):
        group = QGroupBox("AI")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        compact = QGridLayout()
        compact.setHorizontalSpacing(8)
        compact.setVerticalSpacing(8)

        self.provider_combo = QComboBox()
        self.provider_combo.addItem(
            "OpenAI-compatible",
            ("OpenAI-compatible", "https://api.deepseek.com/v1"),
        )
        self.provider_combo.addItem(
            "OpenAI",
            ("OpenAI", "https://api.openai.com/v1"),
        )
        self.provider_combo.addItem(
            "DeepSeek",
            ("DeepSeek", "https://api.deepseek.com/v1"),
        )
        self.provider_combo.currentIndexChanged.connect(
            self._on_provider_changed
        )
        compact.addWidget(QLabel("Provider"), 0, 0)
        compact.addWidget(self.provider_combo, 0, 1)

        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("例如 deepseek-chat")
        compact.addWidget(QLabel("Model"), 0, 2)
        compact.addWidget(self.model_input, 0, 3)

        self.api_key_input = QLineEdit()
        password_mode = (
            QLineEdit.EchoMode.Password
            if hasattr(QLineEdit, "EchoMode")
            else QLineEdit.Password
        )
        self.api_key_input.setEchoMode(password_mode)
        self.api_key_input.setPlaceholderText("本次使用，不会保存")
        compact.addWidget(QLabel("API key"), 1, 0)
        compact.addWidget(self.api_key_input, 1, 1, 1, 3)
        compact.setColumnStretch(1, 1)
        compact.setColumnStretch(3, 1)
        layout.addLayout(compact)

        key_hint = QLabel("API key 仅本次使用，不会保存。")
        key_hint.setStyleSheet("color: #666;")
        layout.addWidget(key_hint)

        self.ai_advanced_btn = QPushButton("高级设置")
        self.ai_advanced_btn.setCheckable(True)
        self.ai_advanced_btn.setFlat(True)
        self.ai_advanced_btn.toggled.connect(self._toggle_ai_advanced)
        layout.addWidget(self.ai_advanced_btn, 0)

        self.ai_advanced_container = QWidget()
        advanced_form = QFormLayout(self.ai_advanced_container)
        advanced_form.setContentsMargins(18, 0, 0, 0)
        self.base_url_input = QLineEdit("https://api.deepseek.com/v1")
        advanced_form.addRow("Base URL", self.base_url_input)
        self.timeout_input = QSpinBox()
        self.timeout_input.setRange(1, 300)
        self.timeout_input.setValue(60)
        advanced_form.addRow("Timeout", self.timeout_input)
        self.ai_advanced_container.setVisible(False)
        layout.addWidget(self.ai_advanced_container)

        action_row = QHBoxLayout()
        self.generate_btn = QPushButton("生成卡片")
        self.generate_btn.setDefault(True)
        self.generate_btn.setMinimumSize(150, 40)
        self.generate_btn.setStyleSheet(
            "QPushButton { font-size: 15px; font-weight: bold; "
            "padding: 8px 22px; }"
        )
        self.generate_btn.clicked.connect(self._generate_cards)
        self.generation_status_label = QLabel()
        self.generation_status_label.setWordWrap(True)
        action_row.addWidget(self.generate_btn)
        action_row.addWidget(self.generation_status_label, 1)
        layout.addLayout(action_row)

        for widget in (
            self.model_input,
            self.api_key_input,
            self.base_url_input,
        ):
            widget.textChanged.connect(self._on_ai_settings_changed)
        self.timeout_input.valueChanged.connect(self._on_ai_settings_changed)
        return group

    def _build_cards_section(self):
        group = QGroupBox("生成的卡片")
        layout = QVBoxLayout(group)
        self.cards_empty_widget = QWidget()
        empty_layout = QVBoxLayout(self.cards_empty_widget)
        empty_layout.setContentsMargins(12, 16, 12, 16)
        empty_title = QLabel("还没有卡片")
        empty_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        empty_hint = QLabel("放入材料后点击“生成卡片”")
        empty_hint.setStyleSheet("color: #777;")
        empty_layout.addWidget(empty_title)
        empty_layout.addWidget(empty_hint)
        empty_layout.addStretch()
        layout.addWidget(self.cards_empty_widget)

        self.cards_scroll = QScrollArea()
        self.cards_scroll.setWidgetResizable(True)
        self.cards_scroll.setMinimumHeight(190)
        self.cards_scroll.setMaximumHeight(280)
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_scroll.setWidget(self.cards_container)
        self.cards_scroll.setVisible(False)
        layout.addWidget(self.cards_scroll)
        return group

    def _build_write_section(self):
        group = QGroupBox("写入 Anki")
        layout = QVBoxLayout(group)
        form = QFormLayout()

        self.deck_combo = QComboBox()
        self.deck_combo.currentIndexChanged.connect(self._on_deck_changed)
        form.addRow("目标牌组 Deck", self.deck_combo)

        self.note_type_combo = QComboBox()
        self.note_type_combo.currentIndexChanged.connect(
            self._on_note_type_changed
        )
        form.addRow("笔记类型 Note type", self.note_type_combo)

        self.front_field_combo = QComboBox()
        self.back_field_combo = QComboBox()
        self.source_field_combo = QComboBox()
        for combo in (
            self.front_field_combo,
            self.back_field_combo,
            self.source_field_combo,
        ):
            combo.currentIndexChanged.connect(self._on_mapping_changed)
        form.addRow("正面 →", self.front_field_combo)
        form.addRow("背面 →", self.back_field_combo)
        form.addRow("来源 →", self.source_field_combo)
        layout.addLayout(form)

        self.target_status_label = QLabel()
        self.target_status_label.setWordWrap(True)
        self.target_status_label.setStyleSheet("color: #777;")
        layout.addWidget(self.target_status_label)

        duplicate_row = QHBoxLayout()
        self.duplicate_btn = QPushButton("检查重复")
        self.duplicate_btn.clicked.connect(self._check_duplicates)
        self.duplicate_status_label = QLabel("未检查")
        duplicate_row.addWidget(self.duplicate_btn)
        duplicate_row.addWidget(self.duplicate_status_label)
        duplicate_row.addStretch()
        layout.addLayout(duplicate_row)

        write_row = QHBoxLayout()
        self.write_btn = QPushButton("写入 Anki")
        self.write_btn.setMinimumSize(140, 38)
        self.write_btn.setStyleSheet(
            "QPushButton { font-size: 14px; font-weight: bold; "
            "padding: 7px 18px; }"
        )
        self.write_btn.clicked.connect(self._confirm_and_write)
        self.write_status_label = QLabel()
        self.write_status_label.setWordWrap(True)
        write_row.addWidget(self.write_btn)
        write_row.addWidget(self.write_status_label, 1)
        layout.addLayout(write_row)
        return group

    def _choose_markdown_file(self):
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "选择 Markdown 文件",
            "",
            "Markdown Files (*.md)",
        )
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            self.generation_status_label.setText("无法读取该 Markdown 文件。")
            return
        self.material_input.setPlainText(text)

    def _use_example_material(self):
        self.session.load_example_material()
        self.material_input.blockSignals(True)
        self.material_input.setPlainText(self.session.material_text)
        self.material_input.blockSignals(False)
        self._after_upstream_change()

    def _on_material_changed(self):
        self.session.update_material(self.material_input.toPlainText())
        self._after_upstream_change()

    def _on_provider_changed(self, _index):
        provider_name, base_url = self.provider_combo.currentData()
        self.base_url_input.blockSignals(True)
        self.base_url_input.setText(base_url)
        self.base_url_input.blockSignals(False)
        self._on_ai_settings_changed()

    def _toggle_ai_advanced(self, expanded):
        self.ai_advanced_container.setVisible(expanded)
        self.ai_advanced_btn.setText(
            "收起高级设置" if expanded else "高级设置"
        )

    def _on_ai_settings_changed(self, *unused):
        self.session.mark_ai_runtime_settings_changed()
        self.generation_status_label.clear()
        self._after_upstream_change(render_material_count=False)

    def _ai_settings_are_ready(self):
        return all(
            (
                self.session.material_text.strip(),
                self.model_input.text().strip(),
                self.api_key_input.text().strip(),
                self.base_url_input.text().strip(),
            )
        )

    def _generate_cards(self):
        if not self._ai_settings_are_ready():
            self.generation_status_label.setText(
                "请先填写学习材料、Model 和 API key。"
            )
            return
        provider_name, _preset_url = self.provider_combo.currentData()
        try:
            settings = BeginnerAIProviderRuntimeSettings(
                provider_name=provider_name,
                base_url=self.base_url_input.text(),
                model=self.model_input.text(),
                api_key=self.api_key_input.text(),
                timeout_seconds=self.timeout_input.value(),
            )
        except ValueError:
            self.generation_status_label.setText(GENERATION_FAILURE_COPY)
            return

        self.session.begin_ai_candidate_generation()
        self._clear_generated_state()
        self._render_cards()
        self.generate_btn.setText("正在生成…")
        self.generate_btn.setEnabled(False)
        self.generation_status_label.setText("正在生成…")
        QApplication.processEvents()
        result = BeginnerAICardDraftGenerator().generate(
            settings=settings,
            material_text=self.session.material_text,
        )
        if not result.success:
            self.session.record_ai_card_draft_error(
                result.state,
                result.error_code.value,
            )
            self.generation_status_label.setText(GENERATION_FAILURE_COPY)
            self._refresh_product_state()
            return

        self.session.apply_ai_candidate_card_drafts(result.drafts)
        for card in self.session.candidate_card_previews:
            self.session.set_candidate_review_decision(
                card.id,
                BeginnerReviewDecision.LOOKS_GOOD,
            )
        self.generation_status_label.setText(
            f"已生成 {len(self.session.candidate_card_previews)} 张卡片。"
        )
        self._render_cards()
        self._refresh_product_state()

    def _render_cards(self):
        self._clear_layout(self.cards_layout)
        self.card_button_groups = {}
        cards = self.session.candidate_card_previews
        if not cards:
            self.cards_empty_widget.setVisible(True)
            self.cards_scroll.setVisible(False)
            return
        self.cards_empty_widget.setVisible(False)
        self.cards_scroll.setVisible(True)

        for index, card in enumerate(cards, start=1):
            card_group = QGroupBox(f"卡片 {index}")
            card_layout = QVBoxLayout(card_group)
            front = QLabel(f"正面：\n{card.front_preview}")
            back = QLabel(f"背面：\n{card.back_preview}")
            front.setWordWrap(True)
            back.setWordWrap(True)
            card_layout.addWidget(front)
            card_layout.addWidget(back)

            source_btn = QPushButton("来源")
            source_btn.setCheckable(True)
            source_btn.setFlat(True)
            source_label = QLabel(card.source_excerpt)
            source_label.setWordWrap(True)
            source_label.setVisible(False)
            source_btn.toggled.connect(source_label.setVisible)
            card_layout.addWidget(source_btn)
            card_layout.addWidget(source_label)

            actions = QHBoxLayout()
            group = QButtonGroup(card_group)
            keep_btn = QRadioButton("保留")
            discard_btn = QRadioButton("丢弃")
            edit_btn = QPushButton("编辑")
            current = self.session.candidate_review_decisions.get(card.id)
            keep_btn.setChecked(current is BeginnerReviewDecision.LOOKS_GOOD)
            discard_btn.setChecked(
                current is BeginnerReviewDecision.SKIP_FOR_NOW
            )
            keep_btn.toggled.connect(
                lambda checked, card_id=card.id: self._set_card_decision(
                    card_id,
                    BeginnerReviewDecision.LOOKS_GOOD,
                    checked,
                )
            )
            discard_btn.toggled.connect(
                lambda checked, card_id=card.id: self._set_card_decision(
                    card_id,
                    BeginnerReviewDecision.SKIP_FOR_NOW,
                    checked,
                )
            )
            edit_btn.clicked.connect(
                lambda _checked=False, card_id=card.id: self._edit_card(card_id)
            )
            group.addButton(keep_btn)
            group.addButton(discard_btn)
            actions.addWidget(keep_btn)
            actions.addWidget(edit_btn)
            actions.addWidget(discard_btn)
            actions.addStretch()
            card_layout.addLayout(actions)
            self.card_button_groups[card.id] = group
            self.cards_layout.addWidget(card_group)
        self.cards_layout.addStretch()

    def _set_card_decision(self, card_id, decision, checked):
        if not checked:
            return
        self.session.set_candidate_review_decision(card_id, decision)
        self._clear_duplicate_state()
        self._refresh_product_state()

    def _edit_card(self, card_id):
        card = next(
            item
            for item in self.session.candidate_card_previews
            if item.id == card_id
        )
        dialog = CardEditDialog(card.front_preview, card.back_preview, self)
        if not dialog.exec():
            return
        front, back = dialog.values()
        if not front or not back:
            return
        decisions = dict(self.session.candidate_review_decisions)
        drafts = []
        for item in self.session.candidate_card_previews:
            draft_id = item.id.removeprefix("candidate-")
            drafts.append(
                BeginnerAICardDraft(
                    id=draft_id,
                    front=front if item.id == card_id else item.front_preview,
                    back=back if item.id == card_id else item.back_preview,
                    source_excerpt=item.source_excerpt,
                )
            )
        self.session.apply_ai_candidate_card_drafts(tuple(drafts))
        for item in self.session.candidate_card_previews:
            self.session.set_candidate_review_decision(
                item.id,
                decisions.get(item.id, BeginnerReviewDecision.LOOKS_GOOD),
            )
        self._clear_duplicate_state()
        self._render_cards()
        self._refresh_product_state()

    def _read_anki_targets(self):
        self.session.clear_anki_target_selection()
        self.anki_mapping = None
        self.anki_field_snapshot = None
        snapshot = self.anki_target_adapter.read_targets()
        self.anki_target_snapshot = snapshot
        self.target_status_label.setText(
            "" if snapshot.state is BeginnerAnkiReadState.SUCCESS
            else "无法读取 Anki 牌组或笔记类型。"
        )
        self._populate_target_options(snapshot)

    def _populate_target_options(self, snapshot):
        for combo in (self.deck_combo, self.note_type_combo):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("请选择", None)
        for deck in snapshot.decks:
            self.deck_combo.addItem(deck.name, deck.id)
        for note_type in snapshot.note_types:
            self.note_type_combo.addItem(note_type.name, note_type.id)
        for combo in (self.deck_combo, self.note_type_combo):
            combo.setCurrentIndex(0)
            combo.blockSignals(False)
        self._clear_field_options()

    def _on_deck_changed(self, _index):
        deck = self._selected_deck()
        if deck is None:
            self.session.clear_anki_deck_selection()
        else:
            self.session.select_anki_deck(deck.id, deck.name)
        self._update_mapping()

    def _on_note_type_changed(self, _index):
        note_type = self._selected_note_type()
        if note_type is None:
            self.session.clear_anki_note_type_selection()
            self.anki_field_snapshot = None
            self._clear_field_options()
            self._update_mapping()
            return
        snapshot = self.anki_target_adapter.read_fields(note_type.id)
        self.anki_field_snapshot = snapshot
        if snapshot.state is not BeginnerAnkiReadState.SUCCESS:
            self.target_status_label.setText("无法读取笔记类型字段。")
            self._clear_field_options()
            self._update_mapping()
            return
        self.target_status_label.clear()
        self.session.select_anki_note_type(
            note_type.id,
            note_type.name,
            snapshot.fields,
        )
        self._populate_field_options(snapshot.fields)
        self._update_mapping()

    def _populate_field_options(self, fields):
        for combo in (
            self.front_field_combo,
            self.back_field_combo,
            self.source_field_combo,
        ):
            combo.blockSignals(True)
            combo.clear()
        self.front_field_combo.addItem("请选择", None)
        self.back_field_combo.addItem("请选择", None)
        self.source_field_combo.addItem("不使用", None)
        for field_name in fields:
            self.front_field_combo.addItem(field_name, field_name)
            self.back_field_combo.addItem(field_name, field_name)
            self.source_field_combo.addItem(field_name, field_name)
        self._select_field(self.front_field_combo, ("front",))
        self._select_field(self.back_field_combo, ("back",))
        self._select_field(self.source_field_combo, ("extra", "source"))
        for combo in (
            self.front_field_combo,
            self.back_field_combo,
            self.source_field_combo,
        ):
            combo.blockSignals(False)

    def _clear_field_options(self):
        for combo in (
            self.front_field_combo,
            self.back_field_combo,
            self.source_field_combo,
        ):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("请选择", None)
            combo.blockSignals(False)

    @staticmethod
    def _select_field(combo, candidates):
        for index in range(combo.count()):
            value = combo.itemData(index)
            if isinstance(value, str) and value.casefold() in candidates:
                combo.setCurrentIndex(index)
                return

    def _on_mapping_changed(self, _index):
        self._update_mapping()

    def _update_mapping(self):
        self._clear_duplicate_state()
        deck = self._selected_deck()
        note_type = self._selected_note_type()
        front_field = self.front_field_combo.currentData()
        back_field = self.back_field_combo.currentData()
        source_field = self.source_field_combo.currentData()
        if (
            deck is None
            or note_type is None
            or self.anki_field_snapshot is None
            or self.anki_field_snapshot.state is not BeginnerAnkiReadState.SUCCESS
            or not front_field
            or not back_field
        ):
            self.anki_mapping = None
            self._refresh_product_state()
            return
        self.session.set_anki_field_mapping(
            front_field,
            back_field,
            source_field,
        )
        self.anki_mapping = build_beginner_field_mapping_preview(
            deck=deck,
            note_type=note_type,
            available_fields=self.anki_field_snapshot.fields,
            front_field=front_field,
            back_field=back_field,
            source_field=source_field,
        )
        self._refresh_product_state()

    def _check_duplicates(self):
        if not self.session.candidate_card_previews or self.anki_mapping is None:
            self.duplicate_status_label.setText("未检查")
            return
        self.session.begin_duplicate_check()
        results = self.duplicate_check_adapter.check(
            self.session.candidate_card_previews,
            self.anki_mapping,
        )
        self.duplicate_results = results
        if results.state is not BeginnerDuplicatePreviewState.SUCCESS:
            self.session.record_duplicate_check_error("collection_read_failed")
            self.duplicate_status_label.setText("未检查")
            self._refresh_product_state()
            return
        duplicate_count = sum(
            item.status is BeginnerDuplicateStatus.POSSIBLE_DUPLICATE
            for item in results.results
        )
        self.session.apply_duplicate_check_preview(
            len(results.results),
            duplicate_count,
        )
        self.duplicate_status_label.setText(
            "未发现重复" if duplicate_count == 0 else "可能重复，已跳过"
        )
        self._prepare_current_write()
        self._refresh_product_state()

    def _prepare_current_write(self):
        summary = build_beginner_final_confirmation_preview(
            self.session,
            self.anki_mapping,
            self.duplicate_results,
        )
        self.write_summary = summary
        self.session.apply_final_confirmation_preview(
            summary.candidate_count,
            len(summary.missing_conditions),
        )
        preparation = prepare_beginner_write(
            self.session,
            summary,
            self.anki_mapping,
            self.duplicate_results,
        )
        self.write_preparation = preparation
        self.write_command = preparation.command
        return preparation

    def _confirm_and_write(self):
        preparation = self._prepare_current_write()
        command = preparation.command
        if command is None:
            self.write_status_label.setText(WRITE_FAILURE_COPY)
            self._refresh_product_state()
            return

        message_box = QMessageBox(self)
        message_box.setWindowTitle("确认写入 Anki？")
        message_box.setText(
            f"将写入 {command.requested_count} 张卡片到「{command.deck_name}」。"
        )
        roles = getattr(QMessageBox, "ButtonRole", QMessageBox)
        message_box.addButton("取消", roles.RejectRole)
        confirm_button = message_box.addButton("确认写入", roles.AcceptRole)
        message_box.exec()
        confirmed = message_box.clickedButton() is confirm_button
        if not confirmed:
            self.write_status_label.setText("已取消。")
            return

        self.session.begin_write(
            command.snapshot_id,
            command.requested_count,
            command.skipped_count,
        )
        self.write_btn.setText("正在写入…")
        self.write_btn.setEnabled(False)
        QApplication.processEvents()
        result = execute_beginner_write_if_confirmed(
            True,
            self.writer,
            command,
        )
        self.session.record_write_result(
            result.snapshot_id,
            result.created_note_ids,
            result.skipped_count,
            result.failed_count,
        )
        self.write_result = result
        if result.success_count and not result.failed_count:
            message = (
                f"已写入 {result.success_count} 张卡片，可以到 Anki 中查看。"
            )
        elif result.success_count:
            message = (
                f"已写入 {result.success_count} 张，{result.failed_count} 张失败。"
                "请检查失败项后重试。"
            )
        else:
            message = WRITE_FAILURE_COPY
        self.write_status_label.setText(message)
        self._refresh_product_state()

    def _after_upstream_change(self, render_material_count=True):
        if render_material_count:
            self.material_count_label.setText(
                f"{self.session.material_char_count} 字符"
            )
        self._clear_generated_state()
        self._render_cards()
        self._refresh_product_state()

    def _clear_generated_state(self):
        self._clear_duplicate_state()
        self.write_status_label.clear()

    def _clear_duplicate_state(self):
        self.duplicate_results = None
        self.write_summary = None
        self.write_preparation = None
        self.write_command = None
        self.write_result = None
        self.duplicate_status_label.setText("未检查")

    def _refresh_product_state(self):
        self.material_count_label.setText(
            f"{self.session.material_char_count} 字符"
        )
        self.generate_btn.setText("生成卡片")
        self.generate_btn.setEnabled(self._ai_settings_are_ready())
        has_cards = bool(self.session.candidate_card_previews)
        self.duplicate_btn.setEnabled(
            has_cards and self.anki_mapping is not None
        )
        command = self.write_command
        if self.session.write_state is BeginnerWriteState.WRITING:
            self.write_btn.setText("正在写入…")
            self.write_btn.setEnabled(False)
        elif command is not None and self.session.has_completed_write_snapshot(
            command.snapshot_id
        ):
            self.write_btn.setText("已写入，请在 Anki 中查看")
            self.write_btn.setEnabled(False)
        else:
            self.write_btn.setText("写入 Anki")
            self.write_btn.setEnabled(
                bool(
                    self.write_preparation
                    and self.write_preparation.can_write
                )
            )

    def _selected_deck(self):
        if self.anki_target_snapshot is None:
            return None
        selected_id = self.deck_combo.currentData()
        return next(
            (
                deck
                for deck in self.anki_target_snapshot.decks
                if deck.id == selected_id
            ),
            None,
        )

    def _selected_note_type(self):
        if self.anki_target_snapshot is None:
            return None
        selected_id = self.note_type_combo.currentData()
        return next(
            (
                note_type
                for note_type in self.anki_target_snapshot.note_types
                if note_type.id == selected_id
            ),
            None,
        )

    def discard_session(self):
        self.material_input.blockSignals(True)
        self.material_input.clear()
        self.material_input.blockSignals(False)
        self.api_key_input.blockSignals(True)
        self.api_key_input.clear()
        self.api_key_input.blockSignals(False)
        if not self.session.closed:
            self.session.close()
        self.anki_target_snapshot = None
        self.anki_field_snapshot = None
        self.anki_mapping = None
        self.duplicate_results = None
        self.write_summary = None
        self.write_preparation = None
        self.write_command = None
        self.write_result = None

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()


class CardEditDialog(QDialog):
    def __init__(self, front, back, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑卡片")
        self.resize(560, 420)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.front_input = QTextEdit(front)
        self.back_input = QTextEdit(back)
        form.addRow("正面", self.front_input)
        form.addRow("背面", self.back_input)
        layout.addLayout(form)
        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        done_btn = QPushButton("完成修改")
        done_btn.clicked.connect(self.accept)
        buttons.addWidget(cancel_btn)
        buttons.addWidget(done_btn)
        layout.addLayout(buttons)

    def values(self):
        return (
            self.front_input.toPlainText().strip(),
            self.back_input.toPlainText().strip(),
        )
