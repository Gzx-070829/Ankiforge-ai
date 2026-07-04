"""
Main dialog for AnkiForge AI (v0.2.2).

Flow:
    pick a .md file
        -> split into chunks by heading (importers/md_importer.py)
        -> generate cards with the local mock provider
        -> show an editable preview table, each row has an "include" checkbox
        -> on "Add to Anki", re-read any user edits from the table, then
           write only the checked rows (anki_writer/add_cards.py)

Nothing is written to the collection until the user clicks "Add to Anki",
and unchecked rows are never written. No row is added without the user
having had a chance to see and edit it first.
"""

from aqt import mw
from aqt.qt import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QPushButton,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QWidget,
    QLineEdit,
    QTextEdit,
    QSpinBox,
    QDoubleSpinBox,
    Qt,
)
from aqt.utils import showInfo, showWarning

from ..config_loader import (
    PROVIDER_PRESETS,
    default_deck_name,
    load_config,
    load_provider_config,
    save_config,
)
from ..ai.providers import create_provider
from ..importers.md_importer import split_markdown_by_headings
from ..anki_writer.add_cards import add_cards_to_deck
from ..pipeline.orchestrator import (
    extract_mock_knowledge_points,
    run_full_mock_pipeline_with_status,
)
from ..pipeline.card_candidate_preview_adapter import (
    build_card_candidate_preview_items,
)
from ..pipeline.preview_adapter import build_read_only_pipeline_preview
from ..pipeline.provider_preview import ReadOnlyProviderPreview
from ..pipeline.selection_bridge_adapter import (
    build_knowledge_point_preview_items,
    create_selections_from_preview_choice,
)
from .provider_profile_draft_dialog import ProviderProfileDraftDialog
from .provider_preview_dialog import ReadOnlyProviderPreviewDialog
from .human_review_draft_dialog import HumanReviewDecisionDraftDialog
from .beginner_flow_models import ADVANCED_WORKBENCH_WARNING
from .beginner_mode_dialog import BeginnerModeDialog
from .review_helpers import (
    ALL_CHUNKS_LABEL,
    cap_cards,
    chunks_for_combo_index,
    format_chunk_label,
    invert_flags,
    keep_items_by_flags,
    remove_items_by_flags,
    summarize_text,
    tags_from_text,
    tags_to_text,
)

COLUMN_HEADERS = ["添加", "Front", "Back 摘要", "Tags", "状态"]
PROVIDER_OPTIONS = ["mock", "deepseek", "openai_compatible"]


class MainDialog(QDialog):
    def __init__(self, parent=None, provider_preview=None):
        super().__init__(parent)
        if provider_preview is not None and not isinstance(
            provider_preview,
            ReadOnlyProviderPreview,
        ):
            raise ValueError(
                "provider_preview must be ReadOnlyProviderPreview or None."
            )
        self.setWindowTitle("AnkiForge AI")
        self.resize(780, 520)

        self._provider_preview = provider_preview
        self.cards = []
        self.checkboxes = []
        self.chunks = []
        self.file_path = None
        self.generation_in_progress = False
        self.settings_collapsed = True
        self.current_generation_label = ALL_CHUNKS_LABEL
        self._legacy_workbench_built = False

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        beginner_group = QGroupBox("新手模式（推荐）")
        beginner_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        beginner_layout = QVBoxLayout(beginner_group)
        beginner_description = QLabel(
            "默认从只读演练开始，带你完成从学习材料到候选卡审核的流程。"
            "打开窗口不会联网；只有你主动点击 AI 生成按钮后才会按提示联网。"
            "打开窗口不会写入 Anki。"
            "读取结构和重复检查均需主动点击；只有在最终确认页再次明确确认，"
            "才会创建你选中的 Anki note。"
        )
        beginner_description.setWordWrap(True)
        beginner_layout.addWidget(beginner_description)
        self.beginner_entry_btn = QPushButton("开始新手模式")
        self.beginner_entry_btn.clicked.connect(self.show_beginner_mode)
        beginner_layout.addWidget(self.beginner_entry_btn)
        layout.addWidget(beginner_group)

        legacy_group = QGroupBox("旧版工作台（高级）")
        legacy_group.setToolTip(ADVANCED_WORKBENCH_WARNING)
        legacy_layout = QVBoxLayout(legacy_group)
        legacy_description = QLabel(
            "这里保留开发/调试功能，可能包含真实 Provider 设置或旧版添加到 Anki "
            "入口。请确认你理解风险后再进入。"
        )
        legacy_description.setWordWrap(True)
        legacy_description.setStyleSheet("color: gray;")
        legacy_layout.addWidget(legacy_description)
        self.legacy_entry_btn = QPushButton("打开旧版工作台")
        self.legacy_entry_btn.clicked.connect(self.show_legacy_workbench)
        legacy_layout.addWidget(self.legacy_entry_btn)
        layout.addWidget(legacy_group)

        self.legacy_workbench_container = QWidget()
        self.legacy_workbench_container.setVisible(False)
        layout.addWidget(self.legacy_workbench_container, 1)

    def show_beginner_mode(self):
        main_window = self.parent()
        collection = getattr(main_window, "col", None)
        BeginnerModeDialog(parent=self, collection=collection).exec()

    def show_legacy_workbench(self):
        if not self._legacy_workbench_built:
            self._build_legacy_workbench()
        self.legacy_workbench_container.setVisible(True)
        self.legacy_entry_btn.setEnabled(False)

    def _build_legacy_workbench(self):
        self.config = load_config()
        layout = QVBoxLayout(self.legacy_workbench_container)

        # --- file picker row ---
        file_row = QHBoxLayout()
        self.file_label = QLabel("未选择文件")
        pick_btn = QPushButton("选择 Markdown 文件...")
        pick_btn.clicked.connect(self.pick_file)
        self.pipeline_preview_btn = QPushButton("Mock Pipeline 只读预览")
        self.pipeline_preview_btn.setEnabled(False)
        self.pipeline_preview_btn.clicked.connect(self.show_pipeline_preview)
        self.knowledge_selection_btn = QPushButton("Mock 知识点选择")
        self.knowledge_selection_btn.setEnabled(False)
        self.knowledge_selection_btn.clicked.connect(self.show_knowledge_point_selection)
        self.human_review_draft_btn = QPushButton("Human Review 决策草稿")
        self.human_review_draft_btn.setToolTip(
            "仅使用离线 mock pipeline 候选形成当前弹窗内的审核草稿；不写入 Anki。"
        )
        self.human_review_draft_btn.clicked.connect(
            self.show_human_review_decision_draft
        )
        file_row.addWidget(self.file_label, stretch=1)
        file_row.addWidget(pick_btn)
        file_row.addWidget(self.pipeline_preview_btn)
        file_row.addWidget(self.knowledge_selection_btn)
        file_row.addWidget(self.human_review_draft_btn)
        layout.addLayout(file_row)

        # --- chunk selector row ---
        chunk_row = QHBoxLayout()
        chunk_row.addWidget(QLabel("生成范围:"))
        self.chunk_combo = QComboBox()
        self.chunk_combo.addItem("全部 headings")
        self.chunk_combo.setEnabled(False)
        chunk_row.addWidget(self.chunk_combo, stretch=1)
        layout.addLayout(chunk_row)

        # --- deck name row ---
        deck_row = QHBoxLayout()
        deck_row.addWidget(QLabel("目标牌组:"))
        self.deck_input = QLineEdit(default_deck_name())
        deck_row.addWidget(self.deck_input)
        layout.addLayout(deck_row)

        # --- provider settings ---
        settings_header = QHBoxLayout()
        self.settings_summary_label = QLabel()
        self.settings_toggle_btn = QPushButton("展开设置")
        self.settings_toggle_btn.clicked.connect(self.toggle_settings)
        self.provider_draft_preview_btn = QPushButton(
            "新 Pipeline Provider 本地草稿预览"
        )
        self.provider_draft_preview_btn.setToolTip(
            "仅编辑当前弹窗中的非敏感草稿；不保存、不发送、不调用 provider。"
        )
        self.provider_draft_preview_btn.clicked.connect(
            self.show_provider_profile_draft_preview
        )
        self.provider_preview_btn = QPushButton("新 Pipeline Provider 只读预览")
        self.provider_preview_btn.setToolTip(
            "只显示显式注入的新 pipeline 安全投影；不读取或验证旧 API key。"
        )
        self.provider_preview_btn.clicked.connect(self.show_provider_preview)
        settings_header.addWidget(self.settings_summary_label, stretch=1)
        settings_header.addWidget(self.provider_draft_preview_btn)
        settings_header.addWidget(self.provider_preview_btn)
        settings_header.addWidget(self.settings_toggle_btn)
        layout.addLayout(settings_header)

        self.settings_group = QGroupBox("AI Provider 设置")
        settings_layout = QFormLayout(self.settings_group)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(PROVIDER_OPTIONS)
        provider = self.config.get("ai_provider", "mock")
        self.provider_combo.setCurrentText(provider if provider in PROVIDER_OPTIONS else "mock")
        self.provider_combo.currentTextChanged.connect(self.on_provider_changed)
        settings_layout.addRow("Provider:", self.provider_combo)

        self.model_input = QLineEdit(str(self.config.get("model") or ""))
        settings_layout.addRow("Model:", self.model_input)

        self.api_base_url_input = QLineEdit(str(self.config.get("api_base_url") or ""))
        settings_layout.addRow("API Base URL:", self.api_base_url_input)

        self.api_key_input = QLineEdit(str(self.config.get("api_key") or ""))
        password_mode = (
            QLineEdit.EchoMode.Password
            if hasattr(QLineEdit, "EchoMode")
            else QLineEdit.Password
        )
        self.api_key_input.setEchoMode(password_mode)
        settings_layout.addRow("API Key:", self.api_key_input)

        self.timeout_input = QSpinBox()
        self.timeout_input.setRange(1, 600)
        self.timeout_input.setValue(int(self.config.get("timeout_seconds") or 60))
        settings_layout.addRow("Timeout 秒:", self.timeout_input)

        self.temperature_input = QDoubleSpinBox()
        self.temperature_input.setRange(0.0, 2.0)
        self.temperature_input.setSingleStep(0.1)
        self.temperature_input.setDecimals(2)
        self.temperature_input.setValue(float(self.config.get("temperature") or 0.2))
        settings_layout.addRow("Temperature:", self.temperature_input)

        self.max_cards_input = QSpinBox()
        self.max_cards_input.setRange(1, 20)
        self.max_cards_input.setValue(int(self.config.get("max_cards_per_chunk") or 3))
        settings_layout.addRow("Max cards/chunk:", self.max_cards_input)

        save_settings_btn = QPushButton("保存设置")
        save_settings_btn.clicked.connect(self.save_settings)
        settings_layout.addRow(save_settings_btn)
        layout.addWidget(self.settings_group)
        self._refresh_provider_field_states()
        self._update_settings_summary()
        self._set_settings_collapsed(True)

        # --- generate buttons ---
        generate_row = QHBoxLayout()
        self.gen_btn = QPushButton()
        self.gen_btn.clicked.connect(lambda: self.generate_cards(False))
        generate_row.addWidget(self.gen_btn)
        self.gen_current_btn = QPushButton("生成/重新生成当前 chunk")
        self.gen_current_btn.clicked.connect(lambda: self.generate_cards(True))
        generate_row.addWidget(self.gen_current_btn)
        layout.addLayout(generate_row)
        self._update_generate_button_text()

        # --- preview table ---
        self.table = QTableWidget(0, len(COLUMN_HEADERS))
        self.table.setHorizontalHeaderLabels(COLUMN_HEADERS)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.cellDoubleClicked.connect(self.edit_card_details)
        layout.addWidget(self.table)

        # --- candidate action buttons ---
        action_row = QHBoxLayout()
        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(self.select_all_cards)
        select_none_btn = QPushButton("全不选")
        select_none_btn.clicked.connect(self.select_no_cards)
        invert_btn = QPushButton("反选")
        invert_btn.clicked.connect(self.invert_card_selection)
        edit_btn = QPushButton("编辑详情")
        edit_btn.clicked.connect(self.edit_current_card_details)
        delete_selected_btn = QPushButton("删除选中")
        delete_selected_btn.clicked.connect(self.delete_selected_cards)
        clear_unselected_btn = QPushButton("清空未选中")
        clear_unselected_btn.clicked.connect(self.clear_unselected_cards)
        clear_btn = QPushButton("清空预览")
        clear_btn.clicked.connect(self.clear_preview)

        for button in [
            select_all_btn,
            select_none_btn,
            invert_btn,
            edit_btn,
            delete_selected_btn,
            clear_unselected_btn,
            clear_btn,
        ]:
            action_row.addWidget(button)
        layout.addLayout(action_row)

        self.status_label = QLabel("提示：可以直接在表格里修改文字，再决定是否勾选添加。")
        self.status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.status_label)

        # --- bottom buttons ---
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        add_btn = QPushButton("添加到 Anki")
        add_btn.clicked.connect(self.add_to_anki)
        bottom_row.addWidget(add_btn)
        layout.addLayout(bottom_row)
        self._legacy_workbench_built = True

    def pick_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 Markdown 文件", "", "Markdown Files (*.md)"
        )
        if path:
            self.file_path = path
            self.file_label.setText(path)
            self.pipeline_preview_btn.setEnabled(True)
            self.knowledge_selection_btn.setEnabled(True)
            self._load_chunks_for_selected_file()

    def show_pipeline_preview(self):
        if not self.file_path:
            showWarning("请先选择一个 Markdown 文件。")
            return

        outcome = run_full_mock_pipeline_with_status(self.file_path)
        preview_data = build_read_only_pipeline_preview(outcome)
        ReadOnlyPipelinePreviewDialog(preview_data, self).exec()

    def show_provider_preview(self):
        ReadOnlyProviderPreviewDialog(self._provider_preview, self).exec()

    def show_provider_profile_draft_preview(self):
        ProviderProfileDraftDialog(parent=self).exec()

    def show_human_review_decision_draft(self):
        preview_items = ()
        if self.file_path:
            outcome = run_full_mock_pipeline_with_status(self.file_path)
            if outcome.result is not None:
                preview_items = build_card_candidate_preview_items(
                    outcome.result.card_candidates,
                    outcome.result.quality_results,
                )
        HumanReviewDecisionDraftDialog(preview_items, self).exec()

    def show_knowledge_point_selection(self):
        if not self.file_path:
            showWarning("请先选择一个 Markdown 文件。")
            return

        try:
            points = extract_mock_knowledge_points(self.file_path)
        except Exception as error:
            showWarning(f"提取 mock 知识点失败: {error}")
            return

        preview_items = build_knowledge_point_preview_items(points)
        if not preview_items:
            showWarning("没有可供选择的知识点。")
            return

        selection_dialog = KnowledgePointSelectionDialog(preview_items, self)
        if not selection_dialog.exec():
            return

        try:
            selections = create_selections_from_preview_choice(
                points,
                selection_dialog.selected_point_ids(),
            )
        except ValueError as error:
            showWarning(str(error))
            return

        outcome = run_full_mock_pipeline_with_status(
            self.file_path,
            selected_point_ids=[selection.point_id for selection in selections],
        )
        preview_data = build_read_only_pipeline_preview(outcome)
        ReadOnlyPipelinePreviewDialog(preview_data, self).exec()

    def _load_chunks_for_selected_file(self):
        try:
            self.chunks = split_markdown_by_headings(self.file_path)
        except OSError as e:
            self.chunks = []
            self._refresh_chunk_combo()
            showWarning(f"读取文件失败: {e}")
            return False

        self._refresh_chunk_combo()
        self._clear_preview_data()
        if not self.chunks:
            self.status_label.setText("没有从该文件中解析出任何 Markdown chunks。")
            showWarning("没有从该文件中解析出任何内容块（文件可能是空的）。")
            return False

        self.status_label.setText(f"已解析 {len(self.chunks)} 个 Markdown chunks。")
        return True

    def _refresh_chunk_combo(self):
        self.chunk_combo.clear()
        self.chunk_combo.addItem(ALL_CHUNKS_LABEL)
        for index, chunk in enumerate(self.chunks):
            self.chunk_combo.addItem(format_chunk_label(chunk, index))
        self.chunk_combo.setEnabled(bool(self.chunks))

    def _chunks_for_generation(self, current_chunk_only):
        return chunks_for_combo_index(
            self.chunks,
            self.chunk_combo.currentIndex(),
            current_chunk_only,
        )

    def generate_cards(self, current_chunk_only=False):
        if self.generation_in_progress:
            showWarning("正在生成卡片，请等待当前任务完成。")
            return
        if not self.file_path:
            showWarning("请先选择一个 Markdown 文件。")
            return
        if not self._save_settings_from_ui(show_success=False):
            return

        if not self.chunks and not self._load_chunks_for_selected_file():
            return

        chunks, target_label = self._chunks_for_generation(current_chunk_only)
        if not chunks:
            message = "请先选择一个具体 heading。"
            showWarning(message)
            self.status_label.setText(message)
            return

        provider_config = load_provider_config()
        self.current_generation_label = target_label
        self.generation_in_progress = True
        self.gen_btn.setEnabled(False)
        self.gen_current_btn.setEnabled(False)
        self.status_label.setText(
            f"正在使用 {provider_config.ai_provider}/{provider_config.model} 生成："
            f"{target_label}"
        )
        mw.taskman.run_in_background(
            lambda: self._generate_cards_in_background(chunks, provider_config),
            self._on_generation_done,
        )

    def _generate_cards_in_background(self, chunks, provider_config):
        provider = create_provider(provider_config)
        cards = []
        for chunk in chunks:
            generated = provider.generate_cards(chunk)
            cards.extend(cap_cards(generated, provider_config.max_cards_per_chunk))
        return cards

    def _on_generation_done(self, future):
        self.generation_in_progress = False
        self.gen_btn.setEnabled(True)
        self.gen_current_btn.setEnabled(True)
        try:
            cards = future.result()
        except Exception as e:
            showWarning(f"生成卡片失败: {e}")
            self.status_label.setText("生成失败，预览未改变，未写入 Anki。")
            return

        if not cards:
            showWarning("没有生成任何卡片。")
            self.status_label.setText("没有生成任何卡片；当前预览表未改变。")
            return

        self.cards = cards
        self._populate_table()
        self.status_label.setText(
            f"已从 {self.current_generation_label} 生成 {len(self.cards)} 张候选卡，"
            "尚未写入 Anki。"
        )

    def _populate_table(self):
        self.table.setRowCount(len(self.cards))
        self.checkboxes = []

        for row, card in enumerate(self.cards):
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            container = QWidget()
            inner_layout = QHBoxLayout(container)
            inner_layout.addWidget(checkbox)
            inner_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            inner_layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row, 0, container)
            self.checkboxes.append(checkbox)

            self.table.setItem(row, 1, self._readonly_item(card.front))
            self.table.setItem(row, 2, self._readonly_item(summarize_text(card.back)))
            self.table.setItem(row, 3, self._readonly_item(tags_to_text(card.tags)))
            self.table.setItem(row, 4, self._readonly_item("候选"))

        self.table.resizeColumnsToContents()

    def select_all_cards(self):
        self._set_all_checkboxes(True)
        self.status_label.setText(f"已全选 {len(self.cards)} 张候选卡。")

    def select_no_cards(self):
        self._set_all_checkboxes(False)
        self.status_label.setText("已取消选择所有候选卡。")

    def invert_card_selection(self):
        for checkbox, checked in zip(self.checkboxes, invert_flags(self._checked_flags())):
            checkbox.setChecked(checked)
        self.status_label.setText("已反选当前候选卡。")

    def delete_selected_cards(self):
        flags = self._checked_flags()
        self.cards, removed = remove_items_by_flags(self.cards, flags)
        self._populate_table()
        self.status_label.setText(f"已删除 {removed} 张候选卡。")

    def clear_unselected_cards(self):
        flags = self._checked_flags()
        self.cards, removed = keep_items_by_flags(self.cards, flags)
        self._populate_table()
        self.status_label.setText(f"已删除 {removed} 张未选中候选卡。")

    def edit_current_card_details(self):
        self.edit_card_details(self.table.currentRow())

    def edit_card_details(self, row, column=None):
        if row < 0 or row >= len(self.cards):
            showWarning("请先选择一张候选卡。")
            return

        dialog = CardDetailDialog(self.cards[row], self)
        if dialog.exec():
            dialog.apply_to_card(self.cards[row])
            self._populate_table()
            self.table.selectRow(row)
            self.status_label.setText(f"已更新第 {row + 1} 张候选卡。")

    def _checked_flags(self):
        return [checkbox.isChecked() for checkbox in self.checkboxes]

    def _set_all_checkboxes(self, checked):
        for checkbox in self.checkboxes:
            checkbox.setChecked(checked)

    def add_to_anki(self):
        if not self.cards:
            showWarning("还没有生成任何卡片，请先点击「生成卡片」。")
            return

        for row, card in enumerate(self.cards):
            card.approved = self.checkboxes[row].isChecked()

        approved_count = sum(1 for c in self.cards if c.approved)
        if approved_count == 0:
            showWarning("没有勾选任何卡片，已取消添加。")
            return

        invalid_rows = [
            str(row + 1)
            for row, card in enumerate(self.cards)
            if card.approved and (not card.front.strip() or not card.back.strip())
        ]
        if invalid_rows:
            showWarning(
                "以下已勾选卡片缺少 Front 或 Back，暂未写入："
                + ", ".join(invalid_rows)
            )
            return

        deck_name = self.deck_input.text().strip() or default_deck_name()
        try:
            result = add_cards_to_deck(self.cards, deck_name)
        except ValueError as e:
            showWarning(str(e))
            return
        except Exception as e:
            showWarning(f"写入 Anki 失败: {e}")
            return

        message = (
            f"新增 {result.added} 张，跳过重复 {result.skipped_duplicates} 张，"
            "预览已清空。"
        )
        showInfo(message)
        self._clear_preview_data()
        self.status_label.setText(message)

    def clear_preview(self):
        self._clear_preview_data()
        self.status_label.setText("已清空当前预览；不会影响已经写入 Anki 的卡片。")

    def _clear_preview_data(self):
        self.cards = []
        self.checkboxes = []
        self.table.setRowCount(0)

    def save_settings(self):
        self._save_settings_from_ui(show_success=True)

    def toggle_settings(self):
        self._set_settings_collapsed(not self.settings_collapsed)

    def _set_settings_collapsed(self, collapsed):
        self.settings_collapsed = collapsed
        self.settings_group.setVisible(not collapsed)
        self.settings_toggle_btn.setText("展开设置" if collapsed else "收起设置")
        self._update_settings_summary()

    def _update_settings_summary(self):
        provider = self.provider_combo.currentText()
        model = self.model_input.text().strip() or "(未设置模型)"
        self.settings_summary_label.setText(f"Provider: {provider} / {model}")

    def on_provider_changed(self, provider_name):
        self._apply_provider_preset_to_ui(provider_name)
        self._refresh_provider_field_states()
        self._update_generate_button_text()
        self._update_settings_summary()

    def _apply_provider_preset_to_ui(self, provider_name):
        preset = PROVIDER_PRESETS.get(provider_name)
        if not preset:
            return
        if provider_name == "mock":
            self.model_input.setText(preset["model"])
            self.api_base_url_input.setText("")
        elif provider_name == "deepseek":
            if not self.model_input.text().strip() or self.model_input.text().startswith("mock-"):
                self.model_input.setText(preset["model"])
            if not self.api_base_url_input.text().strip():
                self.api_base_url_input.setText(preset["api_base_url"])

    def _refresh_provider_field_states(self):
        real_provider = self.provider_combo.currentText() != "mock"
        self.api_base_url_input.setEnabled(real_provider)
        self.api_key_input.setEnabled(real_provider)
        self.timeout_input.setEnabled(real_provider)
        self.temperature_input.setEnabled(real_provider)
        self.model_input.setEnabled(True)

    def _update_generate_button_text(self):
        provider = self.provider_combo.currentText()
        if provider == "mock":
            self.gen_btn.setText("生成/重新生成全部（mock，本地）")
            self.gen_current_btn.setText("生成/重新生成当前 chunk（mock，本地）")
        else:
            self.gen_btn.setText(f"生成/重新生成全部（{provider}，后台 API）")
            self.gen_current_btn.setText(f"生成/重新生成当前 chunk（{provider}）")

    def _save_settings_from_ui(self, show_success):
        self.config.update(
            {
                "ai_provider": self.provider_combo.currentText(),
                "model": self.model_input.text().strip(),
                "api_base_url": self.api_base_url_input.text().strip(),
                "api_key": self.api_key_input.text().strip(),
                "timeout_seconds": self.timeout_input.value(),
                "temperature": self.temperature_input.value(),
                "max_cards_per_chunk": self.max_cards_input.value(),
                "default_deck": self.deck_input.text().strip() or default_deck_name(),
            }
        )
        try:
            save_config(self.config)
        except OSError as e:
            showWarning(f"保存配置失败: {e}")
            return False

        if show_success:
            showInfo("设置已保存。")
        self._update_settings_summary()
        return True

    def _readonly_item(self, text):
        item = QTableWidgetItem(str(text or ""))
        try:
            editable_flag = Qt.ItemFlag.ItemIsEditable
        except AttributeError:
            editable_flag = Qt.ItemIsEditable
        item.setFlags(item.flags() & ~editable_flag)
        return item

    def _item_text(self, row, column):
        item = self.table.item(row, column)
        return item.text().strip() if item is not None else ""


class KnowledgePointSelectionDialog(QDialog):
    def __init__(self, preview_items, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mock Pipeline 知识点选择")
        self.resize(900, 520)
        self.preview_items = list(preview_items)
        self.checkboxes = []

        layout = QVBoxLayout(self)
        headers = [
            "选择",
            "Title",
            "Explanation",
            "Importance",
            "Tags",
            "Source",
            "Evidence",
        ]
        table = QTableWidget(len(self.preview_items), len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setStretchLastSection(True)

        for row, item in enumerate(self.preview_items):
            checkbox = QCheckBox()
            checkbox.setChecked(item.default_selected)
            container = QWidget()
            checkbox_layout = QHBoxLayout(container)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            table.setCellWidget(row, 0, container)
            self.checkboxes.append(checkbox)

            values = [
                item.title,
                item.explanation,
                item.importance,
                tags_to_text(item.tags),
                item.source_display,
                item.evidence,
            ]
            for column, value in enumerate(values, start=1):
                table.setItem(row, column, self._readonly_item(value))

        table.resizeColumnsToContents()
        layout.addWidget(table)

        button_row = QHBoxLayout()
        button_row.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        continue_btn = QPushButton("继续只读预览")
        continue_btn.clicked.connect(self.accept)
        button_row.addWidget(cancel_btn)
        button_row.addWidget(continue_btn)
        layout.addLayout(button_row)

    def selected_point_ids(self):
        return [
            item.point_id
            for item, checkbox in zip(self.preview_items, self.checkboxes)
            if checkbox.isChecked()
        ]

    def _readonly_item(self, text):
        item = QTableWidgetItem("" if text is None else str(text))
        try:
            editable_flag = Qt.ItemFlag.ItemIsEditable
        except AttributeError:
            editable_flag = Qt.ItemIsEditable
        item.setFlags(item.flags() & ~editable_flag)
        return item


class ReadOnlyPipelinePreviewDialog(QDialog):
    def __init__(self, preview_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mock Pipeline 只读预览")
        self.resize(980, 560)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Run status: {preview_data.run_status}"))
        if preview_data.failed_stage:
            layout.addWidget(QLabel(f"Failed stage: {preview_data.failed_stage}"))
        if preview_data.error_message:
            error_label = QLabel(f"Error: {preview_data.error_message}")
            error_label.setWordWrap(True)
            layout.addWidget(error_label)

        summary_table = QTableWidget(len(preview_data.summary_counts), 2)
        summary_table.setHorizontalHeaderLabels(["Summary", "Count"])
        for row, (name, count) in enumerate(preview_data.summary_counts.items()):
            summary_table.setItem(row, 0, self._readonly_item(name))
            summary_table.setItem(row, 1, self._readonly_item(count))
        summary_table.resizeColumnsToContents()
        layout.addWidget(summary_table)

        card_headers = [
            "Candidate ID",
            "Front preview",
            "Back preview",
            "Quality",
            "Issues",
            "Review",
            "Write eligible",
        ]
        card_table = QTableWidget(len(preview_data.cards), len(card_headers))
        card_table.setHorizontalHeaderLabels(card_headers)
        card_table.horizontalHeader().setStretchLastSection(False)
        write_eligible_column = len(card_headers) - 1
        for row, item in enumerate(preview_data.cards):
            issue_text = (
                str(item.quality_issue_count)
                if item.quality_issue_count is not None
                else ""
            )
            values = [
                item.candidate_id,
                item.front_preview,
                item.back_preview,
                item.quality_status,
                issue_text,
                item.review_status,
                "yes" if item.review_allows_write else "no",
            ]
            for column, value in enumerate(values):
                card_table.setItem(row, column, self._readonly_item(value))
        card_table.resizeColumnsToContents()
        card_table.setColumnHidden(write_eligible_column, False)
        card_table.setColumnWidth(
            write_eligible_column,
            max(card_table.columnWidth(write_eligible_column), 110),
        )
        layout.addWidget(card_table)

        button_row = QHBoxLayout()
        button_row.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        button_row.addWidget(close_btn)
        layout.addLayout(button_row)

    def _readonly_item(self, text):
        item = QTableWidgetItem("" if text is None else str(text))
        try:
            editable_flag = Qt.ItemFlag.ItemIsEditable
        except AttributeError:
            editable_flag = Qt.ItemIsEditable
        item.setFlags(item.flags() & ~editable_flag)
        return item


class CardDetailDialog(QDialog):
    def __init__(self, card, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑候选卡详情")
        self.resize(640, 560)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.front_edit = QTextEdit(card.front)
        self.back_edit = QTextEdit(card.back)
        self.extra_edit = QTextEdit(card.extra)
        self.tags_edit = QTextEdit(tags_to_text(card.tags))
        self.source_edit = QTextEdit(card.source)

        form.addRow("Front:", self.front_edit)
        form.addRow("Back:", self.back_edit)
        form.addRow("Extra:", self.extra_edit)
        form.addRow("Tags:", self.tags_edit)
        form.addRow("Source:", self.source_edit)
        form.addRow(QLabel("Source 是普通字段；修改它会影响 duplicate check。"))
        layout.addLayout(form)

        button_row = QHBoxLayout()
        button_row.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.accept)
        button_row.addWidget(cancel_btn)
        button_row.addWidget(save_btn)
        layout.addLayout(button_row)

    def apply_to_card(self, card):
        card.front = self.front_edit.toPlainText().strip()
        card.back = self.back_edit.toPlainText().strip()
        card.extra = self.extra_edit.toPlainText().strip()
        card.tags = tags_from_text(self.tags_edit.toPlainText())
        card.source = self.source_edit.toPlainText().strip()
