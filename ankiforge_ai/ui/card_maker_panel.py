"""Single-screen product panel for turning study material into Anki cards."""

from pathlib import Path
import weakref

from aqt import mw
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
    QMenu,
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
from ..intelligence import GenerationStage, IntelligenceLevel
from ..pipeline.ai_generation_limits import MAX_AI_MATERIAL_CHARS
from ..pipeline.generation_settings import (
    GenerationSettings,
    card_limit_for_settings,
    get_card_mode_profile,
    selectable_card_mode_profiles,
)
from ..pipeline.example_materials import (
    all_example_materials,
    get_example_material,
)
from ..pipeline.provider_endpoint_safety import (
    DEFAULT_OFFICIAL_PROVIDER_HOSTS,
    EndpointConfirmationSession,
    assess_provider_endpoint,
    endpoint_confirmation_key,
)
from ..pipeline.write_traceability import (
    SourceType,
    build_write_result_summary,
    build_write_summary,
    create_last_write_batch_record,
    safe_source_label,
)
from .beginner_ai_card_drafts import (
    BeginnerAIProviderRuntimeSettings,
    generation_error_message_key,
)
from .beginner_final_confirmation import (
    build_beginner_final_confirmation_preview,
)
from .beginner_flow_models import (
    BeginnerAICardDraft,
    BeginnerAIGenerationState,
    BeginnerFlowSession,
    BeginnerReviewDecision,
    BeginnerWriteState,
)
from .beginner_real_write import (
    execute_beginner_write_if_confirmed,
    prepare_beginner_write,
)
from .file_drop_text_edit import FileDropTextEdit
from .document_capabilities_dialog import (
    DocumentCapabilitiesDialog,
    default_document_capabilities,
)
from .document_import_queue import (
    DocumentImportStatus,
    PrivatePathToken,
    add_import_paths,
    apply_import_completion,
    begin_import,
    create_import_queue,
    move_import_item,
    remove_import_item,
    retry_failed_imports,
)
from .document_import_task_controller import (
    DocumentImportTaskController,
    build_bounded_import_material,
    import_document_path_token,
)
from .document_intelligence_presenter import (
    present_batch_intelligence_estimate,
    stage_label,
)
from .generation_task_controller import GenerationTaskController
from .intelligent_generation_task_controller import (
    IntelligentGenerationTaskController,
)
from ..intelligence.recovery import failed_chunk_retry_is_available
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
from .source_location_presenter import present_source_location
from .universal_document_generation_adapter import (
    BoundedProviderGenerationAdapter,
    build_imported_generation_run,
    drafts_from_generation_run,
)
from .style_tokens import (
    BUTTON_HEIGHT,
    FORM_LABEL_WIDTH,
    INPUT_HEIGHT as CONTROL_HEIGHT,
    PRIMARY_BUTTON_HEIGHT,
    SECTION_PADDING,
    SPACING_LG,
    SPACING_MD,
    SPACING_SM,
    SPACING_XL as COLUMN_GAP,
    SPACING_XS,
)


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
        self._document_queue_owns_material = False
        self._document_import_queue = create_import_queue()
        self._pending_document_import_requests = []
        self._current_intelligence_estimate_view = None
        self._next_intelligence_request_id = 0
        self._active_provider_generation_adapter = None
        self._last_intelligence_run = None
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
        self._endpoint_confirmations = EndpointConfirmationSession()
        self._generation_controller = GenerationTaskController(mw.taskman)
        self._intelligent_generation_controller = (
            IntelligentGenerationTaskController(mw.taskman)
        )
        self._document_import_controller = DocumentImportTaskController(mw.taskman)
        self._disposed = False

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

    def confirmed_endpoint_keys(self):
        return self._endpoint_confirmations.keys

    def set_ai_runtime_settings(self, settings, confirmed_endpoint_key=None):
        if not isinstance(settings, BeginnerAIProviderRuntimeSettings):
            raise TypeError(
                "settings must be BeginnerAIProviderRuntimeSettings"
            )
        decision = assess_provider_endpoint(
            settings.base_url,
            official_hosts=DEFAULT_OFFICIAL_PROVIDER_HOSTS,
        )
        if decision.kind == "deny":
            raise ValueError("provider endpoint is denied")
        if decision.kind == "confirm":
            required_key = endpoint_confirmation_key(settings.base_url)
            if confirmed_endpoint_key is not None:
                if confirmed_endpoint_key != required_key:
                    raise ValueError("provider endpoint confirmation does not match")
                self._endpoint_confirmations.add_key(confirmed_endpoint_key)
            if not self._endpoint_confirmations.is_confirmed(settings.base_url):
                raise ValueError("provider endpoint requires confirmation")
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
        self.document_capabilities_btn.setText(
            self.t("document_capabilities")
        )
        self.retry_failed_imports_btn.setText(
            self.t("retry_failed_imports")
        )
        self.retry_failed_generation_btn.setText(
            self.t("retry_failed_generation")
        )
        self._render_document_queue()
        self._render_source_import_feedback()

        self.generation_title_label.setText(self.t("generation_settings"))
        self.create_panel_title.setText(self.t("create_cards_section"))
        self.card_mode_label.setText(self.t("card_mode"))
        self.intelligence_level_label.setText(self.t("intelligence_level"))
        self._retranslate_generation_settings()
        self._update_intelligence_estimate()

        self.cards_title_label.setText(self.t("cards_section"))
        self.review_panel_title.setText(self.t("cards_section"))
        self.empty_cards_title.setText(self.t("no_cards"))
        self.empty_cards_help.setText(self.t("no_cards_help"))
        self.review_required_label.setText(self.t("review_required"))
        self.discard_blocking_btn.setText(self.t("discard_blocking"))
        self.keep_clean_btn.setText(self.t("keep_clean"))

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
        for index in range(self.card_mode_combo.count()):
            profile = get_card_mode_profile(self.card_mode_combo.itemData(index))
            self.card_mode_combo.setItemText(
                index,
                profile.display_name_zh
                if self.language == "zh"
                else profile.display_name_en,
            )
        for index, key in enumerate(
            (
                "intelligence_fast",
                "intelligence_standard",
                "intelligence_deep",
            )
        ):
            self.intelligence_level_combo.setItemText(index, self.t(key))
        for combo, keys in (
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
        self._toggle_plan_details(self.plan_detail_btn.isChecked())
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
        error_keys = {
            "generation_failed",
            "generation_endpoint_not_authorized",
            "generation_http_auth",
            "generation_http_not_found",
            "generation_http_timeout",
            "generation_http_rate_limit",
            "generation_http_unavailable",
            "material_too_long",
        }
        role = {
            "generation_requirements": "warning",
            "generation_success": "success",
        }.get(key, "error" if key in error_keys else "status")
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
            "duplicate_state_changed": "warning",
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
                "duplicate_state_changed": "warning",
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
        self.generation_progress_label = QLabel()
        self.generation_progress_label.setObjectName("StageProgress")
        self.generation_progress_label.setProperty("role", "muted")
        self.generation_progress_label.setWordWrap(True)
        self.generation_progress_label.setVisible(False)
        layout.addWidget(self.generation_progress_label)
        self.retry_failed_generation_btn = QPushButton(
            self.t("retry_failed_generation")
        )
        self._configure_secondary_button(self.retry_failed_generation_btn)
        self.retry_failed_generation_btn.clicked.connect(
            self._retry_failed_generation_chunks
        )
        self.retry_failed_generation_btn.setVisible(False)
        layout.addWidget(self.retry_failed_generation_btn)
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

        self.document_queue_container = QWidget()
        self.document_queue_layout = QVBoxLayout(self.document_queue_container)
        self.document_queue_layout.setContentsMargins(0, 0, 0, 0)
        self.document_queue_layout.setSpacing(SPACING_XS)
        layout.addWidget(self.document_queue_container)

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
        self.example_btn.clicked.connect(self._show_example_menu)
        self.document_capabilities_btn = QPushButton(
            self.t("document_capabilities")
        )
        self._configure_secondary_button(self.document_capabilities_btn)
        self.document_capabilities_btn.clicked.connect(
            self._show_document_capabilities
        )
        self.material_count_label = QLabel(self.t("character_count", count=0))
        self.material_count_label.setProperty("role", "muted")
        actions.addWidget(self.choose_file_btn)
        actions.addWidget(self.example_btn)
        actions.addWidget(self.document_capabilities_btn)
        actions.addStretch()
        actions.addWidget(self.material_count_label)
        layout.addLayout(actions)
        self.retry_failed_imports_btn = QPushButton(
            self.t("retry_failed_imports")
        )
        self._configure_secondary_button(self.retry_failed_imports_btn)
        self.retry_failed_imports_btn.clicked.connect(
            self._retry_failed_document_imports
        )
        self.retry_failed_imports_btn.setVisible(False)
        layout.addWidget(self.retry_failed_imports_btn)
        self._render_document_queue()
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
        for profile in selectable_card_mode_profiles():
            display_name = (
                profile.display_name_zh
                if self.language == "zh"
                else profile.display_name_en
            )
            self.card_mode_combo.addItem(display_name, profile.mode_id)
        self._add_form_row(
            mode_form,
            self.card_mode_label,
            self.card_mode_combo,
        )
        self.intelligence_level_label = self._make_form_label(
            self.t("intelligence_level")
        )
        self.intelligence_level_combo = QComboBox()
        for level, key in (
            (IntelligenceLevel.FAST, "intelligence_fast"),
            (IntelligenceLevel.STANDARD, "intelligence_standard"),
            (IntelligenceLevel.DEEP, "intelligence_deep"),
        ):
            self.intelligence_level_combo.addItem(self.t(key), level.value)
        self.intelligence_level_combo.setCurrentIndex(1)
        self._add_form_row(
            mode_form,
            self.intelligence_level_label,
            self.intelligence_level_combo,
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

        self.intelligence_estimate_label = QLabel(
            self.t("intelligence_estimate_pending")
        )
        self.intelligence_estimate_label.setProperty("role", "status")
        self.intelligence_estimate_label.setWordWrap(True)
        layout.addWidget(self.intelligence_estimate_label)

        self.plan_detail_btn = QPushButton(self.t("plan_details"))
        self.plan_detail_btn.setProperty("role", "subtle")
        self.plan_detail_btn.setCheckable(True)
        self.plan_detail_btn.setFlat(True)
        self.plan_detail_btn.toggled.connect(self._toggle_plan_details)
        layout.addWidget(self.plan_detail_btn)
        self.plan_detail_container = QWidget()
        plan_detail_layout = QVBoxLayout(self.plan_detail_container)
        plan_detail_layout.setContentsMargins(
            FORM_LABEL_WIDTH + SPACING_MD,
            0,
            0,
            0,
        )
        self.plan_detail_label = QLabel()
        self.plan_detail_label.setProperty("role", "secondary")
        self.plan_detail_label.setWordWrap(True)
        plan_detail_layout.addWidget(self.plan_detail_label)
        self.plan_detail_container.setVisible(False)
        layout.addWidget(self.plan_detail_container)

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
        self.intelligence_level_combo.currentIndexChanged.connect(
            self._on_intelligence_level_changed
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
        self._update_intelligence_estimate()
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
        self.review_stats_label = QLabel()
        self.review_stats_label.setProperty("role", "muted")
        self.review_stats_label.setWordWrap(True)
        self.review_stats_label.setVisible(False)
        layout.addWidget(self.review_stats_label)
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
        self.keep_clean_btn = QPushButton(self.t("keep_clean"))
        self.keep_clean_btn.setProperty("role", "secondary")
        self.keep_clean_btn.setVisible(False)
        self.keep_clean_btn.clicked.connect(self._keep_clean_cards)
        quality_row.addWidget(self.quality_summary_label, 1)
        quality_row.addWidget(self.keep_clean_btn)
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
        self.last_write_label = QLabel()
        self.last_write_label.setProperty("role", "muted")
        self.last_write_label.setWordWrap(True)
        self.last_write_label.setVisible(False)
        layout.addWidget(self.last_write_label)

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
        paths, _selected_filter = QFileDialog.getOpenFileNames(
            self,
            self.t("choose_file"),
            "",
            self.t("source_file_filter"),
        )
        if not paths:
            return
        self._enqueue_document_paths(paths)

    def _handle_dropped_files(self, paths):
        if not paths:
            return
        self._enqueue_document_paths(paths)

    def _enqueue_document_paths(self, paths):
        tokens = []
        for selected in tuple(paths):
            path = Path(selected)
            try:
                byte_size = path.stat().st_size
            except OSError:
                self._set_source_import_error("generic")
                continue
            tokens.append(
                PrivatePathToken.from_path(path, byte_size=byte_size)
            )
        if not tokens:
            return
        try:
            self._document_import_queue = add_import_paths(
                self._document_import_queue,
                tokens,
            )
        except ValueError as exc:
            code = str(exc)
            key = f"document_queue_error_{code}"
            if key not in {"document_queue_error_too_many_files", "document_queue_error_batch_too_large"}:
                key = "document_queue_error_file_unavailable"
            self._source_import_message = (key, {})
            self._render_source_import_feedback()
            return
        self._invalidate_generation_for_document_queue_change()
        self._sync_material_from_document_queue()
        self._begin_queued_document_imports()
        self._render_document_queue()
        self._render_cards()
        self._refresh_product_state()

    def _begin_queued_document_imports(self):
        for index, row in enumerate(self._document_import_queue.safe_rows):
            if row.status is not DocumentImportStatus.QUEUED:
                continue
            self._document_import_queue, request = begin_import(
                self._document_import_queue,
                index,
            )
            self._pending_document_import_requests.append(request)
        self._dispatch_next_document_import()

    def _dispatch_next_document_import(self):
        if (
            self._disposed
            or self._document_import_controller.running
            or not self._pending_document_import_requests
        ):
            return
        request = self._pending_document_import_requests.pop(0)
        panel_reference = weakref.ref(self)

        def handle_completion(completion):
            panel = panel_reference()
            if panel is None or panel._disposed:
                return
            panel._handle_document_import_completion(completion)

        self._document_import_controller.submit(
            request=request,
            importer_callback=import_document_path_token,
            on_complete=handle_completion,
        )

    def _handle_document_import_completion(self, completion):
        if self._disposed or self.session.closed:
            return
        previous_queue = self._document_import_queue
        self._document_import_queue = apply_import_completion(
            previous_queue,
            completion,
        )
        if self._document_import_queue is not previous_queue:
            self._invalidate_generation_for_document_queue_change()
        self._sync_material_from_document_queue()
        self._render_source_import_feedback()
        self._render_document_queue()
        self._update_intelligence_estimate()
        self._refresh_product_state()
        self._dispatch_next_document_import()

    def _sync_material_from_document_queue(self):
        results = self._document_import_queue.successful_results
        if results:
            material = build_bounded_import_material(
                results,
                max_chars=MAX_AI_MATERIAL_CHARS,
            )
            self._applying_source_import = True
            self.material_input.blockSignals(True)
            try:
                self.material_input.setPlainText(material)
            finally:
                self.material_input.blockSignals(False)
                self._applying_source_import = False
            self._document_queue_owns_material = True
            self.session.update_material(material)
            self.session.set_source_type(SourceType.UNKNOWN)
            selected_level = self._current_intelligence_level()
            estimates = tuple(
                next(
                    estimate
                    for estimate in result.estimates
                    if estimate.level is selected_level
                )
                for result in results
                if result.estimates
            )
            self.session.record_document_intelligence_artifacts(
                parsed_documents=tuple(result.document for result in results),
                analyses=tuple(
                    result.analysis
                    for result in results
                    if result.analysis is not None
                ),
                chunks=tuple(
                    chunk
                    for result in results
                    for chunk in result.chunks
                ),
                estimate=(
                    present_batch_intelligence_estimate(
                        estimates,
                        language=self.language,
                        card_limit=card_limit_for_settings(
                            self._current_generation_settings()
                        ),
                    )
                    if estimates
                    else None
                ),
            )
            self._source_import_message = (
                "document_imported_batch",
                {"count": len(results)},
            )
            self._source_import_warning_keys = tuple(
                warning
                for row in self._document_import_queue.safe_rows
                for warning in row.warnings
                if row.status is DocumentImportStatus.WARNING
            )
            return
        if not self._document_queue_owns_material:
            return
        material = ""
        self._applying_source_import = True
        self.material_input.blockSignals(True)
        try:
            self.material_input.setPlainText(material)
        finally:
            self.material_input.blockSignals(False)
            self._applying_source_import = False
        self._document_queue_owns_material = False
        self.session.update_material(material)
        self.session.set_source_type(SourceType.UNKNOWN)
        self._source_import_message = None
        self._source_import_warning_keys = ()

    def _retry_failed_document_imports(self):
        self._document_import_queue, requests = retry_failed_imports(
            self._document_import_queue
        )
        self._pending_document_import_requests.extend(requests)
        self._render_document_queue()
        self._dispatch_next_document_import()

    def _render_document_queue(self):
        self._clear_layout(self.document_queue_layout)
        rows = self._document_import_queue.safe_rows
        if not rows:
            empty = QLabel(self.t("document_queue_empty"))
            empty.setProperty("role", "muted")
            self.document_queue_layout.addWidget(empty)
            self.retry_failed_imports_btn.setVisible(False)
            return
        for index, row in enumerate(rows):
            row_widget = QWidget()
            row_widget.setObjectName("DocumentQueueRow")
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(
                SPACING_SM,
                SPACING_XS,
                SPACING_SM,
                SPACING_XS,
            )
            status = self.t(f"document_queue_status_{row.status.value}")
            label = QLabel(
                self.t(
                    "document_queue_row",
                    filename=row.filename,
                    status=status,
                    type=row.file_type or "—",
                    importer=row.importer or "—",
                    sections=row.section_count,
                    blocks=row.block_count,
                    chars=row.char_count,
                )
            )
            label.setWordWrap(True)
            row_layout.addWidget(label, 1)

            up = QPushButton("↑")
            up.setToolTip(self.t("move_document_up"))
            up.setEnabled(index > 0)
            up.clicked.connect(
                lambda _checked=False, current=index: self._move_document_queue_item(
                    current - 1,
                    current,
                )
            )
            down = QPushButton("↓")
            down.setToolTip(self.t("move_document_down"))
            down.setEnabled(index + 1 < len(rows))
            down.clicked.connect(
                lambda _checked=False, current=index: self._move_document_queue_item(
                    current + 1,
                    current,
                )
            )

            remove = QPushButton(self.t("remove_document"))
            remove.clicked.connect(
                lambda _checked=False, current=index: self._remove_document_queue_item(
                    current
                )
            )
            row_layout.addWidget(up)
            row_layout.addWidget(down)
            row_layout.addWidget(remove)
            self.document_queue_layout.addWidget(row_widget)
        self.retry_failed_imports_btn.setVisible(
            any(row.status is DocumentImportStatus.FAILURE for row in rows)
        )

    def _move_document_queue_item(self, destination, current):
        self._document_import_queue = move_import_item(
            self._document_import_queue,
            current,
            destination,
        )
        self._invalidate_generation_for_document_queue_change()
        self._sync_material_from_document_queue()
        self._render_document_queue()
        self._update_intelligence_estimate()

    def _remove_document_queue_item(self, current):
        self._document_import_queue = remove_import_item(
            self._document_import_queue,
            current,
        )
        self._invalidate_generation_for_document_queue_change()
        self._sync_material_from_document_queue()
        self._render_document_queue()
        self._update_intelligence_estimate()

    def _show_document_capabilities(self):
        dialog = DocumentCapabilitiesDialog(
            default_document_capabilities(),
            language=self.language,
            backend_availability={"pdf_optional": False},
            parent=self,
        )
        dialog.exec()

    def _invalidate_generation_for_document_queue_change(self):
        self.session.mark_document_queue_changed()
        self._intelligent_generation_controller.invalidate()
        self._active_provider_generation_adapter = None
        self._last_intelligence_run = None
        self.retry_failed_generation_btn.setVisible(False)
        self._clear_generated_state()

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

    def _show_example_menu(self):
        menu = QMenu(self)
        for example in all_example_materials():
            title = example.title_zh if self.language == "zh" else example.title_en
            action = menu.addAction(title)
            action.triggered.connect(
                lambda _checked=False, example_id=example.example_id: self._use_example_material(
                    example_id
                )
            )
        menu.exec(self.example_btn.mapToGlobal(self.example_btn.rect().bottomLeft()))

    def _use_example_material(self, example_id="zh_concept"):
        example = get_example_material(example_id)
        self._document_import_controller.invalidate()
        self._pending_document_import_requests.clear()
        self._document_import_queue = create_import_queue()
        self._document_queue_owns_material = False
        self.session.mark_document_queue_changed()
        self._render_document_queue()
        self._update_intelligence_estimate()
        self.session.set_source_type(SourceType.PASTE)
        self.session.update_material(example.material_text)
        self.material_input.blockSignals(True)
        self.material_input.setPlainText(self.session.material_text)
        self.material_input.blockSignals(False)
        mode_index = self.card_mode_combo.findData(example.recommended_mode)
        if mode_index >= 0:
            self.card_mode_combo.setCurrentIndex(mode_index)
        self._clear_source_import_feedback()
        self._set_generation_message()
        self._after_upstream_change()

    def _on_material_changed(self):
        material_text = self.material_input.toPlainText()
        if not self._applying_source_import:
            if self._document_import_queue.safe_rows:
                self._document_import_controller.invalidate()
                self._pending_document_import_requests.clear()
                self._document_import_queue = create_import_queue()
                self._document_queue_owns_material = False
                self.session.mark_document_queue_changed()
                self._render_document_queue()
                self._update_intelligence_estimate()
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

    def _toggle_plan_details(self, expanded):
        self.plan_detail_container.setVisible(expanded)
        self.plan_detail_btn.setText(
            self.t("plan_details_collapse")
            if expanded
            else self.t("plan_details")
        )

    def _current_intelligence_level(self):
        return IntelligenceLevel(
            self.intelligence_level_combo.currentData() or "standard"
        )

    def _on_intelligence_level_changed(self, *unused):
        self.session.set_intelligence_level(
            self._current_intelligence_level()
        )
        self._set_generation_message()
        self._after_upstream_change(render_material_count=False)
        self._update_intelligence_estimate()

    def _update_intelligence_estimate(self):
        level = self._current_intelligence_level()
        has_documents = bool(
            self._document_import_queue.successful_results
        )
        self.intelligence_level_combo.setEnabled(has_documents)
        self.plan_detail_btn.setEnabled(has_documents)
        estimates = tuple(
            next(
                (
                    estimate
                    for estimate in result.estimates
                    if estimate.level is level
                ),
                None,
            )
            for result in self._document_import_queue.successful_results
        )
        estimates = tuple(item for item in estimates if item is not None)
        if not estimates:
            self._current_intelligence_estimate_view = None
            message_key = (
                "paste_generation_behavior"
                if self.session.material_text.strip()
                and not self._document_import_queue.safe_rows
                else "intelligence_estimate_pending"
            )
            self.intelligence_estimate_label.setText(
                self.t(message_key)
            )
            self.plan_detail_label.setText(
                self.t(message_key)
                if message_key == "paste_generation_behavior"
                else ""
            )
            return
        view = present_batch_intelligence_estimate(
            estimates,
            language=self.language,
            card_limit=card_limit_for_settings(
                self._current_generation_settings()
            ),
        )
        self._current_intelligence_estimate_view = view
        self.intelligence_estimate_label.setText(
            f"{view.level_label} · {view.call_range} · {view.detail}"
        )
        self.plan_detail_label.setText(view.confirmation_text)

    def _confirm_intelligence_generation(self, estimate_view):
        level = self._current_intelligence_level()
        if level is IntelligenceLevel.FAST:
            return True
        level_label = self.t(
            "intelligence_standard"
            if level is IntelligenceLevel.STANDARD
            else "intelligence_deep"
        )
        estimate = (
            (
                f"{estimate_view.call_range} · {estimate_view.detail}\n"
                f"{estimate_view.confirmation_text}"
            )
            if estimate_view is not None
            else self.t("intelligence_estimate_pending")
        )
        buttons = getattr(QMessageBox, "StandardButton", QMessageBox)
        choice = QMessageBox.question(
            self,
            self.t("intelligence_confirmation_title"),
            self.t(
                "intelligence_confirmation_body",
                level=level_label,
                estimate=estimate,
            ),
            buttons.Yes | buttons.No,
            buttons.No,
        )
        return choice == buttons.Yes

    def _current_generation_settings(self):
        return GenerationSettings(
            card_mode=self.card_mode_combo.currentData(),
            card_count=self.card_count_combo.currentData(),
            answer_length=self.answer_length_combo.currentData(),
            language=self.output_language_combo.currentData(),
        )

    def _update_card_mode_description(self):
        mode_id = self.card_mode_combo.currentData() or "concept"
        profile = get_card_mode_profile(mode_id)
        self.card_mode_description_label.setText(
            profile.description_zh
            if self.language == "zh"
            else profile.description_en
        )

    def _on_generation_settings_changed(self, *unused):
        self._update_card_mode_description()
        self.session.set_generation_settings(
            self._current_generation_settings()
        )
        self.session.invalidate_document_intelligence_artifacts(
            "generation_settings_changed"
        )
        self._set_generation_message()
        self._after_upstream_change(render_material_count=False)
        self._update_intelligence_estimate()

    def _ai_settings_are_ready(self):
        return bool(
            self.session.material_text.strip()
            and self._ai_runtime_settings is not None
        )

    def _document_imports_pending(self):
        return bool(
            self._document_import_queue.imports_pending
            or self._pending_document_import_requests
            or self._document_import_controller.running
        )

    def _generate_cards(self):
        if (
            self._generation_controller.running
            or self._intelligent_generation_controller.running
        ):
            return
        if self._document_imports_pending():
            self._set_generation_message("document_import_in_progress")
            self._refresh_product_state()
            return
        if not self._ai_settings_are_ready():
            self._set_generation_message("generation_requirements")
            return
        settings = self._ai_runtime_settings
        material_text = self.session.material_text
        if len(material_text) > MAX_AI_MATERIAL_CHARS:
            self._set_generation_message("material_too_long")
            self._refresh_product_state()
            return

        generation_settings = self._current_generation_settings()
        self.session.set_generation_settings(generation_settings)
        has_document_results = bool(
            self._document_import_queue.successful_results
        )
        prepared_run = None
        if has_document_results:
            prepared_run = self._prepare_intelligent_generation_run(
                generation_settings
            )
            if prepared_run is None:
                self._refresh_product_state()
                return
        if has_document_results and not self._confirm_intelligence_generation(
            self._current_intelligence_estimate_view
        ):
            return
        self.session.begin_ai_candidate_generation()
        self._clear_generated_state()
        self._render_cards()
        self.generate_btn.setText(self.t("generation_running"))
        self.generate_btn.setEnabled(False)
        self._set_generation_message("generation_running")
        self.generation_progress_label.setText(
            self.t(
                "document_run_in_progress"
                if has_document_results
                else "generation_running"
            )
        )
        self.generation_progress_label.setVisible(True)
        confirmation_key = (
            endpoint_confirmation_key(settings.base_url)
            if self._endpoint_confirmations.is_confirmed(settings.base_url)
            else None
        )
        if has_document_results:
            self._start_intelligent_generation(
                settings,
                generation_settings,
                confirmation_key,
                run_snapshot=prepared_run,
            )
            self._refresh_product_state()
            return
        panel_reference = weakref.ref(self)

        def handle_completion(completion):
            panel = panel_reference()
            if panel is None or panel._disposed:
                return
            panel._handle_generation_completion(completion)

        self._generation_controller.submit(
            material_text=material_text,
            runtime_settings=settings,
            generation_settings=generation_settings,
            endpoint_confirmation_key=confirmation_key,
            on_complete=handle_completion,
        )
        self._refresh_product_state()

    def _start_intelligent_generation(
        self,
        settings,
        generation_settings,
        confirmation_key,
        *,
        run_snapshot=None,
    ):
        run = run_snapshot
        if run is None:
            try:
                run = build_imported_generation_run(
                    self._document_import_queue.successful_results,
                    generation_settings=generation_settings,
                    level=self._current_intelligence_level(),
                    request_id=self._next_intelligence_request_id + 1,
                )
            except (TypeError, ValueError):
                self._set_generation_message("document_batch_too_complex")
                return
        self._next_intelligence_request_id = run.request_id
        adapter = BoundedProviderGenerationAdapter(
            runtime_settings=settings,
            generation_settings=generation_settings,
            endpoint_confirmation_key=confirmation_key,
        )
        self._active_provider_generation_adapter = adapter
        panel_reference = weakref.ref(self)

        def handle_completion(completion):
            panel = panel_reference()
            if panel is None or panel._disposed:
                return
            panel._handle_intelligent_generation_completion(completion)

        self._intelligent_generation_controller.submit(
            run_snapshot=run,
            generator_callback=adapter,
            planner_callback=adapter.planner_callback,
            critic_callback=adapter.critic_callback,
            repair_callback=adapter.repair_callback,
            supplement_callback=adapter.supplement_callback,
            on_complete=handle_completion,
        )

    def _prepare_intelligent_generation_run(self, generation_settings):
        try:
            return build_imported_generation_run(
                self._document_import_queue.successful_results,
                generation_settings=generation_settings,
                level=self._current_intelligence_level(),
                request_id=self._next_intelligence_request_id + 1,
            )
        except (TypeError, ValueError):
            self._set_generation_message("document_batch_too_complex")
            return None

    def _handle_intelligent_generation_completion(self, completion):
        if self._disposed or self.session.closed:
            return
        run = completion.run
        self._last_intelligence_run = run
        results = self._document_import_queue.successful_results
        self.session.record_document_intelligence_artifacts(
            parsed_documents=tuple(result.document for result in results),
            analyses=tuple(
                result.analysis
                for result in results
                if result.analysis is not None
            ),
            chunks=tuple(
                chunk
                for result in results
                for chunk in result.chunks
            ),
            estimate=self._current_intelligence_estimate_view,
            run=run,
        )
        drafts = drafts_from_generation_run(run)
        if completion.error_code is not None or not drafts:
            self.session.record_ai_card_draft_error(
                BeginnerAIGenerationState.PROVIDER_ERROR,
                completion.error_code or "empty_cards",
            )
            self._set_generation_message("generation_failed")
        else:
            self.session.apply_ai_candidate_card_drafts(drafts)
            self._set_generation_message(
                "generation_success",
                count=len(self.session.candidate_card_previews),
            )
            self._render_cards()
        self.generation_progress_label.setText(
            stage_label(run.stage, language=self.language)
        )
        self.generation_progress_label.setVisible(True)
        retry_available = failed_chunk_retry_is_available(run)
        self.retry_failed_generation_btn.setVisible(retry_available)
        self.retry_failed_generation_btn.setEnabled(retry_available)
        self._refresh_product_state()

    def _retry_failed_generation_chunks(self):
        run = self._last_intelligence_run
        adapter = self._active_provider_generation_adapter
        if (
            run is None
            or adapter is None
            or not failed_chunk_retry_is_available(run)
        ):
            self.retry_failed_generation_btn.setVisible(False)
            self.retry_failed_generation_btn.setEnabled(False)
            return
        self.retry_failed_generation_btn.setVisible(False)
        self.generation_progress_label.setText(
            self.t("document_run_in_progress")
        )
        panel_reference = weakref.ref(self)

        def handle_completion(completion):
            panel = panel_reference()
            if panel is None or panel._disposed:
                return
            panel._handle_intelligent_generation_completion(completion)

        submitted = self._intelligent_generation_controller.retry_failed(
            run_snapshot=run,
            retry_generator_callback=adapter,
            on_complete=handle_completion,
        )
        if submitted is None:
            self.retry_failed_generation_btn.setVisible(False)
            self.retry_failed_generation_btn.setEnabled(False)
        self._refresh_product_state()

    def _handle_generation_completion(self, completion):
        if self._disposed or self.session.closed:
            return
        result = completion.result
        if result is None:
            self.session.record_ai_card_draft_error(
                BeginnerAIGenerationState.PROVIDER_ERROR,
                completion.error_code or "background_task_failed",
            )
            self._set_generation_message("generation_failed")
            self.generation_progress_label.setText(
                stage_label(GenerationStage.FAILED, language=self.language)
            )
            self._refresh_product_state()
            return
        if not result.success:
            self.session.record_ai_card_draft_error(
                result.state,
                result.error_code.value,
            )
            self._set_generation_message(generation_error_message_key(result))
            self.generation_progress_label.setText(
                stage_label(GenerationStage.FAILED, language=self.language)
            )
            self._refresh_product_state()
            return

        self.session.apply_ai_candidate_card_drafts(result.drafts)
        self.generation_progress_label.setText(
            stage_label(GenerationStage.COMPLETED, language=self.language)
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
            self.review_required_label.setVisible(False)
            self.review_stats_label.setVisible(False)
            self.quality_summary_label.setVisible(False)
            self.discard_blocking_btn.setVisible(False)
            self.keep_clean_btn.setVisible(False)
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
        workbench = self.session.review_workbench_snapshot()
        stats = workbench.stats
        self.review_stats_label.setText(
            self.t(
                "review_stats",
                total=stats.total_count,
                pending=stats.pending_count,
                kept=stats.kept_count,
                discarded=stats.discarded_count,
                warnings=stats.warning_count,
                blocking=stats.blocking_count,
            )
        )
        self.review_stats_label.setVisible(True)
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
        self.keep_clean_btn.setVisible(bool(good))

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
                    warning_lines.append(
                        f"• {issue.user_message(self.language)} — "
                        f"{issue.suggestion(self.language)}"
                    )
                quality_detail = QLabel("\n".join(warning_lines))
                quality_detail.setProperty("role", "secondary")
                quality_detail.setWordWrap(True)
                card_layout.addWidget(quality_detail)

            source_view = present_source_location(
                card.source_location,
                card.source_excerpt,
                language=self.language,
            )
            source_btn = QPushButton(source_view.chip)
            source_btn.setObjectName("SourceChip")
            source_btn.setProperty("role", "subtle")
            source_btn.setCheckable(True)
            source_btn.setFlat(True)
            source_btn.setToolTip(source_view.action_label)
            source_label = QLabel(source_view.snippet)
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
            copy_btn = QPushButton(self.t("copy"))
            copy_btn.setProperty("role", "secondary")
            restore_btn = QPushButton(self.t("restore"))
            restore_btn.setProperty("role", "secondary")
            review_card = workbench.card(card.id)
            restore_btn.setEnabled(
                (review_card.front, review_card.back, review_card.source)
                != (
                    review_card.original_front,
                    review_card.original_back,
                    review_card.original_source,
                )
            )
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
            copy_btn.clicked.connect(
                lambda _checked=False, card_id=card.id: self._copy_card(card_id)
            )
            restore_btn.clicked.connect(
                lambda _checked=False, card_id=card.id: self._restore_card(card_id)
            )
            group.addButton(keep_btn)
            group.addButton(discard_btn)
            actions.addWidget(keep_btn)
            actions.addWidget(edit_btn)
            actions.addWidget(copy_btn)
            actions.addWidget(restore_btn)
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

    def _keep_clean_cards(self):
        kept = self.session.keep_clean_candidates()
        if kept:
            self._clear_duplicate_state()
            self._render_cards()
            self._refresh_product_state()

    def _copy_card(self, card_id):
        self.session.copy_candidate(card_id)
        self._clear_duplicate_state()
        self._render_cards()
        self._refresh_product_state()

    def _restore_card(self, card_id):
        self.session.restore_candidate_content(card_id)
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
        suggestion = self.session.suggest_anki_field_mapping()
        if suggestion.front_field:
            self._select_field(
                self.front_field_combo,
                (suggestion.front_field.casefold(),),
            )
        if suggestion.back_field:
            self._select_field(
                self.back_field_combo,
                (suggestion.back_field.casefold(),),
            )
        if suggestion.source_field:
            self._select_field(
                self.source_field_combo,
                (suggestion.source_field.casefold(),),
            )
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
        assessment = self.session.assess_anki_field_mapping()
        if not assessment.complete:
            self.anki_mapping = None
            self._set_target_message("mapping_incomplete")
            self._refresh_product_state()
            return
        self._set_target_message()
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
        last_batch = self.session.last_write_batch
        if last_batch is None:
            self.last_write_label.clear()
            self.last_write_label.setVisible(False)
        else:
            self.last_write_label.setText(
                self.t(
                    "last_write",
                    count=last_batch.written_count,
                    deck=last_batch.target_deck,
                    timestamp=last_batch.timestamp_utc,
                )
            )
            self.last_write_label.setVisible(True)
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
                    note_type=result.note_type,
                    source=result.source_label,
                    timestamp=result.timestamp_utc,
                    batch=result.batch_id,
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

        # The collection can change after the preview was prepared. Re-read the
        # candidate fronts after confirmation and require another confirmation
        # if the writable snapshot changed; never silently bypass duplicates.
        confirmed_snapshot_id = command.snapshot_id
        self._check_duplicates()
        fresh_command = self.write_command
        if (
            fresh_command is None
            or fresh_command.snapshot_id != confirmed_snapshot_id
        ):
            self._set_write_message("duplicate_state_changed")
            self._refresh_product_state()
            return
        command = fresh_command

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
        batch_record = None
        if result.created_note_ids:
            batch_record = create_last_write_batch_record(
                snapshot_id=result.snapshot_id,
                created_note_ids=result.created_note_ids,
                requested_count=command.requested_count,
                skipped_count=result.skipped_count,
                failed_count=result.failed_count,
                target_deck=command.deck_name,
                note_type=command.note_type_name,
                tags=command.tags,
                source_type=self.session.source_type,
                language=self.language,
            )
            self.session.record_last_write_batch(batch_record)
        self.write_result_summary = build_write_result_summary(
            written_count=result.success_count,
            skipped_duplicate_count=result.skipped_count,
            failed_count=result.failed_count,
            target_deck=command.deck_name,
            note_type=command.note_type_name,
            source_label=(
                batch_record.source_label
                if batch_record is not None
                else safe_source_label(self.session.source_type, self.language)
            ),
            timestamp_utc=(
                batch_record.timestamp_utc if batch_record is not None else ""
            ),
            batch_id=batch_record.batch_id if batch_record is not None else "",
            tags=command.tags,
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
        self._generation_controller.invalidate()
        self._intelligent_generation_controller.invalidate()
        self._last_intelligence_run = None
        self._active_provider_generation_adapter = None
        if hasattr(self, "retry_failed_generation_btn"):
            self.retry_failed_generation_btn.setVisible(False)
        if hasattr(self, "generation_progress_label"):
            self.generation_progress_label.clear()
            self.generation_progress_label.setVisible(False)
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
        if (
            self._generation_controller.running
            or self._intelligent_generation_controller.running
        ):
            self.generate_btn.setText(self.t("generation_running"))
            self.generate_btn.setEnabled(False)
            self.generate_btn.setToolTip("")
        else:
            self.generate_btn.setText(
                self.t("regenerate_cards")
                if self.session.candidate_card_previews
                else self.t("generate_cards")
            )
            imports_pending = self._document_imports_pending()
            generation_ready = (
                self._ai_settings_are_ready()
                and not self._document_imports_pending()
            )
            self.generate_btn.setEnabled(generation_ready)
            generation_tooltip = (
                ""
                if generation_ready
                else (
                    self.t("document_import_in_progress")
                    if imports_pending
                    else self.t("generation_requirements")
                )
            )
            self.generate_btn.setToolTip(generation_tooltip)
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
        self._disposed = True
        self._generation_controller.close()
        self._intelligent_generation_controller.close()
        self._document_import_controller.close()
        self._active_provider_generation_adapter = None
        self._last_intelligence_run = None
        self._document_queue_owns_material = False
        self._pending_document_import_requests.clear()
        self._endpoint_confirmations.clear()
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
