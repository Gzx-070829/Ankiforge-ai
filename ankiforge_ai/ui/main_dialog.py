"""
Main dialog for AnkiForge AI (v0.1.2).

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

from aqt.qt import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QCheckBox,
    QFileDialog,
    QWidget,
    QLineEdit,
    Qt,
)
from aqt.utils import showInfo, showWarning

from ..config_loader import default_deck_name, load_provider_config
from ..ai.providers import create_provider
from ..importers.md_importer import split_markdown_by_headings
from ..anki_writer.add_cards import add_cards_to_deck

COLUMN_HEADERS = ["添加", "正面 Front", "背面 Back", "备注 Extra", "来源 Source"]


class MainDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AnkiForge AI")
        self.resize(780, 520)

        self.cards = []
        self.checkboxes = []
        self.file_path = None

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

        # --- generate button ---
        gen_btn = QPushButton("生成卡片（mock，本地模拟，不调用 AI API）")
        gen_btn.clicked.connect(self.generate_cards)
        layout.addWidget(gen_btn)

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
        if not self.file_path:
            showWarning("请先选择一个 Markdown 文件。")
            return

        try:
            chunks = split_markdown_by_headings(self.file_path)
        except OSError as e:
            showWarning(f"读取文件失败: {e}")
            return

        if not chunks:
            showWarning("没有从该文件中解析出任何内容块（文件可能是空的）。")
            return

        try:
            provider = create_provider(load_provider_config())
        except ValueError as e:
            showWarning(str(e))
            return
        except Exception as e:
            showWarning(f"初始化 AI provider 失败: {e}")
            return

        self.cards = []
        try:
            for chunk in chunks:
                self.cards.extend(provider.generate_cards(chunk))
        except Exception as e:
            showWarning(f"生成卡片失败: {e}")
            return

        if not self.cards:
            showWarning("没有生成任何卡片。")
            return

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

    def _item_text(self, row, column):
        item = self.table.item(row, column)
        return item.text().strip() if item is not None else ""
