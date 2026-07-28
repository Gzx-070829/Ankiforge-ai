import unittest
from collections.abc import Mapping

from ankiforge_ai.intelligence.generation_run import (
    GenerationStage,
    create_generation_run,
    start_chunk,
    succeed_chunk,
    transition_run,
)
from ankiforge_ai.intelligence.critic import (
    CriticAction,
    CriticDecision,
    decide_card,
    repair_and_revalidate,
)
from ankiforge_ai.intelligence.models import IntelligenceLevel


class CriticRepairV014Tests(unittest.TestCase):
    def repairing_run(self):
        run = create_generation_run(
            run_id="run-repair",
            request_id=1,
            document_id="doc-repair",
            document_hash="d" * 64,
            document_snapshot={"material": "ATP carries cellular energy."},
            settings_snapshot={"card_mode": "concept"},
            level=IntelligenceLevel.DEEP,
            chunk_ids=("chunk-0000000000000001",),
        )
        run = transition_run(run, GenerationStage.PLANNING)
        run = transition_run(run, GenerationStage.GENERATING)
        chunk_id = run.chunks[0].chunk_id
        run = succeed_chunk(start_chunk(run, chunk_id), chunk_id, ())
        run = transition_run(run, GenerationStage.REVIEWING)
        return transition_run(run, GenerationStage.REPAIRING)

    def test_model_pass_cannot_waive_empty_or_ungrounded_local_block(self):
        empty = decide_card(
            card={"candidate_id": "card-1", "front": "", "back": ""},
            source_text="ATP is the immediate energy carrier in cells.",
            model_decision={"action": "pass", "reasoning": "private output"},
        )
        ungrounded = decide_card(
            card={
                "candidate_id": "card-2",
                "front": "Which planet is closest to the Sun?",
                "back": "Mercury is closest to the Sun.",
            },
            source_text="ATP is the immediate energy carrier in cells.",
            model_decision=CriticDecision(CriticAction.PASS),
        )

        self.assertEqual(empty.action, CriticAction.REPAIR)
        self.assertIn("empty_front", empty.reason_codes)
        self.assertEqual(ungrounded.action, CriticAction.REPAIR)
        self.assertIn("source_not_grounded", ungrounded.reason_codes)
        self.assertTrue(ungrounded.local_blocking)
        self.assertNotIn("private output", repr(empty))

    def test_first_local_failure_requests_repair_and_second_rejects(self):
        card = {
            "candidate_id": "card-1",
            "front": "What is ATP?",
            "back": "Mercury is a planet.",
        }
        source = "ATP is the immediate energy carrier in cells."

        first = decide_card(card=card, source_text=source)
        second = decide_card(
            card=card,
            source_text=source,
            repair_attempted=True,
        )

        self.assertEqual(first.action, CriticAction.REPAIR)
        self.assertEqual(second.action, CriticAction.REJECT)
        self.assertEqual(second.reason_codes[-1], "repair_failed_local_validation")

    def test_repair_is_called_once_then_revalidated_against_source(self):
        calls = []

        def repair(card, source_text):
            calls.append((card["candidate_id"], len(source_text)))
            return {
                "candidate_id": card["candidate_id"],
                "front": "What role does ATP have in cells?",
                "back": "ATP is the immediate energy carrier in cells.",
            }

        result = repair_and_revalidate(
            run=self.repairing_run(),
            point_id="point-0000000000000001",
            card={
                "candidate_id": "card-1",
                "front": "What role does ATP have in cells?",
                "back": "Mercury is a planet.",
            },
            source_text="ATP is the immediate energy carrier in cells.",
            repair_callback=repair,
        )

        self.assertEqual(calls, [("card-1", 45)])
        self.assertEqual(result.run.call_budget.call_count, 1)
        self.assertEqual(
            result.run.repaired_point_ids,
            ("point-0000000000000001",),
        )
        self.assertTrue(result.accepted)
        self.assertEqual(result.decision.action, CriticAction.PASS)
        self.assertEqual(result.card["candidate_id"], "card-1")

    def test_repair_with_unsupported_claim_is_rejected_after_one_attempt(self):
        calls = []

        def bad_repair(_card, _source_text):
            calls.append("called")
            return {
                "candidate_id": "card-1",
                "front": "Which planet is closest to the Sun?",
                "back": "Mercury is closest to the Sun.",
            }

        result = repair_and_revalidate(
            run=self.repairing_run(),
            point_id="point-0000000000000001",
            card={
                "candidate_id": "card-1",
                "front": "What role does ATP have?",
                "back": "Mercury is a planet.",
            },
            source_text="ATP is the immediate energy carrier in cells.",
            repair_callback=bad_repair,
        )

        self.assertEqual(calls, ["called"])
        self.assertFalse(result.accepted)
        self.assertEqual(result.decision.action, CriticAction.REJECT)
        self.assertIn("source_not_grounded", result.decision.reason_codes)
        self.assertNotIn("Mercury", repr(result))

    def test_repair_callback_exception_remains_billed_and_cannot_retry_point(self):
        calls = []
        secret = "C:\\Users\\private\\provider-output"

        def failing_repair(_card, _source_text):
            calls.append("called")
            raise RuntimeError(secret)

        result = repair_and_revalidate(
            run=self.repairing_run(),
            point_id="point-0000000000000001",
            card={
                "candidate_id": "card-1",
                "front": "What role does ATP have?",
                "back": "Mercury is a planet.",
            },
            source_text="ATP is the immediate energy carrier in cells.",
            repair_callback=failing_repair,
        )

        self.assertEqual(calls, ["called"])
        self.assertEqual(result.run.call_budget.call_count, 1)
        self.assertEqual(result.decision.reason_codes, ("repair_callback_failed",))
        self.assertNotIn(secret, repr(result))
        with self.assertRaisesRegex(ValueError, "repair_already_used"):
            repair_and_revalidate(
                run=result.run,
                point_id="point-0000000000000001",
                card=result.card,
                source_text="ATP is the immediate energy carrier in cells.",
                repair_callback=failing_repair,
            )
        self.assertEqual(calls, ["called"])

    def test_hostile_repaired_mapping_is_safely_rejected_after_billing(self):
        secret = "C:\\Users\\private\\hostile-repaired-output"

        class HostileRepairedMapping(Mapping):
            def __init__(self):
                self._values = {
                    "candidate_id": "card-1",
                    "front": "What role does ATP have in cells?",
                    "back": "ATP is the immediate energy carrier in cells.",
                }

            def __getitem__(self, key):
                return self._values[key]

            def __iter__(self):
                return iter(self._values)

            def __len__(self):
                return len(self._values)

            def items(self):
                raise RuntimeError(secret)

        original = {
            "candidate_id": "card-1",
            "front": "What role does ATP have?",
            "back": "Mercury is a planet.",
        }
        result = repair_and_revalidate(
            run=self.repairing_run(),
            point_id="point-0000000000000001",
            card=original,
            source_text="ATP is the immediate energy carrier in cells.",
            repair_callback=lambda _card, _source: HostileRepairedMapping(),
        )

        self.assertEqual(result.run.call_budget.call_count, 1)
        self.assertEqual(result.card, original)
        self.assertEqual(result.decision.action, CriticAction.REJECT)
        self.assertEqual(result.decision.reason_codes, ("repair_output_invalid",))
        self.assertNotIn(secret, repr(result))

    def test_model_reasoning_is_discarded_and_reason_codes_are_allowlisted(self):
        secret = "C:\\Users\\private\\material.txt"
        decision = decide_card(
            card={
                "candidate_id": "card-1",
                "front": "What role does ATP have in cells?",
                "back": "ATP is the immediate energy carrier in cells.",
            },
            source_text="ATP is the immediate energy carrier in cells.",
            model_decision={
                "action": "flag",
                "reason_codes": ["critic_style_flag", secret, "UPPER"],
                "reasoning": secret,
            },
        )

        self.assertEqual(decision.action, CriticAction.FLAG)
        self.assertEqual(decision.reason_codes, ("critic_style_flag",))
        self.assertNotIn(secret, repr(decision))

    def test_invalid_model_action_fails_closed_without_echoing_output(self):
        secret = "private-model-output"

        decision = decide_card(
            card={
                "candidate_id": "card-1",
                "front": "What role does ATP have in cells?",
                "back": "ATP is the immediate energy carrier in cells.",
            },
            source_text="ATP is the immediate energy carrier in cells.",
            model_decision={"action": secret, "reasoning": secret},
        )

        self.assertEqual(decision.action, CriticAction.FLAG)
        self.assertEqual(decision.reason_codes, ("critic_output_invalid",))
        self.assertNotIn(secret, repr(decision))


if __name__ == "__main__":
    unittest.main()
