"""
Main dialog for AnkiForge AI (v0.1).

Flow:
    pick a .md file
        -> split into chunks by heading (importers/md_importer.py)
        -> generate cards, currently mocked (ai/schemas.py)
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

from ..importers.md_importer import split_markdown_by_headings
from ..ai.schemas import mock_generate_cards
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
        self.deck_input = QLineEdit("AnkiForge::Inbox")
        deck_row.addWidget(self.deck_input)
        layout.addLayout(deck_row)

        # --- generate button ---
        gen_btn = QPushButton("生成卡片（v0.1 为模拟数据，尚未调用 AI API）")
        gen_btn.clicked.connect(self.generate_cards)
        layout.addWidget(gen_btn)

        # --- preview table ---
        self.table = QTableWidget(0, len(COLUMN_HEADERS))
        self.table.setHorizontalHeaderLabels(COLUMN_HEADERS)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        hint = QLabel("提示：可以直接在表格里修改文字，再决定是否勾选添加。")
        hint.setStyleSheet("color: gray;")
        layout.addWidget(hint)

        # --- bottom buttons ---
        bottom_row = QHBoxLayout()
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

        self.cards = []
        for chunk in chunks:
            self.cards.extend(mock_generate_cards(chunk))

        self._populate_table()

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
            card.front = self.table.item(row, 1).text()
            card.back = self.table.item(row, 2).text()
            card.extra = self.table.item(row, 3).text()
            card.source = self.table.item(row, 4).text()

        approved_count = sum(1 for c in self.cards if c.approved)
        if approved_count == 0:
            showWarning("没有勾选任何卡片，已取消添加。")
            return

        deck_name = self.deck_input.text().strip() or "AnkiForge::Inbox"
        added = add_cards_to_deck(self.cards, deck_name)
        showInfo(f"已添加 {added} 张卡片到牌组「{deck_name}」。")
        self.accept()
