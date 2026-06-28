import unittest
from pathlib import Path


class V05ClosingDocsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).parents[1]
        cls.summary_path = cls.root / "docs" / "pipeline_v0_5_summary.md"
        cls.contract_path = (
            cls.root / "docs" / "pipeline_v0_5_ai_provider_contract.md"
        )
        cls.dev_smoke_path = cls.root / "docs" / "dev_real_provider_smoke.md"
        cls.readme_path = cls.root / "ankiforge_ai" / "README.md"

    def test_required_v0_5_documents_exist_and_are_utf8_readable(self):
        for path in (
            self.summary_path,
            self.contract_path,
            self.dev_smoke_path,
        ):
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file())
                self.assertTrue(path.read_text(encoding="utf-8").strip())

    def test_summary_lists_pr1_through_pr10(self):
        summary = self.summary_path.read_text(encoding="utf-8")

        for number in range(1, 11):
            with self.subTest(pr=number):
                self.assertIn(f"PR{number}", summary)

    def test_summary_records_provider_and_review_safety_chain(self):
        summary = self.summary_path.read_text(encoding="utf-8")
        required_terms = (
            "SourceChunk",
            "KnowledgePointExtractionRequest",
            "KnowledgePointJSONProvider",
            "SafeKnowledgePointJSONProvider",
            "AIKnowledgePointExtractor",
            "KnowledgePointExtractionOutcome",
            "ProviderDryRunSummary",
            "Human Selection",
            "CardCandidate",
            "Quality Gate",
            "Human Review",
            "Write Eligibility",
        )

        for term in required_terms:
            with self.subTest(term=term):
                self.assertIn(term, summary)

    def test_summary_records_core_safety_boundaries(self):
        summary = self.summary_path.read_text(encoding="utf-8")
        required_phrases = (
            "不直接写入 Anki",
            "不提交真实 API key",
            "自动测试不访问真实网络",
            "不是普通用户入口",
            "AI provider 只能进入 KnowledgePoint extraction 阶段",
        )

        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, summary)

    def test_release_checklist_contains_stable_verification_and_artifacts(self):
        summary = self.summary_path.read_text(encoding="utf-8")
        checklist_terms = (
            "python -m unittest discover -s tests",
            "python -m compileall .",
            "git diff --check",
            "git status --short",
            "pipeline_v0_5_ai_provider_contract.md",
            "ai_provider_smoke_source_zh.md",
            "provider_dry_run_summary.py",
            "dev_real_provider_smoke.md",
            "provider-to-Anki write path",
        )

        for term in checklist_terms:
            with self.subTest(term=term):
                self.assertIn(term, summary)

    def test_readme_links_summary_and_dev_smoke_documents(self):
        readme = self.readme_path.read_text(encoding="utf-8")

        self.assertIn("docs/pipeline_v0_5_summary.md", readme)
        self.assertIn("docs/dev_real_provider_smoke.md", readme)
        self.assertIn("dev-only", readme)
        self.assertIn("不会写入", readme)


if __name__ == "__main__":
    unittest.main()
