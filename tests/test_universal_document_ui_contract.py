import ast
import json
import unittest
from dataclasses import replace
from pathlib import Path

from ankiforge_ai.document import SourceLocation, create_native_importer_registry
from ankiforge_ai.intelligence import (
    CallPurpose,
    GenerationStage,
    IntelligenceLevel,
    KnowledgePlan,
    KnowledgePointPlan,
    build_local_knowledge_plan,
    create_generation_run,
    estimate_generation,
    reserve_run_call,
    start_chunk,
    succeed_chunk,
    transition_run,
)
from ankiforge_ai.pipeline.ai_generation_limits import MAX_AI_MATERIAL_CHARS
from ankiforge_ai.ui.beginner_ai_card_drafts import BeginnerAICardDraft
from ankiforge_ai.ui.beginner_flow_models import (
    BeginnerArtifactState,
    BeginnerFlowSession,
)
from ankiforge_ai.ui.document_intelligence_presenter import (
    present_batch_intelligence_estimate,
)
from ankiforge_ai.ui.intelligent_generation_task_controller import (
    IntelligentGenerationTaskController,
)
from ankiforge_ai.ui.product_i18n import PRODUCT_COPY
from ankiforge_ai.ui.universal_document_generation_adapter import (
    BoundedProviderGenerationAdapter,
    build_imported_generation_run,
)


class UniversalDocumentUIContractTests(unittest.TestCase):
    def test_picker_accepts_every_native_extension_and_uses_multi_select(self):
        source = self.panel_source()
        picker = self.function_source(source, "_choose_source_file")
        native_extensions = {
            extension
            for capability in create_native_importer_registry().capabilities()
            for extension in capability.supported_extensions
        }

        self.assertIn("QFileDialog.getOpenFileNames", picker)
        self.assertIn("self._enqueue_document_paths(paths)", picker)
        for language in ("zh", "en"):
            filter_copy = PRODUCT_COPY[language]["source_file_filter"]
            for extension in native_extensions:
                self.assertIn(f"*{extension}", filter_copy)

    def test_drop_enqueues_every_local_path_without_first_only_fallback(self):
        handler = self.function_source(
            self.panel_source(),
            "_handle_dropped_files",
        )

        self.assertIn("self._enqueue_document_paths(paths)", handler)
        self.assertNotIn("paths[0]", handler)
        self.assertNotIn("source_import_first_only", handler)
        self.assertNotIn("_generate_cards", handler)

    def test_create_surface_has_compact_queue_capabilities_and_explicit_retry(self):
        material = self.function_source(
            self.panel_source(),
            "_build_material_section",
        )
        queue_renderer = self.function_source(
            self.panel_source(),
            "_render_document_queue",
        )
        move_item = self.function_source(
            self.panel_source(),
            "_move_document_queue_item",
        )
        remove_item = self.function_source(
            self.panel_source(),
            "_remove_document_queue_item",
        )

        for member in (
            "document_queue_container",
            "document_capabilities_btn",
            "retry_failed_imports_btn",
        ):
            self.assertIn(f"self.{member}", material)
        self.assertIn("DocumentQueueRow", queue_renderer)
        self.assertIn("_remove_document_queue_item", queue_renderer)
        self.assertIn("_move_document_queue_item", queue_renderer)
        self.assertIn("remove_import_item", remove_item)
        self.assertIn("move_import_item", move_item)
        self.assertNotIn("_generate_cards", queue_renderer)

    def test_auto_mode_intelligence_selector_and_standard_default_are_visible(self):
        generation = self.function_source(
            self.panel_source(),
            "_build_generation_section",
        )

        self.assertIn("self.card_mode_combo", generation)
        self.assertIn("self.intelligence_level_combo", generation)
        self.assertIn("IntelligenceLevel.FAST", generation)
        self.assertIn("IntelligenceLevel.STANDARD", generation)
        self.assertIn("IntelligenceLevel.DEEP", generation)
        self.assertIn(
            "self.intelligence_level_combo.setCurrentIndex(1)",
            generation,
        )
        self.assertEqual(
            BeginnerFlowSession().intelligence_level,
            IntelligenceLevel.STANDARD,
        )

    def test_estimate_and_plan_detail_are_present_but_detail_defaults_collapsed(self):
        generation = self.function_source(
            self.panel_source(),
            "_build_generation_section",
        )

        self.assertIn("self.intelligence_estimate_label", generation)
        self.assertIn("self.plan_detail_btn", generation)
        self.assertIn("self.plan_detail_container.setVisible(False)", generation)
        self.assertIn("self.generation_settings_container.setVisible(False)", generation)

    def test_batch_estimate_keeps_bounded_policy_and_explicit_confirmation(self):
        worker_result = self.make_worker_result()
        standard = next(
            estimate
            for estimate in worker_result.estimates
            if estimate.level is IntelligenceLevel.STANDARD
        )
        deep = estimate_generation(
            worker_result.analysis,
            worker_result.chunks,
            level=IntelligenceLevel.DEEP,
        )

        standard_view = present_batch_intelligence_estimate(
            (standard, standard),
            language="en",
        )
        deep_view = present_batch_intelligence_estimate((deep,), language="en")

        self.assertEqual(
            standard_view.call_range,
            "4 planned · up to 8 calls",
        )
        self.assertEqual(
            deep_view.call_range,
            "5 planned · up to 12 calls",
        )
        self.assertTrue(standard_view.requires_confirmation)
        self.assertTrue(deep_view.requires_confirmation)
        self.assertIn("2 documents", standard_view.detail)
        self.assertNotIn("$", standard_view.detail)

    def test_standard_and_deep_confirmation_precedes_generation_submission(self):
        source = self.panel_source()
        generate = self.function_source(source, "_generate_cards")
        confirm = self.function_source(
            source,
            "_confirm_intelligence_generation",
        )

        self.assertIn("IntelligenceLevel.FAST", confirm)
        self.assertIn("QMessageBox.question", confirm)
        self.assertIn(
            "if has_document_results and not self._confirm_intelligence_generation",
            generate,
        )
        self.assertLess(
            generate.index(
                "if has_document_results and not "
                "self._confirm_intelligence_generation"
            ),
            generate.index("self._start_intelligent_generation"),
        )
        confirmation = self.function_source(
            source,
            "_confirm_intelligence_generation",
        )
        self.assertIn("estimate_view.confirmation_text", confirmation)

    def test_pasted_text_explicitly_uses_legacy_one_call_behavior(self):
        panel = self.panel_source()
        estimate = self.function_source(
            panel,
            "_update_intelligence_estimate",
        )
        generate = self.function_source(panel, "_generate_cards")

        self.assertIn("self.intelligence_level_combo.setEnabled(has_documents)", estimate)
        self.assertIn('"paste_generation_behavior"', estimate)
        self.assertIn("has_document_results", generate)
        self.assertIn(
            "if has_document_results and not self._confirm_intelligence_generation",
            generate,
        )
        self.assertLess(
            generate.index("if has_document_results"),
            generate.index("self._generation_controller.submit"),
        )

    def test_queue_mutations_share_one_visible_material_sync_path(self):
        panel = self.panel_source()
        sync = self.function_source(
            panel,
            "_sync_material_from_document_queue",
        )
        completion = self.function_source(
            panel,
            "_handle_document_import_completion",
        )
        move_item = self.function_source(
            panel,
            "_move_document_queue_item",
        )
        remove_item = self.function_source(
            panel,
            "_remove_document_queue_item",
        )
        manual_edit = self.function_source(panel, "_on_material_changed")

        self.assertIn("build_bounded_import_material", sync)
        self.assertIn("self.material_input.setPlainText(material)", sync)
        self.assertIn("self.session.update_material(material)", sync)
        self.assertIn("_sync_material_from_document_queue", completion)
        self.assertIn("_sync_material_from_document_queue", move_item)
        self.assertIn("_sync_material_from_document_queue", remove_item)
        self.assertIn("create_import_queue()", manual_edit)
        self.assertIn("self._document_queue_owns_material = False", manual_edit)

    def test_serial_imports_hard_gate_button_and_generate_handler(self):
        panel = self.panel_source()
        pending = self.function_source(panel, "_document_imports_pending")
        refresh = self.function_source(panel, "_refresh_product_state")
        generate = self.function_source(panel, "_generate_cards")

        self.assertIn("self._document_import_queue.imports_pending", pending)
        self.assertIn("self._pending_document_import_requests", pending)
        self.assertIn("self._document_import_controller.running", pending)
        self.assertIn("not self._document_imports_pending()", refresh)
        self.assertIn("if self._document_imports_pending()", generate)
        self.assertIn('"document_import_in_progress"', generate)
        self.assertLess(
            generate.index("if self._document_imports_pending()"),
            generate.index("_confirm_intelligence_generation"),
        )

    def test_manual_edit_always_switches_source_type_to_paste(self):
        manual_edit = self.function_source(
            self.panel_source(),
            "_on_material_changed",
        )

        self.assertIn(
            "self.session.set_source_type(SourceType.PASTE)",
            manual_edit,
        )
        self.assertNotIn(
            "if not self.session.material_text.strip() or not material_text.strip()",
            manual_edit,
        )

    def test_combined_complexity_preflight_precedes_paid_confirmation(self):
        panel = self.panel_source()
        generate = self.function_source(panel, "_generate_cards")
        prepare = self.function_source(
            panel,
            "_prepare_intelligent_generation_run",
        )

        self.assertIn("_prepare_intelligent_generation_run", generate)
        self.assertIn('"document_batch_too_complex"', prepare)
        self.assertLess(
            generate.index("_prepare_intelligent_generation_run"),
            generate.index("_confirm_intelligence_generation"),
        )
        self.assertNotIn("_controller.submit", prepare)

    def test_stage_progress_partial_retry_and_review_source_presenter_are_wired(self):
        panel = self.panel_source()
        create = self.function_source(panel, "_build_create_panel")
        completion = self.function_source(
            panel,
            "_handle_generation_completion",
        )
        cards = self.function_source(panel, "_render_cards")

        self.assertIn("generation_progress_label", create)
        self.assertIn('"document_run_in_progress"', panel)
        self.assertNotIn(
            "stage_label(GenerationStage.GENERATING",
            self.function_source(panel, "_generate_cards"),
        )
        self.assertIn("GenerationStage.COMPLETED", completion)
        self.assertIn("retry_failed_generation_btn", create)
        retry = self.function_source(
            panel,
            "_retry_failed_generation_chunks",
        )
        self.assertIn("self._intelligent_generation_controller.retry_failed", retry)
        self.assertIn("present_source_location", cards)
        self.assertIn("card.source_location", cards)
        self.assertIn("source_view.chip", cards)
        self.assertIn("source_view.snippet", cards)
        session = BeginnerFlowSession()
        location = SourceLocation(page=7)
        session.apply_ai_candidate_card_drafts(
            (
                BeginnerAICardDraft(
                    id="located",
                    front="Question",
                    back="Answer",
                    source_excerpt="Evidence",
                    source_location=location,
                ),
            )
        )
        self.assertIs(
            session.candidate_card_previews[0].source_location,
            location,
        )

    def test_panel_delegates_parsing_chunking_and_estimation_outside_qt_widget(self):
        panel = self.panel_source()

        self.assertIn("import_document_path_token", panel)
        self.assertIn("build_bounded_import_material", panel)
        for forbidden in (
            "detect_file_type(",
            ".import_document(",
            "analyze_document(",
            "chunk_document(",
            "build_local_knowledge_plan(",
            "estimate_generation(",
        ):
            self.assertNotIn(forbidden, panel)

    def test_fake_provider_runs_standard_planner_and_grouped_generation_end_to_end(self):
        result = self.make_worker_result()
        run = build_imported_generation_run(
            (result,),
            generation_settings=__import__(
                "ankiforge_ai.pipeline.generation_settings",
                fromlist=["GenerationSettings"],
            ).GenerationSettings(card_mode="auto"),
            level=IntelligenceLevel.STANDARD,
            request_id=1,
        )
        provider_calls = []

        class FakeProviderClient:
            def complete_json(self, **kwargs):
                provider_calls.append(
                    {
                        key: value
                        for key, value in kwargs.items()
                        if key != "runtime_settings"
                    }
                )
                purpose = kwargs["purpose"]
                if purpose == "planner":
                    return {
                        "point_ids": [
                            point.point_id for point in run.plan.points
                        ]
                    }
                if purpose == "generate":
                    import json

                    request = json.loads(kwargs["user_prompt"])
                    return {
                        "cards": [
                            {
                                "point_id": point["point_id"],
                                "front": f"What does {point['title']} mean?",
                                "back": point["evidence"][:500],
                                "source_excerpt": point["evidence"][:200],
                            }
                            for point in request["points"][
                                : request["max_cards"]
                            ]
                        ]
                    }
                raise AssertionError("unexpected provider purpose")

        fake_client = FakeProviderClient()

        adapter = BoundedProviderGenerationAdapter(
            runtime_settings=__import__(
                "ankiforge_ai.ui.beginner_ai_card_drafts",
                fromlist=["BeginnerAIProviderRuntimeSettings"],
            ).BeginnerAIProviderRuntimeSettings(
                provider_name="Fake",
                base_url="https://provider.invalid/v1",
                model="fake-model",
                api_key="sk-private-never-render",
            ),
            generation_settings=__import__(
                "ankiforge_ai.pipeline.generation_settings",
                fromlist=["GenerationSettings"],
            ).GenerationSettings(card_mode="auto"),
            endpoint_confirmation_key=None,
            provider_client_factory=lambda: fake_client,
        )

        class ImmediateTaskman:
            def run_in_background(
                self,
                task,
                on_done,
                *,
                uses_collection,
            ):
                from concurrent.futures import Future

                self.uses_collection = uses_collection
                future = Future()
                future.set_result(task())
                on_done(future)

        taskman = ImmediateTaskman()
        completions = []
        IntelligentGenerationTaskController(taskman).submit(
            run_snapshot=run,
            generator_callback=adapter,
            planner_callback=adapter.planner_callback,
            on_complete=completions.append,
        )

        self.assertFalse(taskman.uses_collection)
        self.assertEqual(
            [call["purpose"] for call in provider_calls],
            [
                "planner",
                *(
                    "generate"
                    for _batch in adapter.generation_batches(run)
                ),
            ],
        )
        self.assertEqual(completions[0].run.status.value, "completed")
        expected_calls = 1 + len(adapter.generation_batches(run))
        self.assertEqual(
            completions[0].run.call_budget.call_count,
            expected_calls,
        )
        self.assertEqual(
            [
                reservation.purpose.value
                for reservation in completions[0].run.call_budget.reservations
            ],
            [
                "planner",
                *(
                    "generate"
                    for _batch in adapter.generation_batches(run)
                ),
            ],
        )
        rendered = repr(adapter) + repr(completions[0])
        self.assertNotIn("sk-private", rendered)
        self.assertNotIn(str(Path(__file__).parent), rendered)

    def test_panel_wires_level_specific_provider_stages_without_dummy_calls(self):
        start = self.function_source(
            self.panel_source(),
            "_start_intelligent_generation",
        )

        self.assertIn("planner_callback=adapter.planner_callback", start)
        self.assertIn("critic_callback=adapter.critic_callback", start)
        self.assertIn("repair_callback=adapter.repair_callback", start)
        self.assertIn("supplement_callback=adapter.supplement_callback", start)

    def test_adapter_refuses_hidden_unreserved_batches_and_bounds_every_prompt(self):
        result = self.make_worker_result()
        settings = __import__(
            "ankiforge_ai.pipeline.generation_settings",
            fromlist=["GenerationSettings"],
        ).GenerationSettings(card_mode="auto")
        run = build_imported_generation_run(
            (result,),
            generation_settings=settings,
            level=IntelligenceLevel.FAST,
            request_id=1,
        )
        calls = []

        class RecordingClient:
            def complete_json(self, **kwargs):
                calls.append(kwargs)
                return {"cards": []}

        adapter = self.make_adapter(
            settings,
            provider_client_factory=RecordingClient,
        )

        with self.assertRaisesRegex(ValueError, "controller"):
            adapter(run)
        with self.assertRaisesRegex(ValueError, "material_too_long"):
            adapter._complete(
                purpose="generate",
                system_prompt="system",
                user_prompt="x" * MAX_AI_MATERIAL_CHARS,
            )
        self.assertEqual(calls, [])

    def test_retry_inside_original_multi_chunk_batch_has_a_bounded_card_quota(self):
        results = (
            self.make_worker_result(),
            self.make_worker_result("plain.txt"),
        )
        settings = __import__(
            "ankiforge_ai.pipeline.generation_settings",
            fromlist=["GenerationSettings"],
        ).GenerationSettings(card_mode="auto")
        run = build_imported_generation_run(
            results,
            generation_settings=settings,
            level=IntelligenceLevel.FAST,
            request_id=1,
        )
        adapter_calls = []

        class RetryClient:
            def complete_json(self, **kwargs):
                request = json.loads(kwargs["user_prompt"])
                adapter_calls.append(request["max_cards"])
                point = request["points"][0]
                return {
                    "cards": [
                        {
                            "point_id": point["point_id"],
                            "front": f"What is {point['title']}?",
                            "back": point["evidence"][:500],
                            "source_excerpt": point["evidence"][:200],
                        }
                    ]
                }

        adapter = self.make_adapter(
            settings,
            provider_client_factory=RetryClient,
        )
        original_batch = next(
            batch
            for batch in adapter.generation_batches(run)
            if len(batch) > 1
        )
        retry_run = transition_run(run, GenerationStage.PLANNING)
        retry_run = transition_run(retry_run, GenerationStage.GENERATING)
        retry_run = reserve_run_call(retry_run, CallPurpose.GENERATE)

        cards = adapter(retry_run, original_batch[-1])

        self.assertTrue(cards)
        self.assertEqual(len(adapter_calls), 1)
        self.assertGreaterEqual(adapter_calls[0], 1)

    def test_adapter_rejects_provider_cards_beyond_the_prompted_batch_quota(self):
        result = self.make_worker_result()
        settings = __import__(
            "ankiforge_ai.pipeline.generation_settings",
            fromlist=["GenerationSettings"],
        ).GenerationSettings(card_mode="auto", card_count="fewer")
        run = build_imported_generation_run(
            (result,),
            generation_settings=settings,
            level=IntelligenceLevel.FAST,
            request_id=1,
        )

        class OverQuotaClient:
            def complete_json(self, **kwargs):
                request = json.loads(kwargs["user_prompt"])
                point = request["points"][0]
                return {
                    "cards": [
                        {
                            "point_id": point["point_id"],
                            "front": f"Question {index} about {point['title']}?",
                            "back": point["evidence"][:500],
                            "source_excerpt": point["evidence"][:200],
                        }
                        for index in range(request["max_cards"] + 1)
                    ]
                }

        adapter = self.make_adapter(
            settings,
            provider_client_factory=OverQuotaClient,
        )
        generating = transition_run(run, GenerationStage.PLANNING)
        generating = transition_run(generating, GenerationStage.GENERATING)
        generating = reserve_run_call(generating, CallPurpose.GENERATE)

        with self.assertRaisesRegex(ValueError, "generation output"):
            adapter.generate_batch(
                generating,
                adapter.generation_batches(generating)[0],
            )

    def test_critic_prompt_contains_bounded_source_evidence(self):
        result = self.make_worker_result()
        settings = __import__(
            "ankiforge_ai.pipeline.generation_settings",
            fromlist=["GenerationSettings"],
        ).GenerationSettings(card_mode="auto")
        run = build_imported_generation_run(
            (result,),
            generation_settings=settings,
            level=IntelligenceLevel.DEEP,
            request_id=1,
        )
        captured = []

        class CriticClient:
            def complete_json(self, **kwargs):
                captured.append(kwargs)
                return {"decisions": []}

        adapter = self.make_adapter(
            settings,
            provider_client_factory=CriticClient,
        )
        current = transition_run(run, GenerationStage.PLANNING)
        current = transition_run(current, GenerationStage.GENERATING)
        current = reserve_run_call(current, CallPurpose.GENERATE)
        first_point = run.plan.points[0]
        first_chunk = first_point.source_chunk_ids[0]
        for chunk in current.chunks:
            current = start_chunk(current, chunk.chunk_id)
            cards = ()
            if chunk.chunk_id == first_chunk:
                evidence = current.document_snapshot["chunk_text_by_id"][
                    chunk.chunk_id
                ]
                cards = (
                    {
                        "candidate_id": "card-evidence",
                        "point_id": first_point.point_id,
                        "section_id": first_point.section_id,
                        "front": "What does this source explain?",
                        "back": evidence[:200],
                        "source_excerpt": evidence[:100],
                    },
                )
            current = succeed_chunk(current, chunk.chunk_id, cards)
        current = transition_run(current, GenerationStage.REVIEWING)
        current = reserve_run_call(current, CallPurpose.CRITIC)

        adapter.critic_callback(current)

        request = json.loads(captured[0]["user_prompt"])
        self.assertTrue(request["cards"][0]["evidence"])
        self.assertIn(
            request["cards"][0]["evidence"],
            current.document_snapshot["chunk_text_by_id"][first_chunk],
        )
        self.assertLessEqual(
            len(captured[0]["system_prompt"])
            + 1
            + len(captured[0]["user_prompt"]),
            MAX_AI_MATERIAL_CHARS,
        )

    def test_batch_namespaces_colliding_document_section_identities(self):
        results = (
            self.make_worker_result(),
            self.make_worker_result("plain.txt"),
        )
        settings = __import__(
            "ankiforge_ai.pipeline.generation_settings",
            fromlist=["GenerationSettings"],
        ).GenerationSettings(card_mode="auto")
        source_section_keys = {
            (result.document.document_id, point.section_id)
            for result in results
            for point in build_local_knowledge_plan(
                result.document,
                result.chunks,
                result.analysis,
            ).points
        }

        run = build_imported_generation_run(
            results,
            generation_settings=settings,
            level=IntelligenceLevel.FAST,
            request_id=1,
        )

        self.assertEqual(
            len({point.section_id for point in run.plan.points}),
            len(source_section_keys),
        )
        self.assertTrue(
            all(
                point.section_id.startswith("batch-section-")
                for point in run.plan.points
            )
        )

    def test_combined_batch_over_48_chunks_fails_before_a_run_or_provider_exists(self):
        source = self.make_worker_result()
        expanded = []
        for batch_index in range(2):
            expanded.append(
                replace(
                    source,
                    chunks=tuple(
                        replace(
                            source.chunks[0],
                            chunk_id=(
                                f"chunk-{batch_index * 25 + index + 1:016x}"
                            ),
                        )
                        for index in range(25)
                    ),
                )
            )

        with self.assertRaisesRegex(ValueError, "document_too_complex"):
            build_imported_generation_run(
                tuple(expanded),
                generation_settings=__import__(
                    "ankiforge_ai.pipeline.generation_settings",
                    fromlist=["GenerationSettings"],
                ).GenerationSettings(card_mode="auto"),
                level=IntelligenceLevel.STANDARD,
                request_id=1,
            )

    def test_all_provider_prompts_include_settings_and_auto_template_routing(self):
        result = self.make_worker_result()
        settings = __import__(
            "ankiforge_ai.pipeline.generation_settings",
            fromlist=["GenerationSettings"],
        ).GenerationSettings(
            card_mode="auto",
            card_count="fewer",
            answer_length="medium",
            language="zh",
        )
        run = build_imported_generation_run(
            (result,),
            generation_settings=settings,
            level=IntelligenceLevel.DEEP,
            request_id=1,
        )
        captured = []

        class SettingsClient:
            def complete_json(self, **kwargs):
                request = json.loads(kwargs["user_prompt"])
                captured.append((kwargs["purpose"], request))
                if kwargs["purpose"] == "planner":
                    return {
                        "point_ids": [
                            point.point_id for point in run.plan.points
                        ]
                    }
                if kwargs["purpose"] in {"generate", "supplement"}:
                    return {"cards": []}
                if kwargs["purpose"] == "critic":
                    return {"decisions": []}
                if kwargs["purpose"] == "repair":
                    card = request["card"]
                    return {
                        "candidate_id": card["candidate_id"],
                        "point_id": card["point_id"],
                        "section_id": card["section_id"],
                        "front": "What is grounded evidence?",
                        "back": "grounded evidence",
                        "source_excerpt": "grounded evidence",
                    }
                raise AssertionError("unexpected purpose")

        adapter = self.make_adapter(
            settings,
            provider_client_factory=SettingsClient,
        )
        planning = transition_run(run, GenerationStage.PLANNING)
        planning = reserve_run_call(planning, CallPurpose.PLANNER)
        adapter.planner_callback(planning)

        generating = transition_run(run, GenerationStage.PLANNING)
        generating = transition_run(generating, GenerationStage.GENERATING)
        generating = reserve_run_call(generating, CallPurpose.GENERATE)
        adapter.generate_batch(
            generating,
            adapter.generation_batches(generating)[0],
        )

        first_point = run.plan.points[0]
        reviewing = transition_run(run, GenerationStage.PLANNING)
        reviewing = transition_run(reviewing, GenerationStage.GENERATING)
        reviewing = reserve_run_call(reviewing, CallPurpose.GENERATE)
        first_source = ""
        for chunk in reviewing.chunks:
            reviewing = start_chunk(reviewing, chunk.chunk_id)
            cards = ()
            if chunk.chunk_id in first_point.source_chunk_ids:
                first_source = reviewing.document_snapshot[
                    "chunk_text_by_id"
                ][chunk.chunk_id]
                cards = (
                    {
                        "candidate_id": "card-settings",
                        "point_id": first_point.point_id,
                        "section_id": first_point.section_id,
                        "front": "What is grounded evidence?",
                        "back": first_source[:120],
                        "source_excerpt": first_source[:80],
                    },
                )
            reviewing = succeed_chunk(reviewing, chunk.chunk_id, cards)
        reviewing = transition_run(reviewing, GenerationStage.REVIEWING)
        reviewing = reserve_run_call(reviewing, CallPurpose.CRITIC)
        adapter.critic_callback(reviewing)

        adapter.repair_callback(
            {
                "candidate_id": "card-settings",
                "point_id": first_point.point_id,
                "section_id": first_point.section_id,
                "recommended_template": first_point.recommended_template,
                "front": "Broken",
                "back": "Broken",
            },
            "grounded evidence",
        )

        checking = transition_run(reviewing, GenerationStage.CHECKING_COVERAGE)
        checking = reserve_run_call(checking, CallPurpose.SUPPLEMENT)
        adapter.supplement_callback(checking, (first_point.point_id,))

        self.assertEqual(
            [purpose for purpose, _request in captured],
            ["planner", "generate", "critic", "repair", "supplement"],
        )
        expected_settings = settings.to_safe_dict()
        for purpose, request in captured:
            with self.subTest(purpose=purpose):
                self.assertEqual(
                    request["generation_settings"],
                    expected_settings,
                )
        for purpose, request in captured:
            points = request.get("points", ())
            for point in points:
                self.assertEqual(
                    point["card_template"],
                    point["recommended_template"],
                )
        critic_card = next(
            request["cards"][0]
            for purpose, request in captured
            if purpose == "critic"
        )
        self.assertEqual(
            critic_card["card_template"],
            first_point.recommended_template,
        )
        repair_request = next(
            request
            for purpose, request in captured
            if purpose == "repair"
        )
        self.assertEqual(
            repair_request["card_template"],
            first_point.recommended_template,
        )

    def test_maximum_run_planner_generation_and_critic_prompts_stay_bounded(self):
        settings = __import__(
            "ankiforge_ai.pipeline.generation_settings",
            fromlist=["GenerationSettings"],
        ).GenerationSettings(card_mode="auto")
        run = self.make_maximum_generation_run()
        captured = []

        class MaximumRunClient:
            def complete_json(self, **kwargs):
                captured.append(kwargs)
                if kwargs["purpose"] == "planner":
                    return {
                        "point_ids": [
                            point.point_id for point in run.plan.points
                        ]
                    }
                if kwargs["purpose"] == "generate":
                    return {"cards": []}
                if kwargs["purpose"] == "critic":
                    return {"decisions": []}
                raise AssertionError("unexpected purpose")

        adapter = self.make_adapter(
            settings,
            provider_client_factory=MaximumRunClient,
        )
        planning = transition_run(run, GenerationStage.PLANNING)
        planning = reserve_run_call(planning, CallPurpose.PLANNER)
        adapter.planner_callback(planning)

        generating = transition_run(run, GenerationStage.PLANNING)
        generating = transition_run(generating, GenerationStage.GENERATING)
        generating = reserve_run_call(generating, CallPurpose.GENERATE)
        adapter.generate_batch(
            generating,
            adapter.generation_batches(generating)[0],
        )

        reviewing = transition_run(run, GenerationStage.PLANNING)
        reviewing = transition_run(reviewing, GenerationStage.GENERATING)
        reviewing = reserve_run_call(reviewing, CallPurpose.GENERATE)
        points_by_chunk = {}
        for point in run.plan.points:
            points_by_chunk.setdefault(
                point.source_chunk_ids[0],
                [],
            ).append(point)
        for chunk in reviewing.chunks:
            reviewing = start_chunk(reviewing, chunk.chunk_id)
            cards = tuple(
                {
                    "candidate_id": f"card-{point.point_id[6:]}",
                    "point_id": point.point_id,
                    "section_id": point.section_id,
                    "front": "What is this bounded point?",
                    "back": "evidence " * 20,
                    "source_excerpt": "evidence",
                }
                for point in points_by_chunk[chunk.chunk_id]
            )
            reviewing = succeed_chunk(
                reviewing,
                chunk.chunk_id,
                cards,
            )
        reviewing = transition_run(reviewing, GenerationStage.REVIEWING)
        reviewing = reserve_run_call(reviewing, CallPurpose.CRITIC)
        adapter.critic_callback(reviewing)

        self.assertEqual(
            [call["purpose"] for call in captured],
            ["planner", "generate", "critic"],
        )
        for call in captured:
            with self.subTest(purpose=call["purpose"]):
                self.assertLessEqual(
                    len(call["system_prompt"])
                    + 1
                    + len(call["user_prompt"]),
                    MAX_AI_MATERIAL_CHARS,
                )

    def test_panel_uses_intelligent_controller_for_parsed_document_runs(self):
        panel = self.panel_source()
        generate = self.function_source(panel, "_generate_cards")
        start = self.function_source(panel, "_start_intelligent_generation")

        self.assertIn("_start_intelligent_generation", generate)
        self.assertIn("build_imported_generation_run", start)
        self.assertIn("BoundedProviderGenerationAdapter", start)
        self.assertIn("self._intelligent_generation_controller.submit", start)

    def test_import_completion_never_starts_ai_and_artifact_changes_clear_all_gates(self):
        completion = self.function_source(
            self.panel_source(),
            "_handle_document_import_completion",
        )
        self.assertNotIn("_generate_cards", completion)
        self.assertNotIn("_generation_controller.submit", completion)

        session = BeginnerFlowSession()
        session.record_document_intelligence_artifacts(
            parsed_documents=(object(),),
            analyses=(object(),),
            chunks=(object(),),
            plan=object(),
            estimate=object(),
            run=object(),
        )
        session.apply_ai_candidate_card_drafts(
            (
                BeginnerAICardDraft(
                    id="draft-1",
                    front="Question",
                    back="Answer",
                    source_excerpt="Source",
                ),
            )
        )
        session.duplicate_check_preview_state = BeginnerArtifactState.CURRENT
        session.final_confirmation_preview_state = BeginnerArtifactState.CURRENT

        session.mark_document_queue_changed()

        self.assertEqual(session.parsed_documents, ())
        self.assertEqual(session.document_analyses, ())
        self.assertEqual(session.document_chunks, ())
        self.assertIsNone(session.knowledge_plan)
        self.assertIsNone(session.intelligence_estimate)
        self.assertIsNone(session.intelligence_run)
        self.assertEqual(session.candidate_card_previews, ())
        self.assertIs(
            session.duplicate_check_preview_state,
            BeginnerArtifactState.CLEARED,
        )
        self.assertIs(
            session.final_confirmation_preview_state,
            BeginnerArtifactState.CLEARED,
        )

    def test_intelligence_setting_change_invalidates_artifacts_but_same_value_does_not(self):
        session = BeginnerFlowSession()
        session.record_document_intelligence_artifacts(
            parsed_documents=(object(),),
            analyses=(object(),),
            chunks=(object(),),
            plan=object(),
            estimate=object(),
            run=object(),
        )
        revision = session.document_artifact_revision

        session.set_intelligence_level(IntelligenceLevel.STANDARD)
        self.assertEqual(session.document_artifact_revision, revision)
        self.assertTrue(session.parsed_documents)

        session.set_intelligence_level(IntelligenceLevel.DEEP)
        self.assertEqual(
            session.intelligence_level,
            IntelligenceLevel.DEEP,
        )
        self.assertGreater(session.document_artifact_revision, revision)
        self.assertEqual(session.parsed_documents, ())

    def test_api_settings_and_existing_write_safety_controls_remain_unchanged(self):
        panel = self.panel_source()
        build_ui = self.function_source(panel, "_build_ui")
        write = self.function_source(panel, "_confirm_and_write")
        discard = self.function_source(panel, "discard_session")

        self.assertNotIn("_build_provider_section", build_ui)
        self.assertNotIn("api_key_input", panel)
        self.assertIn("self._check_duplicates()", write)
        self.assertIn("if not confirmed", write)
        self.assertIn("self.write_coordinator.execute_if_confirmed", write)
        self.assertIn(
            "self._active_provider_generation_adapter = None",
            discard,
        )
        self.assertIn("self._last_intelligence_run = None", discard)

    @staticmethod
    def make_worker_result(filename="structured.md"):
        from ankiforge_ai.ui.document_import_queue import PrivatePathToken
        from ankiforge_ai.ui.document_import_task_controller import (
            import_document_path_token,
        )

        fixture = (
            Path(__file__).parent
            / "fixtures"
            / "documents"
            / filename
        )
        return import_document_path_token(
            PrivatePathToken.from_path(
                fixture,
                byte_size=fixture.stat().st_size,
            )
        )

    @staticmethod
    def make_adapter(settings, *, provider_client_factory):
        runtime = __import__(
            "ankiforge_ai.ui.beginner_ai_card_drafts",
            fromlist=["BeginnerAIProviderRuntimeSettings"],
        ).BeginnerAIProviderRuntimeSettings(
            provider_name="Fake",
            base_url="https://provider.invalid/v1",
            model="fake-model",
            api_key="sk-private-never-render",
        )
        return BoundedProviderGenerationAdapter(
            runtime_settings=runtime,
            generation_settings=settings,
            provider_client_factory=provider_client_factory,
        )

    @staticmethod
    def make_maximum_generation_run():
        chunk_ids = tuple(
            f"chunk-{index:016x}" for index in range(1, 49)
        )
        points = tuple(
            KnowledgePointPlan(
                point_id=f"point-{index:016x}",
                title=f"evidence concept {index}",
                point_type="concept",
                priority="high" if index % 3 == 0 else "medium",
                section_id=f"section-{((index - 1) // 2) + 1}",
                source_chunk_ids=(
                    chunk_ids[(index - 1) // 2],
                ),
                source_locations=(),
                recommended_template="concept",
                rationale="bounded maximum fixture",
            )
            for index in range(1, 97)
        )
        plan = KnowledgePlan(
            plan_id="plan-ffffffffffffffff",
            document_id="doc-maximum-run",
            source="local",
            chunk_ids=chunk_ids,
            points=points,
        )
        run = create_generation_run(
            run_id="run-maximum",
            request_id=1,
            document_id=plan.document_id,
            document_hash="f" * 64,
            document_snapshot={
                "chunk_text_by_id": {
                    chunk_id: (
                        f"evidence concept {index * 2 - 1} "
                        f"evidence concept {index * 2} "
                        + "evidence " * 1_400
                    )
                    for index, chunk_id in enumerate(
                        chunk_ids,
                        start=1,
                    )
                }
            },
            settings_snapshot={"card_mode": "auto"},
            level=IntelligenceLevel.DEEP,
            chunk_ids=chunk_ids,
        )
        return replace(run, plan=plan)

    @staticmethod
    def function_source(source, name):
        tree = ast.parse(source)
        node = next(
            item
            for item in ast.walk(tree)
            if isinstance(item, ast.FunctionDef) and item.name == name
        )
        return ast.get_source_segment(source, node) or ""

    @staticmethod
    def root():
        return Path(__file__).parents[1]

    def panel_source(self):
        return (
            self.root() / "ankiforge_ai" / "ui" / "card_maker_panel.py"
        ).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
