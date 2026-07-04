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
from .product_i18n import DEFAULT_PRODUCT_LANGUAGE, product_text


class CardMakerPanel(QWidget):
    """One disposable, single-screen card-making session."""

    def __init__(
        self,
        parent=None,
        collection=None,
        language=DEFAULT_PRODUCT_LANGUAGE,
    ):
        super().__init__(parent)
        self.language = language
        self._generation_message = None
        self._target_message = None
        self._write_message = None
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

    def t(self, key, **values):
        return product_text(self.language, key, **values)

    def set_language(self, language):
        if language == self.language:
            return
        product_text(language, "title")
        self.language = language
        self._retranslate_ui()

    def _retranslate_ui(self):
        self.material_group.setTitle(self.t("material_section"))
        self.material_help_label.setText(self.t("material_help"))
        self.material_input.setPlaceholderText(self.t("material_placeholder"))
        self.choose_markdown_btn.setText(self.t("choose_markdown"))
        self.example_btn.setText(self.t("use_example"))

        self.ai_group.setTitle(self.t("ai_section"))
        self.provider_label.setText(self.t("provider"))
        self.model_label.setText(self.t("model"))
        self.model_input.setPlaceholderText(self.t("model_placeholder"))
        self.api_key_label.setText(self.t("api_key"))
        self.api_key_input.setPlaceholderText(self.t("api_key_placeholder"))
        self.api_key_help_label.setText(self.t("api_key_help"))
        self.base_url_label.setText(self.t("base_url"))
        self.timeout_label.setText(self.t("timeout"))
        self._toggle_ai_advanced(self.ai_advanced_btn.isChecked())

        self.cards_group.setTitle(self.t("cards_section"))
        self.empty_cards_title.setText(self.t("no_cards"))
        self.empty_cards_help.setText(self.t("no_cards_help"))

        self.write_group.setTitle(self.t("write_section"))
        self.deck_label.setText(self.t("deck"))
        self.note_type_label.setText(self.t("note_type"))
        self.front_mapping_label.setText(self.t("front_mapping"))
        self.back_mapping_label.setText(self.t("back_mapping"))
        self.source_mapping_label.setText(self.t("source_mapping"))
        self.duplicate_btn.setText(self.t("check_duplicates"))
        self._retranslate_combo_placeholders()
        self._render_cards()
        self._render_status_messages()
        self._refresh_product_state()

    def _retranslate_combo_placeholders(self):
        for combo in (self.deck_combo, self.note_type_combo):
            if combo.count():
                combo.setItemText(0, self.t("select"))
        for combo in (self.front_field_combo, self.back_field_combo):
            if combo.count():
                combo.setItemText(0, self.t("select"))
        if self.source_field_combo.count():
            self.source_field_combo.setItemText(0, self.t("no_source"))

    def _set_generation_message(self, key=None, **values):
        self._generation_message = (key, values) if key else None
        self._render_generation_message()

    def _render_generation_message(self):
        if self._generation_message is None:
            self.generation_status_label.clear()
            return
        key, values = self._generation_message
        message = self.t(key, **values)
        if key == "generation_failed":
            message += "\n" + self.t("model_failure_help")
        self.generation_status_label.setText(message)

    def _set_target_message(self, key=None, **values):
        self._target_message = (key, values) if key else None
        if self._target_message is None:
            self.target_status_label.clear()
            return
        self.target_status_label.setText(self.t(key, **values))

    def _set_write_message(self, key=None, **values):
        self._write_message = (key, values) if key else None
        if self._write_message is None:
            self.write_status_label.clear()
            return
        self.write_status_label.setText(self.t(key, **values))

    def _render_status_messages(self):
        self._render_generation_message()
        if self._target_message is None:
            self.target_status_label.clear()
        else:
            key, values = self._target_message
            self.target_status_label.setText(self.t(key, **values))
        if self._write_message is None:
            self.write_status_label.clear()
        else:
            key, values = self._write_message
            self.write_status_label.setText(self.t(key, **values))
        self._refresh_duplicate_copy()

    def _refresh_duplicate_copy(self):
        if (
            self.duplicate_results is None
            or self.duplicate_results.state
            is not BeginnerDuplicatePreviewState.SUCCESS
        ):
            key = "duplicates_unchecked"
        elif any(
            item.status is BeginnerDuplicateStatus.POSSIBLE_DUPLICATE
            for item in self.duplicate_results.results
        ):
            key = "duplicates_skipped"
        else:
            key = "duplicates_clear"
        self.duplicate_status_label.setText(self.t(key))

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
        self.material_group = QGroupBox(self.t("material_section"))
        layout = QVBoxLayout(self.material_group)
        self.material_help_label = QLabel(self.t("material_help"))
        self.material_help_label.setStyleSheet("color: #666;")
        layout.addWidget(self.material_help_label)

        self.material_input = QTextEdit()
        self.material_input.setPlaceholderText(self.t("material_placeholder"))
        self.material_input.setMinimumHeight(150)
        self.material_input.setMaximumHeight(230)
        self.material_input.textChanged.connect(self._on_material_changed)
        layout.addWidget(self.material_input)

        actions = QHBoxLayout()
        self.choose_markdown_btn = QPushButton(self.t("choose_markdown"))
        self.choose_markdown_btn.clicked.connect(self._choose_markdown_file)
        self.example_btn = QPushButton(self.t("use_example"))
        self.example_btn.clicked.connect(self._use_example_material)
        self.material_count_label = QLabel(self.t("character_count", count=0))
        self.material_count_label.setStyleSheet("color: #777;")
        actions.addWidget(self.choose_markdown_btn)
        actions.addWidget(self.example_btn)
        actions.addStretch()
        actions.addWidget(self.material_count_label)
        layout.addLayout(actions)
        return self.material_group

    def _build_ai_section(self):
        self.ai_group = QGroupBox(self.t("ai_section"))
        layout = QVBoxLayout(self.ai_group)
        layout.setSpacing(8)
        compact = QGridLayout()
        compact.setHorizontalSpacing(8)
        compact.setVerticalSpacing(8)

        self.provider_combo = QComboBox()
        self.provider_combo.addItem(
            "DeepSeek",
            ("DeepSeek", "https://api.deepseek.com", "deepseek-v4-flash"),
        )
        self.provider_combo.addItem(
            "OpenAI",
            ("OpenAI", "https://api.openai.com/v1", "gpt-4o-mini"),
        )
        self.provider_combo.addItem(
            "OpenAI-compatible",
            ("OpenAI-compatible", "", ""),
        )
        self.provider_combo.currentIndexChanged.connect(
            self._on_provider_changed
        )
        self.provider_label = QLabel(self.t("provider"))
        compact.addWidget(self.provider_label, 0, 0)
        compact.addWidget(self.provider_combo, 0, 1)

        self.model_input = QLineEdit("deepseek-v4-flash")
        self.model_input.setPlaceholderText(self.t("model_placeholder"))
        self.model_label = QLabel(self.t("model"))
        compact.addWidget(self.model_label, 0, 2)
        compact.addWidget(self.model_input, 0, 3)

        self.api_key_input = QLineEdit()
        password_mode = (
            QLineEdit.EchoMode.Password
            if hasattr(QLineEdit, "EchoMode")
            else QLineEdit.Password
        )
        self.api_key_input.setEchoMode(password_mode)
        self.api_key_input.setPlaceholderText(self.t("api_key_placeholder"))
        self.api_key_label = QLabel(self.t("api_key"))
        compact.addWidget(self.api_key_label, 1, 0)
        compact.addWidget(self.api_key_input, 1, 1, 1, 3)
        compact.setColumnStretch(1, 1)
        compact.setColumnStretch(3, 1)
        layout.addLayout(compact)

        self.api_key_help_label = QLabel(self.t("api_key_help"))
        self.api_key_help_label.setStyleSheet("color: #666;")
        layout.addWidget(self.api_key_help_label)

        self.ai_advanced_btn = QPushButton(self.t("advanced_settings"))
        self.ai_advanced_btn.setCheckable(True)
        self.ai_advanced_btn.setFlat(True)
        self.ai_advanced_btn.toggled.connect(self._toggle_ai_advanced)
        layout.addWidget(self.ai_advanced_btn, 0)

        self.ai_advanced_container = QWidget()
        advanced_form = QFormLayout(self.ai_advanced_container)
        advanced_form.setContentsMargins(18, 0, 0, 0)
        self.base_url_input = QLineEdit("https://api.deepseek.com")
        self.base_url_label = QLabel(self.t("base_url"))
        advanced_form.addRow(self.base_url_label, self.base_url_input)
        self.timeout_input = QSpinBox()
        self.timeout_input.setRange(1, 300)
        self.timeout_input.setValue(60)
        self.timeout_label = QLabel(self.t("timeout"))
        advanced_form.addRow(self.timeout_label, self.timeout_input)
        self.ai_advanced_container.setVisible(False)
        layout.addWidget(self.ai_advanced_container)

        action_row = QHBoxLayout()
        self.generate_btn = QPushButton(self.t("generate_cards"))
        self.generate_btn.setDefault(True)
        self.generate_btn.setMinimumSize(150, 40)
        self.generate_btn.setStyleSheet(
            "QPushButton { background: #2563eb; color: white; border: none; "
            "border-radius: 6px; font-size: 15px; font-weight: bold; "
            "padding: 8px 22px; } "
            "QPushButton:hover { background: #1d4ed8; } "
            "QPushButton:disabled { background: #9ca3af; color: #f3f4f6; }"
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
        return self.ai_group

    def _build_cards_section(self):
        self.cards_group = QGroupBox(self.t("cards_section"))
        layout = QVBoxLayout(self.cards_group)
        self.cards_empty_widget = QWidget()
        empty_layout = QVBoxLayout(self.cards_empty_widget)
        empty_layout.setContentsMargins(12, 16, 12, 16)
        self.empty_cards_title = QLabel(self.t("no_cards"))
        self.empty_cards_title.setStyleSheet(
            "font-size: 15px; font-weight: bold;"
        )
        self.empty_cards_help = QLabel(self.t("no_cards_help"))
        self.empty_cards_help.setStyleSheet("color: #777;")
        empty_layout.addWidget(self.empty_cards_title)
        empty_layout.addWidget(self.empty_cards_help)
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
        return self.cards_group

    def _build_write_section(self):
        self.write_group = QGroupBox(self.t("write_section"))
        layout = QVBoxLayout(self.write_group)
        form = QFormLayout()

        self.deck_combo = QComboBox()
        self.deck_combo.currentIndexChanged.connect(self._on_deck_changed)
        self.deck_label = QLabel(self.t("deck"))
        form.addRow(self.deck_label, self.deck_combo)

        self.note_type_combo = QComboBox()
        self.note_type_combo.currentIndexChanged.connect(
            self._on_note_type_changed
        )
        self.note_type_label = QLabel(self.t("note_type"))
        form.addRow(self.note_type_label, self.note_type_combo)

        self.front_field_combo = QComboBox()
        self.back_field_combo = QComboBox()
        self.source_field_combo = QComboBox()
        for combo in (
            self.front_field_combo,
            self.back_field_combo,
            self.source_field_combo,
        ):
            combo.currentIndexChanged.connect(self._on_mapping_changed)
        self.front_mapping_label = QLabel(self.t("front_mapping"))
        self.back_mapping_label = QLabel(self.t("back_mapping"))
        self.source_mapping_label = QLabel(self.t("source_mapping"))
        form.addRow(self.front_mapping_label, self.front_field_combo)
        form.addRow(self.back_mapping_label, self.back_field_combo)
        form.addRow(self.source_mapping_label, self.source_field_combo)
        layout.addLayout(form)

        self.target_status_label = QLabel()
        self.target_status_label.setWordWrap(True)
        self.target_status_label.setStyleSheet("color: #777;")
        layout.addWidget(self.target_status_label)

        duplicate_row = QHBoxLayout()
        self.duplicate_btn = QPushButton(self.t("check_duplicates"))
        self.duplicate_btn.clicked.connect(self._check_duplicates)
        self.duplicate_status_label = QLabel(self.t("duplicates_unchecked"))
        duplicate_row.addWidget(self.duplicate_btn)
        duplicate_row.addWidget(self.duplicate_status_label)
        duplicate_row.addStretch()
        layout.addLayout(duplicate_row)

        write_row = QHBoxLayout()
        self.write_btn = QPushButton(self.t("write_to_anki"))
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
        return self.write_group

    def _choose_markdown_file(self):
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            self.t("choose_markdown"),
            "",
            self.t("markdown_filter"),
        )
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            self._set_generation_message("markdown_read_failed")
            return
        self.material_input.setPlainText(text)

    def _use_example_material(self):
        self.session.load_example_material()
        self.material_input.blockSignals(True)
        self.material_input.setPlainText(self.session.material_text)
        self.material_input.blockSignals(False)
        self._set_generation_message()
        self._after_upstream_change()

    def _on_material_changed(self):
        self.session.update_material(self.material_input.toPlainText())
        self._set_generation_message()
        self._after_upstream_change()

    def _on_provider_changed(self, _index):
        _provider_name, base_url, suggested_model = (
            self.provider_combo.currentData()
        )
        previous_model = self.model_input.text().strip()
        self.base_url_input.blockSignals(True)
        self.base_url_input.setText(base_url)
        self.base_url_input.blockSignals(False)
        if previous_model in {
            "",
            "deepseek-v4-flash",
            "gpt-4o-mini",
        }:
            self.model_input.blockSignals(True)
            self.model_input.setText(suggested_model)
            self.model_input.blockSignals(False)
        self._on_ai_settings_changed()

    def _toggle_ai_advanced(self, expanded):
        self.ai_advanced_container.setVisible(expanded)
        self.ai_advanced_btn.setText(
            self.t("advanced_settings_collapse")
            if expanded
            else self.t("advanced_settings")
        )

    def _on_ai_settings_changed(self, *unused):
        self.session.mark_ai_runtime_settings_changed()
        self._set_generation_message()
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
            self._set_generation_message("generation_requirements")
            return
        provider_name, _preset_url, _suggested_model = (
            self.provider_combo.currentData()
        )
        try:
            settings = BeginnerAIProviderRuntimeSettings(
                provider_name=provider_name,
                base_url=self.base_url_input.text(),
                model=self.model_input.text(),
                api_key=self.api_key_input.text(),
                timeout_seconds=self.timeout_input.value(),
            )
        except ValueError:
            self._set_generation_message("generation_failed")
            return

        self.session.begin_ai_candidate_generation()
        self._clear_generated_state()
        self._render_cards()
        self.generate_btn.setText(self.t("generation_running"))
        self.generate_btn.setEnabled(False)
        self._set_generation_message("generation_running")
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
            self._set_generation_message("generation_failed")
            self._refresh_product_state()
            return

        self.session.apply_ai_candidate_card_drafts(result.drafts)
        for card in self.session.candidate_card_previews:
            self.session.set_candidate_review_decision(
                card.id,
                BeginnerReviewDecision.LOOKS_GOOD,
            )
        self._set_generation_message(
            "generation_success",
            count=len(self.session.candidate_card_previews),
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
            card_group = QGroupBox(self.t("card_number", number=index))
            card_layout = QVBoxLayout(card_group)
            front = QLabel(f"{self.t('front')}:\n{card.front_preview}")
            back = QLabel(f"{self.t('back')}:\n{card.back_preview}")
            front.setWordWrap(True)
            back.setWordWrap(True)
            card_layout.addWidget(front)
            card_layout.addWidget(back)

            source_btn = QPushButton(self.t("source"))
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
            keep_btn = QRadioButton(self.t("keep"))
            discard_btn = QRadioButton(self.t("discard"))
            edit_btn = QPushButton(self.t("edit"))
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
        dialog = CardEditDialog(
            card.front_preview,
            card.back_preview,
            self.language,
            self,
        )
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
        self._set_target_message(
            None
            if snapshot.state is BeginnerAnkiReadState.SUCCESS
            else "target_read_failed"
        )
        self._populate_target_options(snapshot)

    def _populate_target_options(self, snapshot):
        for combo in (self.deck_combo, self.note_type_combo):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(self.t("select"), None)
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
            self._set_target_message("field_read_failed")
            self._clear_field_options()
            self._update_mapping()
            return
        self._set_target_message()
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
        self.front_field_combo.addItem(self.t("select"), None)
        self.back_field_combo.addItem(self.t("select"), None)
        self.source_field_combo.addItem(self.t("no_source"), None)
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
            combo.addItem(self.t("select"), None)
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
            self._refresh_duplicate_copy()
            return
        self.session.begin_duplicate_check()
        results = self.duplicate_check_adapter.check(
            self.session.candidate_card_previews,
            self.anki_mapping,
        )
        self.duplicate_results = results
        if results.state is not BeginnerDuplicatePreviewState.SUCCESS:
            self.session.record_duplicate_check_error("collection_read_failed")
            self._refresh_duplicate_copy()
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
        self._refresh_duplicate_copy()
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
            self._set_write_message("write_failed")
            self._refresh_product_state()
            return

        message_box = QMessageBox(self)
        message_box.setWindowTitle(self.t("confirm_write_title"))
        message_box.setText(
            self.t(
                "confirm_write_body",
                count=command.requested_count,
                deck=command.deck_name,
            )
        )
        roles = getattr(QMessageBox, "ButtonRole", QMessageBox)
        message_box.addButton(self.t("cancel"), roles.RejectRole)
        confirm_button = message_box.addButton(
            self.t("confirm_write"),
            roles.AcceptRole,
        )
        message_box.exec()
        confirmed = message_box.clickedButton() is confirm_button
        if not confirmed:
            self._set_write_message("write_cancelled")
            return

        self.session.begin_write(
            command.snapshot_id,
            command.requested_count,
            command.skipped_count,
        )
        self.write_btn.setText(self.t("write_running"))
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
            self._set_write_message(
                "write_success",
                count=result.success_count,
            )
        elif result.success_count:
            self._set_write_message(
                "write_partial",
                success=result.success_count,
                failed=result.failed_count,
            )
        else:
            self._set_write_message("write_failed")
        self._refresh_product_state()

    def _after_upstream_change(self, render_material_count=True):
        if render_material_count:
            self.material_count_label.setText(
                self.t(
                    "character_count",
                    count=self.session.material_char_count,
                )
            )
        self._clear_generated_state()
        self._render_cards()
        self._refresh_product_state()

    def _clear_generated_state(self):
        self._clear_duplicate_state()
        self._set_write_message()

    def _clear_duplicate_state(self):
        self.duplicate_results = None
        self.write_summary = None
        self.write_preparation = None
        self.write_command = None
        self.write_result = None
        self._refresh_duplicate_copy()

    def _refresh_product_state(self):
        self.material_count_label.setText(
            self.t(
                "character_count",
                count=self.session.material_char_count,
            )
        )
        self.generate_btn.setText(
            self.t("regenerate_cards")
            if self.session.candidate_card_previews
            else self.t("generate_cards")
        )
        self.generate_btn.setEnabled(self._ai_settings_are_ready())
        has_cards = bool(self.session.candidate_card_previews)
        self.duplicate_btn.setEnabled(
            has_cards and self.anki_mapping is not None
        )
        command = self.write_command
        if self.session.write_state is BeginnerWriteState.WRITING:
            self.write_btn.setText(self.t("write_running"))
            self.write_btn.setEnabled(False)
        elif command is not None and self.session.has_completed_write_snapshot(
            command.snapshot_id
        ):
            self.write_btn.setText(self.t("write_completed_button"))
            self.write_btn.setEnabled(False)
        else:
            self.write_btn.setText(self.t("write_to_anki"))
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
    def __init__(self, front, back, language, parent=None):
        super().__init__(parent)
        self.language = language
        self.setWindowTitle(product_text(language, "edit_card"))
        self.resize(560, 420)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.front_input = QTextEdit(front)
        self.back_input = QTextEdit(back)
        form.addRow(product_text(language, "front"), self.front_input)
        form.addRow(product_text(language, "back"), self.back_input)
        layout.addLayout(form)
        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel_btn = QPushButton(product_text(language, "cancel"))
        cancel_btn.clicked.connect(self.reject)
        done_btn = QPushButton(product_text(language, "finish_edit"))
        done_btn.clicked.connect(self.accept)
        buttons.addWidget(cancel_btn)
        buttons.addWidget(done_btn)
        layout.addLayout(buttons)

    def values(self):
        return (
            self.front_input.toPlainText().strip(),
            self.back_input.toPlainText().strip(),
        )
