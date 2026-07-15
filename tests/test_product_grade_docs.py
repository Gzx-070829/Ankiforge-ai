import unittest
from pathlib import Path


class ProductGradeDocumentationTests(unittest.TestCase):
    REQUIRED_GUIDES = (
        "docs/product_grade_master_plan.md",
        "docs/getting_started.md",
        "docs/installation_ankiweb.md",
        "docs/ai_settings_and_privacy.md",
        "docs/card_modes_and_templates.md",
        "docs/card_quality_system.md",
        "docs/review_workbench.md",
        "docs/field_mapping.md",
        "docs/write_safety_and_traceability.md",
        "docs/importing_materials.md",
        "docs/troubleshooting.md",
        "docs/manual_anki_acceptance.md",
        "docs/v1_candidate_acceptance_checklist.md",
        "docs/future_roadmap.md",
    )

    RELEASE_AND_GROWTH_DOCS = (
        "docs/ankiweb_description_v0_13.md",
        "docs/release_notes_v0_13_product_grade.md",
        "docs/demo_script_v0_13.md",
        "docs/screenshots_checklist_v0_13.md",
        "docs/bilibili_zhihu_demo_outline.md",
        "docs/github_readme_badges_and_assets.md",
    )

    GOVERNANCE_FILES = (
        "SECURITY.md",
        "CONTRIBUTING.md",
        "PRIVACY.md",
        "CODE_OF_CONDUCT.md",
        ".github/ISSUE_TEMPLATE/bug_report.md",
        ".github/ISSUE_TEMPLATE/feature_request.md",
        ".github/ISSUE_TEMPLATE/card_quality_feedback.md",
        ".github/ISSUE_TEMPLATE/ankiweb_installation_help.md",
        ".github/pull_request_template.md",
    )

    def test_required_product_grade_documents_exist(self):
        for relative_path in (
            *self.REQUIRED_GUIDES,
            *self.RELEASE_AND_GROWTH_DOCS,
            *self.GOVERNANCE_FILES,
        ):
            with self.subTest(path=relative_path):
                self.assertTrue(
                    (self.root / relative_path).is_file(),
                    f"Missing product-grade document: {relative_path}",
                )

    def test_readmes_state_the_product_and_safety_boundaries(self):
        zh = self.read("README.md")
        en = self.read("README.en.md")

        self.assert_terms(
            zh,
            "这是 Anki 桌面端插件，不是共享牌组",
            "1227582295",
            "API key",
            "仅在本次会话",
            "人工审核",
            "写入前",
            "PDF",
            "质量提示不能保证",
            "最终卡片负责",
            "测试牌组",
        )
        self.assert_terms(
            en,
            "Anki Desktop add-on, not a shared deck",
            "1227582295",
            "API key",
            "session-only",
            "manual review",
            "before writing",
            "PDF",
            "quality feedback cannot guarantee",
            "responsible for the final cards",
            "test deck",
        )

    def test_readmes_link_to_the_current_user_guides(self):
        combined = self.read("README.md") + self.read("README.en.md")
        for target in (
            "docs/getting_started.md",
            "docs/installation_ankiweb.md",
            "docs/ai_settings_and_privacy.md",
            "docs/card_modes_and_templates.md",
            "docs/card_quality_system.md",
            "docs/review_workbench.md",
            "docs/write_safety_and_traceability.md",
            "docs/importing_materials.md",
            "docs/troubleshooting.md",
        ):
            with self.subTest(target=target):
                self.assertIn(target.casefold(), combined)

    def test_security_policy_covers_product_specific_risks(self):
        text = self.read("SECURITY.md")
        self.assert_terms(
            text,
            "responsible disclosure",
            "API key",
            "Anki data",
            "unintended write",
            "provider privacy",
            "file import",
            "rotate",
        )

    def test_contributing_covers_code_docs_fixtures_and_sensitive_data(self):
        text = self.read("CONTRIBUTING.md")
        self.assert_terms(
            text,
            "code contributions",
            "documentation contributions",
            "card-quality fixture contributions",
            "bug reports",
            "security reports",
            "no real API keys",
            "no user Anki data",
        )

    def test_issue_templates_collect_context_without_secrets(self):
        combined = "\n".join(
            self.read(path)
            for path in self.GOVERNANCE_FILES
            if path.startswith(".github/ISSUE_TEMPLATE/")
        )
        self.assert_terms(
            combined,
            "Anki version",
            "operating system",
            "add-on version",
            "steps",
            "screenshots",
            "material type",
            "provider",
            "do not include",
            "API key",
        )

    def test_pull_request_template_preserves_safety_gates(self):
        text = self.read(".github/pull_request_template.md")
        self.assert_terms(
            text,
            "tests",
            "API key",
            "Anki user data",
            "automatic AI calls",
            "automatic Anki writes",
            "duplicate check",
            "final confirmation",
        )

    def test_v013_release_copy_is_bilingual_and_does_not_overclaim(self):
        ankiweb = self.read("docs/ankiweb_description_v0_13.md")
        release = self.read("docs/release_notes_v0_13_product_grade.md")
        combined = ankiweb + release
        self.assert_terms(
            combined,
            "v0.13.0-product-grade-preview",
            "1227582295",
            "这是 Anki 插件，不是共享牌组",
            "This is an Anki add-on, not a shared deck",
            "session-only",
            "人工审核",
            "manual review",
            "PDF",
            "fallback",
            "test deck",
        )
        for forbidden in (
            "perfect cards",
            "完美卡片",
            "no review required",
            "无需审核",
            "complete pdf parsing",
            "完整 PDF 解析",
            "absolute privacy",
            "绝对隐私保证",
            "fully automated learning",
            "全自动学习系统",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden.casefold(), combined)

    def test_roadmap_has_explicit_version_boundaries(self):
        text = self.read("docs/future_roadmap.md")
        for version in ("v1.0", "v1.1", "v1.2", "v2.0", "v3.0"):
            with self.subTest(version=version):
                self.assertIn(version, text)
        self.assert_terms(
            text,
            "Full undo deferred",
            "OCR",
            "PDF parser",
            "cloud services",
            "not part of v0.13",
        )

    def test_current_guides_are_not_pinned_to_v012(self):
        current = "\n".join(
            self.read(path)
            for path in (
                "README.md",
                "README.en.md",
                "docs/card_quality_system.md",
                "docs/review_workbench.md",
                "docs/write_safety_and_traceability.md",
            )
        )
        self.assertNotIn("v0.12", current)

    @property
    def root(self):
        return Path(__file__).parents[1]

    def read(self, relative_path):
        path = self.root / relative_path
        self.assertTrue(path.is_file(), f"Missing document: {relative_path}")
        return path.read_text(encoding="utf-8").casefold()

    def assert_terms(self, text, *terms):
        for term in terms:
            with self.subTest(term=term):
                self.assertIn(term.casefold(), text)


if __name__ == "__main__":
    unittest.main()
