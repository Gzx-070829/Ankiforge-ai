import unittest

from ankiforge_ai.document import BlockKind, DocumentBlock, DocumentIR, DocumentSection
from ankiforge_ai.intelligence import analyze_document, route_template
from ankiforge_ai.pipeline.generation_settings import (
    GenerationSettings,
    selectable_card_mode_profiles,
)


def _single_block_document(kind, text):
    return DocumentIR(
        schema_version=1,
        document_id="doc-route",
        title="Routing fixture",
        language_hint="en",
        source_type="text",
        source_label="route.txt",
        sections=(
            DocumentSection(
                section_id="route-section",
                heading="Topic",
                heading_path=("Topic",),
                blocks=(DocumentBlock("route-block", kind, text),),
            ),
        ),
        original_char_count=len(text),
        extracted_char_count=len(text),
    )


class TemplateRouterV014Tests(unittest.TestCase):
    def test_auto_uses_code_evidence_and_returns_reason_and_constraints(self):
        analysis = analyze_document(
            _single_block_document(
                BlockKind.CODE,
                "def total(values):\n    return sum(values)",
            )
        )

        route = route_template(analysis, requested_mode="auto")

        self.assertEqual(route.mode_id, "code_understanding")
        self.assertEqual(route.template_id, "concept")
        self.assertEqual(route.reason_code, "auto.code")
        self.assertGreaterEqual(route.confidence, 0.8)
        self.assertEqual(
            route.source_constraints,
            ("grounded_in_source_chunks", "preserve_code_context"),
        )
        self.assertFalse(route.overridden)

    def test_auto_prefers_point_evidence_over_document_wide_signal(self):
        analysis = analyze_document(
            _single_block_document(BlockKind.CODE, "answer = 6 * 7")
        )

        route = route_template(
            analysis,
            requested_mode="auto",
            point_type="formula",
            block_kinds=(BlockKind.FORMULA,),
        )

        self.assertEqual(route.mode_id, "formula_rule")
        self.assertEqual(route.template_id, "formula_rule")
        self.assertEqual(route.reason_code, "auto.formula")
        self.assertEqual(
            route.source_constraints,
            ("grounded_in_source_chunks", "preserve_formula_and_conditions"),
        )

    def test_explicit_selectable_mode_overrides_auto(self):
        analysis = analyze_document(
            _single_block_document(BlockKind.CODE, "def parse():\n    pass")
        )

        route = route_template(analysis, requested_mode="definition")

        self.assertEqual(route.mode_id, "definition")
        self.assertEqual(route.template_id, "definition")
        self.assertEqual(route.confidence, 1.0)
        self.assertEqual(route.reason_code, "explicit_mode")
        self.assertTrue(route.overridden)

    def test_public_modes_expand_without_changing_defaults_or_exposing_cloze(self):
        selectable = tuple(
            profile.mode_id for profile in selectable_card_mode_profiles()
        )

        self.assertEqual(GenerationSettings(), GenerationSettings(
            card_mode="concept",
            card_count="balanced",
            answer_length="short",
            language="auto",
        ))
        for mode in (
            "auto",
            "code_understanding",
            "table_relationship",
            "transcript_summary_candidate",
        ):
            self.assertIn(mode, selectable)
            self.assertEqual(GenerationSettings(card_mode=mode).card_mode, mode)
        self.assertNotIn("cloze_candidate", selectable)

    def test_cloze_and_unknown_modes_fail_closed(self):
        analysis = analyze_document(
            _single_block_document(BlockKind.PARAGRAPH, "A safe fact.")
        )

        for mode in ("cloze_candidate", "unknown"):
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(ValueError, "selectable"):
                    route_template(analysis, requested_mode=mode)

    def test_route_repr_does_not_contain_source_body(self):
        body = "confidential code-like source body"
        analysis = analyze_document(
            _single_block_document(BlockKind.CODE, body)
        )

        self.assertNotIn(body, repr(route_template(analysis)))

    def test_invalid_block_kind_error_does_not_echo_path_like_input(self):
        analysis = analyze_document(
            _single_block_document(BlockKind.PARAGRAPH, "A safe fact.")
        )
        path_like = "C:\\Users\\private\\source.txt"

        with self.assertRaisesRegex(ValueError, "known block kinds") as raised:
            route_template(
                analysis,
                requested_mode="auto",
                block_kinds=(path_like,),
            )

        self.assertNotIn(path_like, str(raised.exception))


if __name__ == "__main__":
    unittest.main()
