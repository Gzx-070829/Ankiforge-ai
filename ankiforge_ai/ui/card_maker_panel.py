"""Single-screen product panel for turning study material into Anki cards."""

from pathlib import Path

from aqt.qt import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QTextEdit,
    Qt,
    QVBoxLayout,
    QWidget,
)

from ..anki_writer.minimal_write import MinimalAnkiWriter
from ..importers.source_import import (
    ImportedSource,
    SourceImportError,
    import_source_file,
    merge_imported_source_text,
)
from ..pipeline.generation_settings import GenerationSettings
from ..pipeline.write_traceability import (
    LastWriteBatchRecord,
    SourceType,
    build_write_result_summary,
    build_write_summary,
    safe_source_label,
    source_type_from_path,
)
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
from .file_drop_text_edit import FileDropTextEdit
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


SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 12
SPACING_LG = 16
COLUMN_GAP = 24
FORM_LABEL_WIDTH = 96
CONTROL_HEIGHT = 40
BUTTON_HEIGHT = 36
PRIMARY_BUTTON_HEIGHT = 44
SECTION_PADDING = 18


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
        self._source_import_message = None
        self._source_import_warning_keys = ()
        self._applying_source_import = False
        self.session = BeginnerFlowSession()
        self.anki_target_adapter = ReadOnlyAnkiTargetAdapter(collection)
        self.duplicate_check_adapter = ReadOnlyDuplicateCheckAdapter(collection)
        self.writer = MinimalAnkiWriter(collection)
        self.anki_target_snapshot = None
        self.anki_field_snapshot = None
        self.anki_mapping = None
        self.duplicate_results = None
        self.write_summary = None
        self.final_confirmation_preview = None
        self.write_result_summary = None
        self.write_preparation = None
        self.write_command = None
        self.write_result = None
        self.card_button_groups = {}
        self._ai_runtime_settings = None

        self.setObjectName("CardMakerPanel")
        self.setMaximumWidth(1280)
        self._build_ui()
        self._read_anki_targets()
        self._render_cards()
        self._refresh_product_state()

    def t(self, key, **values):
        return product_text(self.language, key, **values)

    def ai_runtime_settings(self):
        return self._ai_runtime_settings

    def set_ai_runtime_settings(self, settings):
        if not isinstance(settings, BeginnerAIProviderRuntimeSettings):
            raise TypeError(
                "settings must be BeginnerAIProviderRuntimeSettings"
            )
        self._ai_runtime_settings = settings
        self.session.mark_ai_runtime_settings_changed()
        self._set_generation_message()
        self._after_upstream_change(render_material_count=False)

    def clear_ai_runtime_settings(self):
        self._ai_runtime_settings = None
        self.session.mark_ai_runtime_settings_changed()
        self._set_generation_message()
        self._after_upstream_change(render_material_count=False)

    def set_language(self, language):
        if language == self.language:
            return
        product_text(language, "title")
        self.language = language
        self._retranslate_ui()

    def _retranslate_ui(self):
        self.material_title_label.setText(self.t("material_section"))
        self.material_help_label.setText(self.t("material_help"))
        self.material_input.setPlaceholderText(self.t("material_placeholder"))
        self.choose_file_btn.setText(self.t("choose_file"))
        self.example_btn.setText(self.t("use_example"))
        self._render_source_import_feedback()

        self.generation_title_label.setText(self.t("generation_settings"))
        self.create_panel_title.setText(self.t("create_cards_section"))
        self.card_mode_label.setText(self.t("card_mode"))
        self._retranslate_generation_settings()

        self.cards_title_label.setText(self.t("cards_section"))
        self.review_panel_title.setText(self.t("cards_section"))
        self.empty_cards_title.setText(self.t("no_cards"))
        self.empty_cards_help.setText(self.t("no_cards_help"))
        self.review_required_label.setText(self.t("review_required"))
        self.discard_blocking_btn.setText(self.t("discard_blocking"))

        self.write_title_label.setText(self.t("write_section"))
        self.deck_label.setText(self.t("deck"))
        self.note_type_label.setText(self.t("note_type"))
        self.front_mapping_label.setText(self.t("front_mapping"))
        self.back_mapping_label.setText(self.t("back_mapping"))
        self.source_mapping_label.setText(self.t("source_mapping"))
        self.duplicate_btn.setText(self.t("check_duplicates"))
        self._retranslate_combo_placeholders()
        self._render_cards()
        self._render_write_summary()
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

    def _retranslate_generation_settings(self):
        for combo, keys in (
            (
                self.card_mode_combo,
                (
                    "mode_concept",
                    "mode_definition",
                    "mode_exam",
                    "mode_quick_review",
                ),
            ),
            (
                self.card_count_combo,
                (
                    "card_count_auto",
                    "card_count_fewer",
                    "card_count_balanced",
                    "card_count_more",
                ),
            ),
            (
                self.answer_length_combo,
                ("answer_length_short", "answer_length_medium"),
            ),
            (
                self.output_language_combo,
                (
                    "output_language_auto",
                    "output_language_zh",
                    "output_language_en",
                ),
            ),
        ):
            for index, key in enumerate(keys):
                combo.setItemText(index, self.t(key))
        self.card_count_label.setText(self.t("card_count"))
        self.answer_length_label.setText(self.t("answer_length"))
        self.output_language_label.setText(self.t("output_language"))
        self._toggle_generation_settings(
            self.generation_settings_btn.isChecked()
        )
        self._update_card_mode_description()

    def _set_generation_message(self, key=None, **values):
        self._generation_message = (key, values) if key else None
        self._render_generation_message()

    @staticmethod
    def _set_status_role(label, role):
        """Refresh a label after changing its lightweight visual role."""

        if label.property("role") == role:
            return
        label.setProperty("role", role)
        label.style().unpolish(label)
        label.style().polish(label)
        label.update()

    def _render_generation_message(self):
        if self._generation_message is None:
            self.generation_status_label.clear()
            self.generation_status_label.setVisible(False)
            return
        key, values = self._generation_message
        message = self.t(key, **values)
        if key == "generation_failed":
            message += "\n" + self.t("model_failure_help")
        role = {
            "generation_failed": "error",
            "generation_requirements": "warning",
            "generation_success": "success",
        }.get(key, "status")
        self._set_status_role(self.generation_status_label, role)
        self.generation_status_label.setText(message)
        self.generation_status_label.setVisible(True)

    def _set_target_message(self, key=None, **values):
        self._target_message = (key, values) if key else None
        if self._target_message is None:
            self.target_status_label.clear()
            self.target_status_label.setVisible(False)
            return
        key, values = self._target_message
        role = "error" if key.endswith("_failed") else "status"
        self._set_status_role(self.target_status_label, role)
        self.target_status_label.setText(self.t(key, **values))
        self.target_status_label.setVisible(True)

    def _set_write_message(self, key=None, **values):
        self._write_message = (key, values) if key else None
        if self._write_message is None:
            self.write_status_label.clear()
            self.write_status_label.setVisible(False)
            return
        key, values = self._write_message
        role = {
            "write_failed": "error",
            "write_partial": "warning",
            "write_success": "success",
        }.get(key, "status")
        self._set_status_role(self.write_status_label, role)
        self.write_status_label.setText(self.t(key, **values))
        self.write_status_label.setVisible(True)

    def _render_status_messages(self):
        self._render_generation_message()
        if self._target_message is None:
            self.target_status_label.clear()
            self.target_status_label.setVisible(False)
        else:
            key, values = self._target_message
            role = "error" if key.endswith("_failed") else "status"
            self._set_status_role(self.target_status_label, role)
            self.target_status_label.setText(self.t(key, **values))
            self.target_status_label.setVisible(True)
        if self._write_message is None:
            self.write_status_label.clear()
            self.write_status_label.setVisible(False)
        else:
            key, values = self._write_message
            role = {
                "write_failed": "error",
                "write_partial": "warning",
                "write_success": "success",
            }.get(key, "status")
            self._set_status_role(self.write_status_label, role)
            self.write_status_label.setText(self.t(key, **values))
            self.write_status_label.setVisible(True)
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
        role = {
            "duplicates_clear": "success",
            "duplicates_skipped": "warning",
        }.get(key, "muted")
        self._set_status_role(self.duplicate_status_label, role)
        self.duplicate_status_label.setText(self.t(key))

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        columns = QHBoxLayout()
        columns.setSpacing(COLUMN_GAP)
        left = QWidget()
        left.setMinimumWidth(440)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self._build_create_panel(), 1)

        right = QWidget()
        right.setMinimumWidth(460)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self._build_review_panel(), 1)

        columns.addWidget(left, 45)
        columns.addWidget(right, 55)
        root.addLayout(columns)

    def _make_panel(self, title_key, object_name):
        panel = QFrame()
        panel.setObjectName(object_name)
        panel.setProperty("workflowPanel", True)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(
            SECTION_PADDING,
            SECTION_PADDING,
            SECTION_PADDING,
            SECTION_PADDING,
        )
        layout.setSpacing(SPACING_LG)
        title = QLabel(self.t(title_key))
        title.setProperty("role", "panelTitle")
        layout.addWidget(title)
        return panel, title, layout

    def _build_create_panel(self):
        panel, self.create_panel_title, layout = self._make_panel(
            "create_cards_section",
            "CreatePanel",
        )
        layout.addWidget(self._build_material_section(), 1)
        layout.addWidget(self._build_generation_section())

        self.generate_btn = QPushButton(self.t("generate_cards"))
        self._configure_primary_button(self.generate_btn)
        self.generate_btn.setDefault(True)
        self.generate_btn.clicked.connect(self._generate_cards)
        layout.addWidget(self.generate_btn)
        self.generation_status_label = QLabel()
        self.generation_status_label.setProperty("role", "status")
        self.generation_status_label.setWordWrap(True)
        self.generation_status_label.setVisible(False)
        layout.addWidget(self.generation_status_label)
        return panel

    def _build_review_panel(self):
        panel, self.review_panel_title, layout = self._make_panel(
            "cards_section",
            "ReviewPanel",
        )
        layout.addWidget(self._build_cards_section(show_title=False), 1)
        layout.addWidget(self._build_write_section())
        return panel

    def _make_section(self, title_key, *, elevated=False):
        section = QWidget()
        section.setProperty("productSection", True)
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(SPACING_SM)

        title = QLabel(self.t(title_key))
        title.setProperty("role", "sectionTitle")
        section_layout.addWidget(title)

        card = QFrame()
        card.setProperty("sectionCard", elevated)
        card.setProperty("sectionBody", not elevated)
        card_layout = QVBoxLayout(card)
        body_padding = SECTION_PADDING if elevated else 0
        card_layout.setContentsMargins(
            body_padding,
            body_padding,
            body_padding,
            body_padding,
        )
        card_layout.setSpacing(SPACING_MD)
        section_layout.addWidget(card, 1)
        return section, title, card, card_layout

    @staticmethod
    def _configure_form_layout(form):
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(SPACING_MD)
        form.setVerticalSpacing(SPACING_MD)
        row_policy = getattr(QFormLayout, "RowWrapPolicy", QFormLayout)
        growth_policy = getattr(
            QFormLayout,
            "FieldGrowthPolicy",
            QFormLayout,
        )
        form.setRowWrapPolicy(row_policy.DontWrapRows)
        form.setFieldGrowthPolicy(growth_policy.AllNonFixedFieldsGrow)

    @staticmethod
    def _make_form_label(text):
        label = QLabel(text)
        label.setProperty("role", "fieldLabel")
        label.setFixedWidth(FORM_LABEL_WIDTH)
        label.setWordWrap(False)
        label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        return label

    @staticmethod
    def _configure_form_control(widget):
        widget.setMinimumHeight(CONTROL_HEIGHT)
        return widget

    def _add_form_row(self, form, label, control):
        self._configure_form_control(control)
        form.addRow(label, control)

    @staticmethod
    def _configure_secondary_button(button):
        button.setProperty("role", "secondary")
        button.setMinimumHeight(BUTTON_HEIGHT)

    @staticmethod
    def _configure_primary_button(button):
        button.setProperty("role", "primary")
        button.setMinimumHeight(PRIMARY_BUTTON_HEIGHT)

    def _build_material_section(self):
        (
            self.material_group,
            self.material_title_label,
            self.material_card,
            layout,
        ) = self._make_section("material_section")
        self.material_help_label = QLabel(self.t("material_help"))
        self.material_help_label.setProperty("role", "secondary")
        self.material_help_label.setWordWrap(True)
        layout.addWidget(self.material_help_label)

        self.material_input = FileDropTextEdit(
            files_dropped=self._handle_dropped_files,
        )
        self.material_input.setObjectName("MaterialDropArea")
        self.material_input.setPlaceholderText(self.t("material_placeholder"))
        self.material_input.setMinimumHeight(220)
        self.material_input.textChanged.connect(self._on_material_changed)
        layout.addWidget(self.material_input, 1)

        self.material_import_status_label = QLabel()
        self.material_import_status_label.setProperty("role", "status")
        self.material_import_status_label.setWordWrap(True)
        self.material_import_status_label.setVisible(False)
        layout.addWidget(self.material_import_status_label)
        self.material_import_warning_label = QLabel()
        self.material_import_warning_label.setProperty("role", "warning")
        self.material_import_warning_label.setWordWrap(True)
        self.material_import_warning_label.setVisible(False)
        layout.addWidget(self.material_import_warning_label)

        actions = QHBoxLayout()
        self.choose_file_btn = QPushButton(self.t("choose_file"))
        self._configure_secondary_button(self.choose_file_btn)
        self.choose_file_btn.clicked.connect(self._choose_source_file)
        self.example_btn = QPushButton(self.t("use_example"))
        self._configure_secondary_button(self.example_btn)
        self.example_btn.clicked.connect(self._use_example_material)
        self.material_count_label = QLabel(self.t("character_count", count=0))
        self.material_count_label.setProperty("role", "muted")
        actions.addWidget(self.choose_file_btn)
        actions.addWidget(self.example_btn)
        actions.addStretch()
        actions.addWidget(self.material_count_label)
        layout.addLayout(actions)
        return self.material_group

    def _build_generation_section(self):
        (
            self.generation_group,
            self.generation_title_label,
            self.generation_card,
            layout,
        ) = self._make_section("generation_settings")

        mode_form = QFormLayout()
        self._configure_form_layout(mode_form)
        self.card_mode_label = self._make_form_label(self.t("card_mode"))
        self.card_mode_combo = QComboBox()
        for mode_id, key in (
            ("concept", "mode_concept"),
            ("definition", "mode_definition"),
            ("exam", "mode_exam"),
            ("quick_review", "mode_quick_review"),
        ):
            self.card_mode_combo.addItem(self.t(key), mode_id)
        self._add_form_row(
            mode_form,
            self.card_mode_label,
            self.card_mode_combo,
        )
        layout.addLayout(mode_form)

        self.card_mode_description_label = QLabel()
        self.card_mode_description_label.setProperty("role", "secondary")
        self.card_mode_description_label.setWordWrap(False)
        self.card_mode_description_label.setContentsMargins(
            FORM_LABEL_WIDTH + SPACING_MD,
            0,
            0,
            0,
        )
        layout.addWidget(self.card_mode_description_label)

        self.generation_settings_btn = QPushButton(
            self.t("more_options")
        )
        self.generation_settings_btn.setProperty("role", "subtle")
        self.generation_settings_btn.setCheckable(True)
        self.generation_settings_btn.setFlat(True)
        self.generation_settings_btn.toggled.connect(
            self._toggle_generation_settings
        )
        layout.addWidget(self.generation_settings_btn)

        self.generation_settings_container = QWidget()
        generation_form = QFormLayout(self.generation_settings_container)
        self._configure_form_layout(generation_form)
        self.card_count_combo = QComboBox()
        for value, key in (
            ("auto", "card_count_auto"),
            ("fewer", "card_count_fewer"),
            ("balanced", "card_count_balanced"),
            ("more", "card_count_more"),
        ):
            self.card_count_combo.addItem(self.t(key), value)
        self.card_count_combo.setCurrentIndex(2)
        self.card_count_label = self._make_form_label(self.t("card_count"))
        self._add_form_row(
            generation_form,
            self.card_count_label,
            self.card_count_combo,
        )
        self.answer_length_combo = QComboBox()
        self.answer_length_combo.addItem(self.t("answer_length_short"), "short")
        self.answer_length_combo.addItem(self.t("answer_length_medium"), "medium")
        self.answer_length_label = self._make_form_label(
            self.t("answer_length")
        )
        self._add_form_row(
            generation_form,
            self.answer_length_label,
            self.answer_length_combo,
        )
        self.output_language_combo = QComboBox()
        self.output_language_combo.addItem(self.t("output_language_auto"), "auto")
        self.output_language_combo.addItem(self.t("output_language_zh"), "zh")
        self.output_language_combo.addItem(self.t("output_language_en"), "en")
        self.output_language_label = self._make_form_label(
            self.t("output_language")
        )
        self._add_form_row(
            generation_form,
            self.output_language_label,
            self.output_language_combo,
        )
        self.generation_settings_container.setVisible(False)
        layout.addWidget(self.generation_settings_container)
        self.card_mode_combo.currentIndexChanged.connect(
            self._on_generation_settings_changed
        )
        self.card_count_combo.currentIndexChanged.connect(
            self._on_generation_settings_changed
        )
        self.answer_length_combo.currentIndexChanged.connect(
            self._on_generation_settings_changed
        )
        self.output_language_combo.currentIndexChanged.connect(
            self._on_generation_settings_changed
        )
        self._update_card_mode_description()
        return self.generation_group

    def _build_cards_section(self, show_title=True):
        (
            self.cards_group,
            self.cards_title_label,
            self.cards_card,
            layout,
        ) = self._make_section("cards_section")
        self.cards_title_label.setVisible(show_title)
        self.review_required_label = QLabel(self.t("review_required"))
        self.review_required_label.setProperty("role", "secondary")
        self.review_required_label.setWordWrap(True)
        self.review_required_label.setVisible(False)
        layout.addWidget(self.review_required_label)
        quality_row = QHBoxLayout()
        self.quality_summary_label = QLabel()
        self.quality_summary_label.setProperty("role", "status")
        self.quality_summary_label.setWordWrap(True)
        self.quality_summary_label.setVisible(False)
        self.discard_blocking_btn = QPushButton(self.t("discard_blocking"))
        self.discard_blocking_btn.setProperty("role", "secondary")
        self.discard_blocking_btn.setVisible(False)
        self.discard_blocking_btn.clicked.connect(
            self._discard_blocking_cards
        )
        quality_row.addWidget(self.quality_summary_label, 1)
        quality_row.addWidget(self.discard_blocking_btn)
        layout.addLayout(quality_row)
        self.cards_empty_widget = QWidget()
        self.cards_empty_widget.setObjectName("CardsEmptyState")
        empty_layout = QVBoxLayout(self.cards_empty_widget)
        empty_layout.setContentsMargins(12, 16, 12, 16)
        self.empty_cards_glyph = QLabel("◇")
        self.empty_cards_glyph.setObjectName("EmptyStateGlyph")
        self.empty_cards_glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_cards_title = QLabel(self.t("no_cards"))
        self.empty_cards_title.setObjectName("EmptyStateTitle")
        self.empty_cards_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_cards_help = QLabel(self.t("no_cards_help"))
        self.empty_cards_help.setObjectName("EmptyStateHelp")
        self.empty_cards_help.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addStretch()
        empty_layout.addWidget(self.empty_cards_glyph)
        empty_layout.addWidget(self.empty_cards_title)
        empty_layout.addWidget(self.empty_cards_help)
        empty_layout.addStretch()
        layout.addWidget(self.cards_empty_widget)

        self.cards_scroll = QScrollArea()
        self.cards_scroll.setWidgetResizable(True)
        self.cards_scroll.setMinimumHeight(190)
        self.cards_container = QWidget()
        self.cards_container.setObjectName("CardsList")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_scroll.setWidget(self.cards_container)
        self.cards_scroll.setVisible(False)
        layout.addWidget(self.cards_scroll)
        return self.cards_group

    def _build_write_section(self):
        (
            self.write_group,
            self.write_title_label,
            self.write_card,
            layout,
        ) = self._make_section("write_section", elevated=True)
        self.write_card.setObjectName("WriteFooter")
        form = QFormLayout()
        self._configure_form_layout(form)

        self.deck_combo = QComboBox()
        self.deck_combo.currentIndexChanged.connect(self._on_deck_changed)
        self.deck_label = self._make_form_label(self.t("deck"))
        self._add_form_row(form, self.deck_label, self.deck_combo)

        self.note_type_combo = QComboBox()
        self.note_type_combo.currentIndexChanged.connect(
            self._on_note_type_changed
        )
        self.note_type_label = self._make_form_label(self.t("note_type"))
        self._add_form_row(
            form,
            self.note_type_label,
            self.note_type_combo,
        )

        self.front_field_combo = QComboBox()
        self.back_field_combo = QComboBox()
        self.source_field_combo = QComboBox()
        for combo in (
            self.front_field_combo,
            self.back_field_combo,
            self.source_field_combo,
        ):
            combo.currentIndexChanged.connect(self._on_mapping_changed)
        self.front_mapping_label = self._make_form_label(
            self.t("front_mapping")
        )
        self.back_mapping_label = self._make_form_label(
            self.t("back_mapping")
        )
        self.source_mapping_label = self._make_form_label(
            self.t("source_mapping")
        )
        for label, combo in (
            (self.front_mapping_label, self.front_field_combo),
            (self.back_mapping_label, self.back_field_combo),
            (self.source_mapping_label, self.source_field_combo),
        ):
            self._add_form_row(form, label, combo)
        layout.addLayout(form)

        self.target_status_label = QLabel()
        self.target_status_label.setWordWrap(True)
        self.target_status_label.setProperty("role", "status")
        self.target_status_label.setVisible(False)
        layout.addWidget(self.target_status_label)

        duplicate_row = QHBoxLayout()
        self.duplicate_btn = QPushButton(self.t("check_duplicates"))
        self._configure_secondary_button(self.duplicate_btn)
        self.duplicate_btn.clicked.connect(self._check_duplicates)
        self.duplicate_status_label = QLabel(self.t("duplicates_unchecked"))
        self.duplicate_status_label.setProperty("role", "muted")
        duplicate_row.addWidget(self.duplicate_btn)
        duplicate_row.addWidget(self.duplicate_status_label)
        duplicate_row.addStretch()
        layout.addLayout(duplicate_row)

        self.write_summary_label = QLabel(self.t("write_summary_empty"))
        self.write_summary_label.setProperty("role", "status")
        self.write_summary_label.setWordWrap(True)
        layout.addWidget(self.write_summary_label)

        self.write_btn = QPushButton(self.t("write_to_anki"))
        self._configure_primary_button(self.write_btn)
        self.write_btn.clicked.connect(self._confirm_and_write)
        layout.addWidget(self.write_btn)
        self.write_status_label = QLabel()
        self.write_status_label.setProperty("role", "status")
        self.write_status_label.setWordWrap(True)
        self.write_status_label.setVisible(False)
        layout.addWidget(self.write_status_label)
        return self.write_group

    def _choose_source_file(self):
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            self.t("choose_file"),
            "",
            self.t("source_file_filter"),
        )
        if not path:
            return
        self._import_source_path(Path(path))

    def _handle_dropped_files(self, paths):
        if not paths:
            return
        extra_warnings = ("source_import_first_only",) if len(paths) > 1 else ()
        self._import_source_path(Path(paths[0]), extra_warnings=extra_warnings)

    def _import_source_path(self, path, *, extra_warnings=()):
        try:
            imported = import_source_file(Path(path))
        except SourceImportError as error:
            self._set_source_import_error(
                error.code,
                warning_keys=extra_warnings,
            )
            return
        self._apply_imported_source(imported, extra_warnings=extra_warnings)

    def _apply_imported_source(self, imported: ImportedSource, *, extra_warnings=()):
        existing_text = self.material_input.toPlainText()
        warnings = list(imported.warnings) + list(extra_warnings)
        combined_text, appended = merge_imported_source_text(
            existing_text,
            imported,
        )
        if appended:
            warnings.append("source_import_appended")

        imported_source_type = source_type_from_path(imported.filename)
        self.session.set_source_type(
            SourceType.UNKNOWN if appended and existing_text.strip() else imported_source_type
        )

        self._applying_source_import = True
        try:
            self.material_input.setPlainText(combined_text)
        finally:
            self._applying_source_import = False
        self._source_import_message = (
            "source_imported",
            {
                "filename": imported.filename,
                "kind": imported.suffix.lstrip(".").upper(),
                "count": imported.char_count,
            },
        )
        self._source_import_warning_keys = tuple(dict.fromkeys(warnings))
        self._render_source_import_feedback()

    def _set_source_import_error(self, error_code, *, warning_keys=()):
        key = f"source_import_error_{error_code}"
        try:
            self.t(key)
        except KeyError:
            key = "source_import_error_generic"
        self._source_import_message = (key, {})
        self._source_import_warning_keys = tuple(warning_keys)
        self._render_source_import_feedback()

    def _clear_source_import_feedback(self):
        self._source_import_message = None
        self._source_import_warning_keys = ()
        self._render_source_import_feedback()

    def _render_source_import_feedback(self):
        if self._source_import_message is None:
            self._set_status_role(self.material_import_status_label, "status")
            self.material_import_status_label.clear()
            self.material_import_status_label.setVisible(False)
        else:
            key, values = self._source_import_message
            role = "error" if "source_import_error_" in key else "success"
            self._set_status_role(self.material_import_status_label, role)
            self.material_import_status_label.setText(self.t(key, **values))
            self.material_import_status_label.setVisible(True)
        warnings = [self.t(key) for key in self._source_import_warning_keys]
        self._set_status_role(self.material_import_warning_label, "warning")
        self.material_import_warning_label.setText("\n".join(warnings))
        self.material_import_warning_label.setVisible(bool(warnings))

    def _use_example_material(self):
        self.session.set_source_type(SourceType.PASTE)
        self.session.load_example_material()
        self.material_input.blockSignals(True)
        self.material_input.setPlainText(self.session.material_text)
        self.material_input.blockSignals(False)
        self._clear_source_import_feedback()
        self._set_generation_message()
        self._after_upstream_change()

    def _on_material_changed(self):
        material_text = self.material_input.toPlainText()
        if not self._applying_source_import:
            if not self.session.material_text.strip() or not material_text.strip():
                self.session.set_source_type(SourceType.PASTE)
        self.session.update_material(material_text)
        if not self._applying_source_import:
            self._clear_source_import_feedback()
        self._set_generation_message()
        self._after_upstream_change()

    def _toggle_generation_settings(self, expanded):
        self.generation_settings_container.setVisible(expanded)
        self.generation_settings_btn.setText(
            self.t("more_options_collapse")
            if expanded
            else self.t("more_options")
        )

    def _current_generation_settings(self):
        return GenerationSettings(
            card_mode=self.card_mode_combo.currentData(),
            card_count=self.card_count_combo.currentData(),
            answer_length=self.answer_length_combo.currentData(),
            language=self.output_language_combo.currentData(),
        )

    def _update_card_mode_description(self):
        mode_id = self.card_mode_combo.currentData() or "concept"
        self.card_mode_description_label.setText(
            self.t(f"mode_{mode_id}_description")
        )

    def _on_generation_settings_changed(self, *unused):
        self._update_card_mode_description()
        self.session.set_generation_settings(
            self._current_generation_settings()
        )
        self._set_generation_message()
        self._after_upstream_change(render_material_count=False)

    def _ai_settings_are_ready(self):
        return bool(
            self.session.material_text.strip()
            and self._ai_runtime_settings is not None
        )

    def _generate_cards(self):
        if not self._ai_settings_are_ready():
            self._set_generation_message("generation_requirements")
            return
        settings = self._ai_runtime_settings

        generation_settings = self._current_generation_settings()
        self.session.set_generation_settings(generation_settings)
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
            generation_settings=generation_settings,
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
            self.review_required_label.setVisible(False)
            self.quality_summary_label.setVisible(False)
            self.discard_blocking_btn.setVisible(False)
            self.cards_empty_widget.setVisible(True)
            self.cards_scroll.setVisible(False)
            return
        self.cards_empty_widget.setVisible(False)
        self.cards_scroll.setVisible(True)
        self.review_required_label.setVisible(True)
        qualities = tuple(
            self.session.quality_for_candidate(card.id) for card in cards
        )
        blocking = sum(item.is_blocking for item in qualities)
        warnings = sum(item.severity == "warning" for item in qualities)
        good = len(qualities) - blocking - warnings
        self._set_status_role(
            self.quality_summary_label,
            "error" if blocking else "warning" if warnings else "success",
        )
        self.quality_summary_label.setText(
            self.t(
                "quality_summary",
                good=good,
                warnings=warnings,
                blocking=blocking,
            )
        )
        self.quality_summary_label.setVisible(True)
        self.discard_blocking_btn.setVisible(bool(blocking))

        for index, card in enumerate(cards, start=1):
            quality = self.session.quality_for_candidate(card.id)
            card_group = QGroupBox(self.t("card_number", number=index))
            card_group.setProperty("cardItem", True)
            card_layout = QVBoxLayout(card_group)
            front = QLabel(f"{self.t('front')}:\n{card.front_preview}")
            back = QLabel(f"{self.t('back')}:\n{card.back_preview}")
            front.setWordWrap(True)
            back.setWordWrap(True)
            card_layout.addWidget(front)
            card_layout.addWidget(back)

            quality_label = QLabel(
                self.t(f"quality_status_{quality.severity}")
            )
            self._set_status_role(
                quality_label,
                {
                    "info": "success",
                    "warning": "warning",
                    "blocking": "error",
                }[quality.severity],
            )
            quality_label.setWordWrap(True)
            card_layout.addWidget(quality_label)
            if quality.issues:
                warning_lines = []
                for issue in quality.issues[:3]:
                    warning_id = issue.warning_id
                    warning_lines.append(
                        f"• {self.t(f'quality_{warning_id}')} — "
                        f"{self.t(f'quality_{issue.suggestion_id}')}"
                    )
                quality_detail = QLabel("\n".join(warning_lines))
                quality_detail.setProperty("role", "secondary")
                quality_detail.setWordWrap(True)
                card_layout.addWidget(quality_detail)

            source_btn = QPushButton(self.t("source"))
            source_btn.setProperty("role", "subtle")
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
            edit_btn.setProperty("role", "secondary")
            current = self.session.candidate_review_decisions.get(card.id)
            keep_btn.setChecked(current is BeginnerReviewDecision.LOOKS_GOOD)
            keep_btn.setEnabled(not quality.is_blocking)
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

    def _discard_blocking_cards(self):
        discarded = self.session.discard_blocking_candidates()
        if discarded:
            self._clear_duplicate_state()
            self._render_cards()
            self._refresh_product_state()

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
        self.session.replace_candidate_content(card_id, front, back)
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
        final_preview = build_beginner_final_confirmation_preview(
            self.session,
            self.anki_mapping,
            self.duplicate_results,
        )
        self.final_confirmation_preview = final_preview
        self.session.apply_final_confirmation_preview(
            final_preview.candidate_count,
            len(final_preview.missing_conditions),
        )
        preparation = prepare_beginner_write(
            self.session,
            final_preview,
            self.anki_mapping,
            self.duplicate_results,
        )
        self.write_preparation = preparation
        self.write_command = preparation.command
        command = preparation.command
        if command is None:
            self.write_summary = None
        else:
            written_ids = {item.candidate_id for item in command.cards}
            qualities = tuple(
                self.session.quality_for_candidate(candidate_id)
                for candidate_id in written_ids
            )
            field_mapping = (
                f"Front → {command.front_field}",
                f"Back → {command.back_field}",
                *(
                    (f"Source → {command.source_field}",)
                    if command.source_field
                    else ()
                ),
            )
            self.write_summary = build_write_summary(
                target_deck=command.deck_name,
                note_type=command.note_type_name,
                field_mapping=field_mapping,
                source_label=command.cards[0].source,
                cards_to_write=command.requested_count,
                warning_count=sum(item.warning_count for item in qualities),
                blocking_count=sum(item.blocking_count for item in qualities),
                duplicate_behavior="skip_possible_duplicates",
                tags=command.tags,
            )
        self._render_write_summary()
        return preparation

    def _render_write_summary(self):
        if self.write_result_summary is not None:
            result = self.write_result_summary
            self._set_status_role(
                self.write_summary_label,
                "success" if result.written_count and not result.failed_count else "warning",
            )
            self.write_summary_label.setText(
                self.t(
                    "write_result_summary",
                    written=result.written_count,
                    skipped=result.skipped_duplicate_count,
                    failed=result.failed_count,
                    deck=result.target_deck,
                    tags=", ".join(result.tags),
                )
            )
            return
        if self.write_summary is None:
            self._set_status_role(self.write_summary_label, "status")
            self.write_summary_label.setText(self.t("write_summary_empty"))
            return
        summary = self.write_summary
        self._set_status_role(
            self.write_summary_label,
            "error" if summary.blocking_count else "warning"
            if summary.warning_count
            else "success",
        )
        self.write_summary_label.setText(
            self.t(
                "write_summary",
                deck=summary.target_deck,
                note_type=summary.note_type,
                cards=summary.cards_to_write,
                skipped=(
                    self.write_command.skipped_count
                    if self.write_command is not None
                    else 0
                ),
                warnings=summary.warning_count,
                blocking=summary.blocking_count,
                source=summary.source_label,
                tags=", ".join(summary.tags),
            )
        )

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
                "confirm_write_body_v1",
                count=command.requested_count,
                deck=command.deck_name,
                warnings=(
                    self.write_summary.warning_count
                    if self.write_summary is not None
                    else 0
                ),
                tags=", ".join(command.tags),
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
        self.write_result_summary = build_write_result_summary(
            written_count=result.success_count,
            skipped_duplicate_count=result.skipped_count,
            failed_count=result.failed_count,
            target_deck=command.deck_name,
            tags=command.tags,
        )
        if result.created_note_ids:
            self.session.record_last_write_batch(
                LastWriteBatchRecord(
                    snapshot_id=result.snapshot_id,
                    created_note_ids=result.created_note_ids,
                    requested_count=command.requested_count,
                    skipped_count=result.skipped_count,
                    failed_count=result.failed_count,
                    target_deck=command.deck_name,
                    tags=command.tags,
                    source_type=self.session.source_type,
                )
            )
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
        self._render_write_summary()
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
        self.final_confirmation_preview = None
        self.write_result_summary = None
        self.write_preparation = None
        self.write_command = None
        self.write_result = None
        self._refresh_duplicate_copy()
        if hasattr(self, "write_summary_label"):
            self._render_write_summary()

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
        generation_ready = self._ai_settings_are_ready()
        self.generate_btn.setEnabled(generation_ready)
        self.generate_btn.setToolTip(
            "" if generation_ready else self.t("generation_requirements")
        )
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
        self._clear_source_import_feedback()
        self._ai_runtime_settings = None
        if not self.session.closed:
            self.session.close()
        self.anki_target_snapshot = None
        self.anki_field_snapshot = None
        self.anki_mapping = None
        self.duplicate_results = None
        self.write_summary = None
        self.final_confirmation_preview = None
        self.write_result_summary = None
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
