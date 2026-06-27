import ast
import copy
import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

from ankiforge_ai.pipeline.controlled_write_bridge import (
    PipelineWriteEligibility,
    build_pipeline_write_eligibility,
    build_write_ready_preview_item,
    build_write_ready_preview_items,
)
from ankiforge_ai.pipeline.human_review import create_human_review
from ankiforge_ai.pipeline.models import (
    CardCandidate,
    QualityGateResult,
    QualityIssue,
)


class ControlledWriteBridgeTests(unittest.TestCase):
    def setUp(self):
        self.candidate = self._candidate("cc_selection_1_0", "什么是过拟合？")
        self.passed = QualityGateResult(self.candidate.candidate_id, [])
        self.warning = QualityGateResult(
            self.candidate.candidate_id,
            [QualityIssue("back_too_short", "Back is short.", "warning")],
        )
        self.failed = QualityGateResult(
            self.candidate.candidate_id,
            [QualityIssue("empty_back", "Back is required.", "error")],
        )

    def test_pending_is_not_eligible(self):
        review = create_human_review(self.candidate, self.passed)
        eligibility = build_pipeline_write_eligibility(
            self.candidate, self.passed, review
        )

        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.reasons, ("review_not_approved",))

    def test_rejected_is_not_eligible(self):
        review = create_human_review(
            self.candidate, self.passed, decision="rejected"
        )
        eligibility = build_pipeline_write_eligibility(
            self.candidate, self.passed, review
        )

        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.review_status, "rejected")

    def test_needs_edit_is_not_eligible(self):
        review = create_human_review(
            self.candidate, self.passed, decision="needs_edit"
        )

        self.assertFalse(
            build_pipeline_write_eligibility(
                self.candidate, self.passed, review
            ).eligible
        )

    def test_missing_review_is_not_eligible(self):
        eligibility = build_pipeline_write_eligibility(
            self.candidate, self.passed, None
        )

        self.assertEqual(eligibility.review_status, "unreviewed")
        self.assertEqual(eligibility.reasons, ("review_missing",))

    def test_missing_quality_result_is_not_eligible(self):
        approved = create_human_review(
            self.candidate, self.passed, decision="approved"
        )
        eligibility = build_pipeline_write_eligibility(
            self.candidate, None, approved
        )

        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.quality_status, "unchecked")
        self.assertEqual(eligibility.reasons, ("quality_unchecked",))

    def test_approved_passed_is_write_ready(self):
        approved = create_human_review(
            self.candidate, self.passed, decision="approved"
        )
        eligibility = build_pipeline_write_eligibility(
            self.candidate, self.passed, approved
        )
        item = build_write_ready_preview_item(
            self.candidate, self.passed, approved
        )

        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.reasons, ())
        self.assertEqual(item.quality_status, "passed")
        self.assertEqual(item.review_status, "approved")

    def test_approved_warning_is_write_ready(self):
        approved = create_human_review(
            self.candidate, self.warning, decision="approved"
        )
        item = build_write_ready_preview_item(
            self.candidate, self.warning, approved
        )

        self.assertEqual(item.quality_status, "warning")
        self.assertEqual(item.review_status, "approved")

    def test_approved_failed_is_not_eligible(self):
        approved = create_human_review(
            self.candidate, self.passed, decision="approved"
        )
        eligibility = build_pipeline_write_eligibility(
            self.candidate, self.failed, approved
        )

        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.reasons, ("quality_failed",))
        with self.assertRaisesRegex(ValueError, "quality_failed"):
            build_write_ready_preview_item(
                self.candidate, self.failed, approved
            )

    def test_reasons_have_stable_order(self):
        no_state = build_pipeline_write_eligibility(self.candidate)
        pending = create_human_review(self.candidate, self.failed)
        failed_pending = build_pipeline_write_eligibility(
            self.candidate, self.failed, pending
        )

        self.assertEqual(
            no_state.reasons,
            ("quality_unchecked", "review_missing"),
        )
        self.assertEqual(
            failed_pending.reasons,
            ("quality_failed", "review_not_approved"),
        )

    def test_candidate_id_mismatch_raises(self):
        wrong_quality = QualityGateResult("other", [])
        approved = create_human_review(
            self.candidate, self.passed, decision="approved"
        )
        wrong_review = replace(approved, candidate_id="other")

        with self.assertRaises(ValueError):
            build_pipeline_write_eligibility(
                self.candidate, wrong_quality, approved
            )
        with self.assertRaises(ValueError):
            build_pipeline_write_eligibility(
                self.candidate, self.passed, wrong_review
            )

    def test_batch_length_mismatch_raises(self):
        approved = create_human_review(
            self.candidate, self.passed, decision="approved"
        )

        with self.assertRaisesRegex(ValueError, "quality results"):
            build_write_ready_preview_items([self.candidate], [], [approved])
        with self.assertRaisesRegex(ValueError, "human reviews"):
            build_write_ready_preview_items([self.candidate], [self.passed], [])

    def test_batch_filters_and_preserves_candidate_order(self):
        first = self._candidate("cc_selection_1_0", "第一题")
        second = self._candidate("cc_selection_2_0", "第二题")
        third = self._candidate("cc_selection_3_0", "第三题")
        qualities = [
            QualityGateResult(first.candidate_id, []),
            QualityGateResult(second.candidate_id, []),
            QualityGateResult(third.candidate_id, []),
        ]
        reviews = [
            create_human_review(first, qualities[0], decision="approved"),
            create_human_review(second, qualities[1]),
            create_human_review(third, qualities[2], decision="approved"),
        ]

        items = build_write_ready_preview_items(
            [first, second, third], qualities, reviews
        )

        self.assertEqual(
            [item.candidate_id for item in items],
            [first.candidate_id, third.candidate_id],
        )

    def test_missing_batch_state_returns_no_write_ready_items(self):
        self.assertEqual(build_write_ready_preview_items([self.candidate]), [])

    def test_chinese_content_is_preserved_and_tags_are_isolated(self):
        approved = create_human_review(
            self.candidate, self.warning, decision="approved"
        )
        item = build_write_ready_preview_item(
            self.candidate, self.warning, approved
        )

        self.assertEqual(item.front, "什么是过拟合？")
        self.assertEqual(item.back, "模型过度拟合训练数据。")
        self.assertEqual(item.extra, "注意训练误差与泛化误差。")
        self.assertEqual(item.tags, ("机器学习", "模型评估"))
        self.assertEqual(item.source, "学习笔记.md > 过拟合")
        self.assertEqual(item.source_display, "学习笔记.md > 过拟合")

        self.candidate.tags.append("后来添加")
        self.assertEqual(item.tags, ("机器学习", "模型评估"))
        with self.assertRaises(FrozenInstanceError):
            item.front = "被修改"

    def test_helpers_do_not_modify_inputs(self):
        approved = create_human_review(
            self.candidate, self.warning, decision="approved"
        )
        before = copy.deepcopy((self.candidate, self.warning, approved))

        build_pipeline_write_eligibility(
            self.candidate, self.warning, approved
        )
        build_write_ready_preview_item(
            self.candidate, self.warning, approved
        )

        self.assertEqual((self.candidate, self.warning, approved), before)

    def test_eligibility_is_frozen(self):
        eligibility = build_pipeline_write_eligibility(self.candidate)

        self.assertIsInstance(eligibility, PipelineWriteEligibility)
        with self.assertRaises(FrozenInstanceError):
            eligibility.eligible = True

    def test_module_has_no_forbidden_runtime_imports(self):
        module_path = (
            Path(__file__).parents[1]
            / "ankiforge_ai"
            / "pipeline"
            / "controlled_write_bridge.py"
        )
        source = module_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_modules = {
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        imported_modules.update(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )

        forbidden = ("aqt", "PyQt", "PyQt6", "provider", "config")
        self.assertFalse(
            any(
                module.startswith(prefix)
                for module in imported_modules
                for prefix in forbidden
            )
        )
        self.assertNotIn("GeneratedCard", source)

    @staticmethod
    def _candidate(candidate_id, front):
        return CardCandidate(
            candidate_id=candidate_id,
            selection_id=f"selection_{candidate_id}",
            point_id=f"point_{candidate_id}",
            document_id="document_1",
            chunk_id="chunk_1",
            source_display="学习笔记.md > 过拟合",
            heading_path=["机器学习", "过拟合"],
            ordinal=0,
            card_type="basic",
            front=front,
            back="模型过度拟合训练数据。",
            extra="注意训练误差与泛化误差。",
            tags=["机器学习", "模型评估"],
            source="学习笔记.md > 过拟合",
        )


if __name__ == "__main__":
    unittest.main()
