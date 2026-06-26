"""
Main dialog for AnkiForge AI (v0.2).

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

COLUMN_HEADERS = ["添加", "正面 Front", "背面 Back", "备注 Extra", "来源 Source"]
PROVIDER_OPTIONS = ["mock", "deepseek", "openai_compatible"]


class MainDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AnkiForge AI")
        self.resize(780, 520)

        self.cards = []
        self.checkboxes = []
        self.file_path = None
        self.config = load_config()
        self.generation_in_progress = False

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # --- file picker row ---
        file_row = QHBoxLayout()
        self.file_label = QLabel("未选择文件")
        pick_btn = QPushButton("选择 Markdown 文件...")
        pick_btn.clicked.connect(self.pick_file)
        file_row.addWidget(self.file_label, stretch=1)
        file_row.addWidget(pick_btn)
        layout.addLayout(file_row)

        # --- deck name row ---
        deck_row = QHBoxLayout()
        deck_row.addWidget(QLabel("目标牌组:"))
        self.deck_input = QLineEdit(default_deck_name())
        deck_row.addWidget(self.deck_input)
        layout.addLayout(deck_row)

        # --- provider settings ---
        settings_group = QGroupBox("AI Provider")
        settings_layout = QFormLayout(settings_group)

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
        layout.addWidget(settings_group)
        self._refresh_provider_field_states()

        # --- generate button ---
        self.gen_btn = QPushButton()
        self.gen_btn.clicked.connect(self.generate_cards)
        layout.addWidget(self.gen_btn)
        self._update_generate_button_text()

        # --- preview table ---
        self.table = QTableWidget(0, len(COLUMN_HEADERS))
        self.table.setHorizontalHeaderLabels(COLUMN_HEADERS)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        self.status_label = QLabel("提示：可以直接在表格里修改文字，再决定是否勾选添加。")
        self.status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.status_label)

        # --- bottom buttons ---
        bottom_row = QHBoxLayout()
        clear_btn = QPushButton("清空预览")
        clear_btn.clicked.connect(self.clear_preview)
        bottom_row.addWidget(clear_btn)
        bottom_row.addStretch()
        add_btn = QPushButton("添加到 Anki")
        add_btn.clicked.connect(self.add_to_anki)
        bottom_row.addWidget(add_btn)
        layout.addLayout(bottom_row)

    def pick_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 Markdown 文件", "", "Markdown Files (*.md)"
        )
        if path:
            self.file_path = path
            self.file_label.setText(path)

    def generate_cards(self):
        if self.generation_in_progress:
            showWarning("正在生成卡片，请等待当前任务完成。")
            return
        if not self.file_path:
            showWarning("请先选择一个 Markdown 文件。")
            return
        if not self._save_settings_from_ui(show_success=False):
            return

        try:
            chunks = split_markdown_by_headings(self.file_path)
        except OSError as e:
            showWarning(f"读取文件失败: {e}")
            return

        if not chunks:
            showWarning("没有从该文件中解析出任何内容块（文件可能是空的）。")
            return

        provider_config = load_provider_config()
        self.generation_in_progress = True
        self.gen_btn.setEnabled(False)
        self.status_label.setText(
            f"正在使用 {provider_config.ai_provider} 生成卡片；完成前不会写入 Anki。"
        )
        mw.taskman.run_in_background(
            lambda: self._generate_cards_in_background(chunks, provider_config),
            self._on_generation_done,
        )

    def _generate_cards_in_background(self, chunks, provider_config):
        provider = create_provider(provider_config)
        cards = []
        for chunk in chunks:
            cards.extend(provider.generate_cards(chunk))
        return cards

    def _on_generation_done(self, future):
        self.generation_in_progress = False
        self.gen_btn.setEnabled(True)
        try:
            cards = future.result()
        except Exception as e:
            showWarning(f"生成卡片失败: {e}")
            self.status_label.setText("生成失败；当前预览表未改变，也未写入 Anki。")
            return

        if not cards:
            showWarning("没有生成任何卡片。")
            self.status_label.setText("没有生成任何卡片；当前预览表未改变。")
            return

        self.cards = cards
        self._populate_table()
        self.status_label.setText(
            f"已生成 {len(self.cards)} 张候选卡片；写入前仍可编辑或取消勾选。"
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

            self.table.setItem(row, 1, QTableWidgetItem(card.front))
            self.table.setItem(row, 2, QTableWidgetItem(card.back))
            self.table.setItem(row, 3, QTableWidgetItem(card.extra))
            self.table.setItem(row, 4, QTableWidgetItem(card.source))

        self.table.resizeColumnsToContents()

    def add_to_anki(self):
        if not self.cards:
            showWarning("还没有生成任何卡片，请先点击「生成卡片」。")
            return

        # Pull any edits the user made directly in the table back into the
        # card objects before writing, so manual corrections aren't lost.
        for row, card in enumerate(self.cards):
            card.approved = self.checkboxes[row].isChecked()
            card.front = self._item_text(row, 1)
            card.back = self._item_text(row, 2)
            card.extra = self._item_text(row, 3)
            card.source = self._item_text(row, 4)

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

        message = f"已添加 {result.added} 张卡片到牌组「{deck_name}」。"
        if result.skipped_duplicates:
            message += (
                f"\n已跳过 {result.skipped_duplicates} 张重复卡片"
                "（同 Front + Source）。"
            )
        showInfo(message)
        if result.added:
            self.accept()

    def clear_preview(self):
        self.cards = []
        self.checkboxes = []
        self.table.setRowCount(0)
        self.status_label.setText("已清空当前预览；不会影响已经写入 Anki 的卡片。")

    def save_settings(self):
        self._save_settings_from_ui(show_success=True)

    def on_provider_changed(self, provider_name):
        self._apply_provider_preset_to_ui(provider_name)
        self._refresh_provider_field_states()
        self._update_generate_button_text()

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
            self.gen_btn.setText("生成卡片（mock，本地模拟，不调用 AI API）")
        else:
            self.gen_btn.setText(f"生成卡片（{provider}，后台调用真实 API）")

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
        return True

    def _item_text(self, row, column):
        item = self.table.item(row, column)
        return item.text().strip() if item is not None else ""
