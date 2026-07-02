import ast
import json
import unittest
from pathlib import Path

from ankiforge_ai.pipeline.openai_compatible_provider import (
    OpenAICompatibleTransportResponse,
)
from ankiforge_ai.ui.beginner_ai_card_drafts import (
    BEGINNER_AI_EMPTY_CARDS_COPY,
    BEGINNER_AI_EMPTY_OUTPUT_COPY,
    BEGINNER_AI_INVALID_JSON_COPY,
    BEGINNER_AI_PROVIDER_ERROR_COPY,
    BEGINNER_AI_TIMEOUT_COPY,
    BeginnerAICardDraftGenerator,
    BeginnerAIDraftErrorCode,
    BeginnerAIProviderRuntimeSettings,
    parse_beginner_ai_card_drafts,
)
from ankiforge_ai.ui.beginner_flow_models import (
    COMPLETION_TITLE,
    BeginnerAICardDraft,
    BeginnerAIGenerationState,
    BeginnerArtifactState,
    BeginnerFlowSession,
)


class StubTransport:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.call_count = 0

    def post_json(self, url, headers, payload, timeout_seconds):
        self.call_count += 1
        if self.error is not None:
            raise self.error
        return self.response


class BeginnerAIRetryAndOutputRepairTests(unittest.TestCase):
    def test_generation_state_model_is_complete(self):
        self.assertEqual(
            {state.value for state in BeginnerAIGenerationState},
            {
                "idle",
                "running",
                "success",
                "provider_error",
                "timeout",
                "invalid_json",
                "empty_output",
                "empty_cards",
            },
        )

    def test_timeout_clears_old_candidates_and_enters_timeout_state(self):
        session = self.reviewed_session()
        session.begin_ai_candidate_generation()
        result = BeginnerAICardDraftGenerator(
            StubTransport(error=TimeoutError("private timeout detail"))
        ).generate(self.settings(), session.material_text)
        session.record_ai_card_draft_error(result.state, result.error_code.value)

        self.assertEqual(result.state, BeginnerAIGenerationState.TIMEOUT)
        self.assertEqual(result.error_code, BeginnerAIDraftErrorCode.TIMEOUT)
        self.assertEqual(result.user_message, BEGINNER_AI_TIMEOUT_COPY)
        self.assertEqual(session.ai_generation_state, BeginnerAIGenerationState.TIMEOUT)
        self.assert_no_old_review_or_candidates(session)

    def test_provider_error_is_safe_and_does_not_leak_api_key(self):
        secret = "secret-provider-key-never-display"
        result = BeginnerAICardDraftGenerator(
            StubTransport(error=RuntimeError(secret))
        ).generate(self.settings(secret), "交叉验证用于评估泛化表现。")
        rendered = " ".join(
            (
                repr(result),
                str(result),
                json.dumps(result.to_safe_dict(), ensure_ascii=False),
                result.user_message,
            )
        )

        self.assertEqual(result.state, BeginnerAIGenerationState.PROVIDER_ERROR)
        self.assertEqual(result.user_message, BEGINNER_AI_PROVIDER_ERROR_COPY)
        self.assertNotIn(secret, rendered)
        self.assertIn("检查 API key", result.user_message)

    def test_invalid_json_has_specific_state_and_no_drafts(self):
        result = parse_beginner_ai_card_drafts("这不是 JSON")

        self.assertEqual(result.state, BeginnerAIGenerationState.INVALID_JSON)
        self.assertEqual(result.drafts, ())
        self.assertEqual(result.user_message, BEGINNER_AI_INVALID_JSON_COPY)

    def test_markdown_code_fence_json_is_repaired(self):
        content = "```json\n" + self.cards_json() + "\n```"

        result = parse_beginner_ai_card_drafts(content)

        self.assertTrue(result.success)
        self.assertEqual(result.state, BeginnerAIGenerationState.SUCCESS)
        self.assertEqual(len(result.drafts), 1)

    def test_cards_object_json_is_repaired(self):
        payload = {"cards": json.loads(self.cards_json())}

        result = parse_beginner_ai_card_drafts(
            json.dumps(payload, ensure_ascii=False)
        )

        self.assertTrue(result.success)
        self.assertEqual(result.drafts[0].front, "什么是早停？")

    def test_explanatory_text_around_json_is_repaired_locally(self):
        content = "以下是结果：\n" + self.cards_json() + "\n请人工核对。"

        result = parse_beginner_ai_card_drafts(content)

        self.assertTrue(result.success)
        self.assertEqual(len(result.drafts), 1)

    def test_empty_provider_content_has_empty_output_state(self):
        response = OpenAICompatibleTransportResponse(
            status_code=200,
            json_body={"choices": [{"message": {"content": "  "}}]},
        )

        result = BeginnerAICardDraftGenerator(StubTransport(response)).generate(
            self.settings(),
            "早停会观察验证集表现。",
        )

        self.assertEqual(result.state, BeginnerAIGenerationState.EMPTY_OUTPUT)
        self.assertEqual(result.error_code, BeginnerAIDraftErrorCode.EMPTY_OUTPUT)
        self.assertEqual(result.user_message, BEGINNER_AI_EMPTY_OUTPUT_COPY)

    def test_empty_array_has_empty_cards_state(self):
        result = parse_beginner_ai_card_drafts("[]")

        self.assertEqual(result.state, BeginnerAIGenerationState.EMPTY_CARDS)
        self.assertEqual(result.error_code, BeginnerAIDraftErrorCode.NO_CARDS)
        self.assertEqual(result.user_message, BEGINNER_AI_EMPTY_CARDS_COPY)

    def test_missing_card_fields_are_invalid_json_state(self):
        result = parse_beginner_ai_card_drafts('[{"front":"只有正面"}]')

        self.assertEqual(result.state, BeginnerAIGenerationState.INVALID_JSON)
        self.assertEqual(result.drafts, ())

    def test_material_change_clears_old_error_review_and_downstream(self):
        session = self.reviewed_session()
        session.begin_ai_candidate_generation()
        session.record_ai_card_draft_error(
            BeginnerAIGenerationState.PROVIDER_ERROR,
            BeginnerAIDraftErrorCode.REQUEST_FAILED.value,
        )

        session.update_material("新材料会清除旧状态。")

        self.assertEqual(session.ai_generation_state, BeginnerAIGenerationState.IDLE)
        self.assertIsNone(session.ai_draft_error_code)
        self.assert_no_old_review_or_candidates(session)
        self.assert_prewrite_cleared(session)

    def test_runtime_setting_change_clears_old_error_and_downstream(self):
        session = self.reviewed_session()
        session.begin_ai_candidate_generation()
        session.record_ai_card_draft_error(
            BeginnerAIGenerationState.INVALID_JSON,
            BeginnerAIDraftErrorCode.MALFORMED_RESPONSE.value,
        )

        session.mark_ai_runtime_settings_changed()

        self.assertEqual(session.ai_generation_state, BeginnerAIGenerationState.IDLE)
        self.assertIsNone(session.ai_draft_error_code)
        self.assert_no_old_review_or_candidates(session)
        self.assert_prewrite_cleared(session)

    def test_regeneration_replaces_old_candidates_and_review(self):
        session = self.reviewed_session()
        old_front = session.candidate_card_previews[0].front_preview
        session.begin_ai_candidate_generation()
        replacement = BeginnerAICardDraft(
            id="replacement",
            front="交叉验证有什么作用？",
            back="用于估计模型面对新数据时的表现。",
            source_excerpt="交叉验证帮助评估模型在新数据上的表现",
        )

        session.apply_ai_candidate_card_drafts((replacement,))

        self.assertEqual(session.ai_generation_state, BeginnerAIGenerationState.SUCCESS)
        self.assertEqual(len(session.candidate_card_previews), 1)
        self.assertNotEqual(session.candidate_card_previews[0].front_preview, old_front)
        self.assertEqual(session.candidate_review_decisions, {})
        self.assert_prewrite_cleared(session)

    def test_ui_has_running_state_retry_and_clear_before_provider_call(self):
        source = self.dialog_source()
        handler = self.function_source(source, "_generate_ai_candidate_drafts")

        self.assertIn('QPushButton("重新生成")', source)
        self.assertIn("BEGINNER_AI_GENERATING_COPY", handler)
        self.assertLess(
            handler.index("self.session.begin_ai_candidate_generation()"),
            handler.index("BeginnerAICardDraftGenerator().generate"),
        )
        self.assertIn("result.state", handler)

    def test_all_error_copy_states_no_write_and_no_collection_access(self):
        for copy in (
            BEGINNER_AI_PROVIDER_ERROR_COPY,
            BEGINNER_AI_TIMEOUT_COPY,
            BEGINNER_AI_INVALID_JSON_COPY,
            BEGINNER_AI_EMPTY_OUTPUT_COPY,
            BEGINNER_AI_EMPTY_CARDS_COPY,
        ):
            self.assertIn("没有写入 Anki", copy)
            self.assertIn("没有访问 Anki collection", copy)

    def test_no_formal_card_output_and_completion_copy_is_unchanged(self):
        imported_names = self.imported_names(self.generator_source())
        imported_names |= self.imported_names(self.model_source())

        self.assertNotIn("GeneratedCard", imported_names)
        self.assertNotIn("WriteReadyPreviewItem", imported_names)
        self.assertEqual(COMPLETION_TITLE, "演练完成，尚未写入 Anki")

    @staticmethod
    def settings(secret="temporary-session-key"):
        return BeginnerAIProviderRuntimeSettings(
            provider_name="OpenAI-compatible",
            base_url="https://provider.invalid/v1",
            model="test-model",
            api_key=secret,
            timeout_seconds=10,
        )

    @staticmethod
    def draft():
        return BeginnerAICardDraft(
            id="old-draft",
            front="早停如何工作？",
            back="验证表现不再改善时停止训练。",
            source_excerpt="早停会观察验证集表现",
        )

    def reviewed_session(self):
        session = BeginnerFlowSession()
        session.update_material("早停会观察验证集表现。")
        session.apply_ai_candidate_card_drafts((self.draft(),))
        candidate_id = session.candidate_card_previews[0].id
        session.set_candidate_review_decision(candidate_id, "looks_good")
        session.eligibility_state = BeginnerArtifactState.CURRENT
        session.write_plan_preview_state = BeginnerArtifactState.CURRENT
        session.final_confirmation_preview_state = BeginnerArtifactState.CURRENT
        return session

    @staticmethod
    def cards_json():
        return json.dumps(
            [
                {
                    "front": "什么是早停？",
                    "back": "验证表现不再改善时提前停止训练。",
                    "source_excerpt": "早停会观察验证集表现",
                }
            ],
            ensure_ascii=False,
        )

    def assert_no_old_review_or_candidates(self, session):
        self.assertEqual(session.ai_candidate_card_drafts, ())
        self.assertEqual(session.candidate_card_previews, ())
        self.assertEqual(session.candidate_review_decisions, {})

    def assert_prewrite_cleared(self, session):
        self.assertEqual(session.eligibility_state, BeginnerArtifactState.CLEARED)
        self.assertEqual(
            session.write_plan_preview_state,
            BeginnerArtifactState.CLEARED,
        )
        self.assertEqual(
            session.final_confirmation_preview_state,
            BeginnerArtifactState.CLEARED,
        )

    @staticmethod
    def imported_names(source):
        tree = ast.parse(source)
        return {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }

    @staticmethod
    def function_source(source, name):
        tree = ast.parse(source)
        node = next(
            item
            for item in ast.walk(tree)
            if isinstance(item, ast.FunctionDef) and item.name == name
        )
        return ast.unparse(node)

    @staticmethod
    def repo_root():
        return Path(__file__).parents[1]

    def dialog_source(self):
        return (
            self.repo_root() / "ankiforge_ai" / "ui" / "beginner_mode_dialog.py"
        ).read_text(encoding="utf-8")

    def generator_source(self):
        return (
            self.repo_root()
            / "ankiforge_ai"
            / "ui"
            / "beginner_ai_card_drafts.py"
        ).read_text(encoding="utf-8")

    def model_source(self):
        return (
            self.repo_root() / "ankiforge_ai" / "ui" / "beginner_flow_models.py"
        ).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
