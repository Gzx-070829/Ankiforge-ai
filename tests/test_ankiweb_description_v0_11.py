import unittest
from pathlib import Path


class AnkiWebDescriptionV011Tests(unittest.TestCase):
    def test_bilingual_draft_prevents_installation_misunderstandings(self):
        draft = (
            Path(__file__).parents[1] / "docs" / "ankiweb_description_v0_11.md"
        ).read_text(encoding="utf-8")

        for required in (
            "这是 Anki 插件，不是共享牌组",
            "不要在 Shared Decks 里搜索",
            "工具 → 插件 → 获取插件",
            "1227582295",
            "它不是网页服务",
            "它不提供现成卡组",
            "API key 仅会话内使用，不保存",
            "Markdown / TXT 导入",
            "基础 DOCX 文本提取",
            "PDF 友好提示",
            "This is an Anki add-on, not a shared deck",
            "Tools → Add-ons → Get Add-ons",
            "It does not run as a web app",
            "It does not include pre-made cards",
            "API key is session-only and is not saved",
            "basic DOCX text extraction",
            "PDF fallback guidance",
        ):
            self.assertIn(required.casefold(), draft.casefold())


if __name__ == "__main__":
    unittest.main()
