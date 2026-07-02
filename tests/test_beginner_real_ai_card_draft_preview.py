import ast
import json
import unittest
from pathlib import Path

from ankiforge_ai.pipeline.openai_compatible_provider import (
    OpenAICompatibleTransportResponse,
)
from ankiforge_ai.ui.beginner_ai_card_drafts import (
    BEGINNER_AI_PROVIDER_DISCLOSURE_COPY,
    BEGINNER_AI_INVALID_JSON_COPY,
    BeginnerAICardDraftGenerator,
    BeginnerAIDraftErrorCode,
    BeginnerAIProviderRuntimeSettings,
    parse_beginner_ai_card_drafts,
)
from ankiforge_ai.ui.beginner_flow_models import (
    COMPLETION_TITLE,
    BeginnerAICardDraft,
    BeginnerArtifactState,
    BeginnerFlowSession,
    BeginnerFlowStep,
)


class FakeTransport:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def post_json(self, url, headers, payload, timeout_seconds):
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "payload": payload,
                "timeout_seconds": timeout_seconds,
            }
        )
        if self.error is not None:
            raise self.error
        return self.response


class BeginnerRealAICardDraftPreviewTests(unittest.TestCase):
    def test_api_key_is_session_only_and_absent_from_safe_views(self):
        secret = "session-secret-that-must-not-leak"
        settings = self.settings(secret)
        session = BeginnerFlowSession()

        rendered = " ".join(
            (
                repr(settings),
                str(settings),
                json.dumps(settings.to_safe_dict(), ensure_ascii=False),
                repr(session),
                str(session),
                json.dumps(session.to_safe_dict(), ensure_ascii=False),
            )
        )

        self.assertNotIn(secret, rendered)
        self.assertNotIn("api_key", BeginnerFlowSession.public_field_names())
        self.assertNotIn("api_key", settings.to_safe_dict())
        self.assertTrue(settings.to_safe_dict()["credential_supplied"])

    def test_constructing_session_and_generator_does_not_call_transport(self):
        transport = FakeTransport()

        session = BeginnerFlowSession()
        generator = BeginnerAICardDraftGenerator(transport=transport)

        self.assertIsInstance(session, BeginnerFlowSession)
        self.assertIsInstance(generator, BeginnerAICardDraftGenerator)
        self.assertEqual(transport.calls, [])

    def test_network_transport_runs_only_when_generate_is_called(self):
        transport = FakeTransport(response=self.valid_response())
        generator = BeginnerAICardDraftGenerator(transport=transport)
        self.assertEqual(transport.calls, [])

        result = generator.generate(self.settings(), "过拟合会降低泛化能力。")

        self.assertTrue(result.success)
        self.assertEqual(len(transport.calls), 1)
        call = transport.calls[0]
        self.assertTrue(call["url"].endswith("/chat/completions"))
        self.assertEqual(call["payload"]["model"], "test-model")
        self.assertIn("Bearer ", call["headers"]["Authorization"])

    def test_json_array_and_cards_object_parse_to_read_only_drafts(self):
        cards = [
            {
                "front": "什么是过拟合？",
                "back": "模型过度贴合训练数据，导致泛化表现下降。",
                "source_excerpt": "过拟合会降低泛化能力",
            }
        ]

        array_result = parse_beginner_ai_card_drafts(
            json.dumps(cards, ensure_ascii=False)
        )
        object_result = parse_beginner_ai_card_drafts(
            json.dumps({"cards": cards}, ensure_ascii=False)
        )

        for result in (array_result, object_result):
            self.assertTrue(result.success)
            self.assertEqual(len(result.drafts), 1)
            self.assertIsInstance(result.drafts[0], BeginnerAICardDraft)
            self.assertEqual(result.drafts[0].front, "什么是过拟合？")

    def test_invalid_json_becomes_safe_non_writing_error(self):
        result = parse_beginner_ai_card_drafts("not-json")

        self.assertFalse(result.success)
        self.assertEqual(
            result.error_code,
            BeginnerAIDraftErrorCode.MALFORMED_RESPONSE,
        )
        self.assertEqual(result.user_message, BEGINNER_AI_INVALID_JSON_COPY)
        self.assertIn("没有写入 Anki", result.user_message)

    def test_provider_exception_does_not_leak_api_key_or_raw_exception(self):
        secret = "do-not-show-this-api-key"
        transport = FakeTransport(error=RuntimeError(secret))

        result = BeginnerAICardDraftGenerator(transport).generate(
            self.settings(secret),
            "交叉验证帮助评估模型泛化表现。",
        )
        rendered = " ".join(
            (
                repr(result),
                str(result),
                json.dumps(result.to_safe_dict(), ensure_ascii=False),
            )
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error_code, BeginnerAIDraftErrorCode.REQUEST_FAILED)
        self.assertNotIn(secret, rendered)
        self.assertNotIn("RuntimeError", rendered)

    def test_material_change_clears_ai_drafts_review_and_downstream(self):
        session = self.ai_draft_session()

        session.update_material("新的材料会让旧草稿失效。")

        self.assertEqual(session.ai_candidate_card_drafts, ())
        self.assertEqual(session.candidate_card_previews, ())
        self.assertEqual(session.candidate_review_decisions, {})
        self.assertEqual(session.ai_draft_state, BeginnerArtifactState.CLEARED)
        self.assert_prewrite_cleared(session)
        self.assertEqual(session.last_clearing_reason, "material_changed")

    def test_runtime_setting_change_clears_ai_drafts_and_review(self):
        session = self.ai_draft_session()

        session.mark_ai_runtime_settings_changed()

        self.assertEqual(session.ai_candidate_card_drafts, ())
        self.assertEqual(session.candidate_card_previews, ())
        self.assertEqual(session.candidate_review_decisions, {})
        self.assertEqual(session.ai_draft_state, BeginnerArtifactState.CLEARED)
        self.assert_prewrite_cleared(session)
        self.assertEqual(
            session.last_clearing_reason,
            "ai_runtime_settings_changed",
        )

    def test_close_discards_material_ai_drafts_and_review(self):
        session = self.ai_draft_session()

        session.close()

        self.assertEqual(session.material_text, "")
        self.assertEqual(session.ai_candidate_card_drafts, ())
        self.assertEqual(session.candidate_card_previews, ())
        self.assertEqual(session.candidate_review_decisions, {})
        self.assertEqual(session.ai_draft_state, BeginnerArtifactState.EMPTY)

    def test_ai_drafts_feed_step_four_without_formal_write_models(self):
        session = BeginnerFlowSession()
        session.update_material("早停可以降低过拟合风险。")
        draft = self.draft()

        session.apply_ai_candidate_card_drafts((draft,))

        self.assertEqual(session.current_step, BeginnerFlowStep.REVIEW_CANDIDATE_CARDS)
        self.assertEqual(session.candidate_origin, "real_ai_draft")
        self.assertEqual(session.candidate_card_previews[0].front_preview, draft.front)
        self.assertFalse(session.anki_collection_access_allowed)
        self.assertFalse(session.duplicate_check_allowed)
        self.assertFalse(session.anki_write_allowed)

        imported_names = self.imported_names(self.model_source()) | self.imported_names(
            self.generator_source()
        )
        self.assertNotIn("GeneratedCard", imported_names)
        self.assertNotIn("WriteReadyPreviewItem", imported_names)

    def test_dialog_discloses_network_and_calls_generator_only_in_click_handler(self):
        source = self.dialog_source()
        init_source = self.function_source(source, "__init__")
        handler_source = self.function_source(
            source,
            "_generate_ai_candidate_drafts",
        )

        self.assertIn("用 AI 生成候选卡", init_source)
        self.assertIn("本次会话 API key", init_source)
        self.assertIn("本次会联网", init_source)
        self.assertNotIn("BeginnerAICardDraftGenerator()", init_source)
        self.assertNotIn(".generate(", init_source)
        self.assertIn("BeginnerAICardDraftGenerator().generate", handler_source)
        self.assertIn("self.session.material_text", handler_source)
        self.assertIn("self.session.apply_ai_candidate_card_drafts", handler_source)
        self.assertIn("self.ai_api_key_input.clear()", source)

    def test_disclosure_and_completion_copy_remain_explicit(self):
        self.assertIn("发送给所选 AI Provider", BEGINNER_AI_PROVIDER_DISCLOSURE_COPY)
        self.assertIn("本次请求会联网", BEGINNER_AI_PROVIDER_DISCLOSURE_COPY)
        self.assertIn("API key 只用于当前窗口", BEGINNER_AI_PROVIDER_DISCLOSURE_COPY)
        self.assertIn("不会保存", BEGINNER_AI_PROVIDER_DISCLOSURE_COPY)
        self.assertIn("不会写入 Anki", BEGINNER_AI_PROVIDER_DISCLOSURE_COPY)
        self.assertEqual(COMPLETION_TITLE, "演练完成，尚未写入 Anki")

    @staticmethod
    def settings(secret="temporary-test-key"):
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
            id="ai-draft-1",
            front="早停如何帮助降低过拟合？",
            back="当验证表现不再改善时提前停止训练。",
            source_excerpt="早停可以降低过拟合风险",
        )

    def ai_draft_session(self):
        session = BeginnerFlowSession()
        session.update_material("早停可以降低过拟合风险。")
        session.apply_ai_candidate_card_drafts((self.draft(),))
        candidate_id = session.candidate_card_previews[0].id
        session.set_candidate_review_decision(candidate_id, "looks_good")
        session.eligibility_state = BeginnerArtifactState.CURRENT
        session.write_plan_preview_state = BeginnerArtifactState.CURRENT
        session.final_confirmation_preview_state = BeginnerArtifactState.CURRENT
        return session

    @staticmethod
    def valid_response():
        content = json.dumps(
            {
                "cards": [
                    {
                        "front": "什么是过拟合？",
                        "back": "模型过度贴合训练数据。",
                        "source_excerpt": "过拟合会降低泛化能力",
                    }
                ]
            },
            ensure_ascii=False,
        )
        return OpenAICompatibleTransportResponse(
            status_code=200,
            json_body={"choices": [{"message": {"content": content}}]},
        )

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
        function = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == name
        )
        return ast.unparse(function)

    @staticmethod
    def repo_root():
        return Path(__file__).parents[1]

    def dialog_source(self):
        return (
            self.repo_root() / "ankiforge_ai" / "ui" / "beginner_mode_dialog.py"
        ).read_text(encoding="utf-8")

    def model_source(self):
        return (
            self.repo_root() / "ankiforge_ai" / "ui" / "beginner_flow_models.py"
        ).read_text(encoding="utf-8")

    def generator_source(self):
        return (
            self.repo_root()
            / "ankiforge_ai"
            / "ui"
            / "beginner_ai_card_drafts.py"
        ).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
