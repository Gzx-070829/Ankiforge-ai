"""Non-Qt bridge from imported documents to bounded Provider stages."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field, replace

from ..document import SourceSpan, source_span_from_chunk
from ..intelligence import (
    CallPurpose,
    GenerationRun,
    IntelligenceLevel,
    KnowledgePlan,
    create_generation_run,
)
from ..intelligence.planning import build_local_knowledge_plan
from ..pipeline.generation_settings import (
    GenerationSettings,
    card_limit_for_settings,
)
from ..pipeline.ai_generation_limits import validate_ai_material_text
from ..pipeline.openai_compatible_http_transport import (
    OpenAICompatibleHTTPTransport,
)
from ..pipeline.openai_compatible_provider import build_chat_completions_url
from ..pipeline.provider_endpoint_safety import (
    DEFAULT_OFFICIAL_PROVIDER_HOSTS,
    endpoint_is_authorized,
)
from .beginner_ai_card_drafts import (
    BeginnerAICardDraft,
    BeginnerAIProviderRuntimeSettings,
)
from .document_import_queue import DocumentImportWorkerResult


_PROVIDER_PURPOSES = frozenset(
    {"planner", "generate", "critic", "repair", "supplement"}
)
_MAX_PROVIDER_JSON_CHARS = 256_000
_MAX_GENERATION_BATCHES = 3
_SAFE_REASON = re.compile(r"^[a-z][a-z0-9_]{0,119}$")
_SETTINGS_INSTRUCTION = (
    "Follow generation_settings for card mode, answer length, output language, "
    "and each point's card_template. "
)


class _OpenAICompatibleJSONClient:
    """One raw JSON completion; retry and billing stay outside this client."""

    def __init__(self, transport=None):
        self._transport = transport or OpenAICompatibleHTTPTransport()

    def complete_json(
        self,
        *,
        runtime_settings: BeginnerAIProviderRuntimeSettings,
        endpoint_confirmation_key: str | None,
        purpose: str,
        system_prompt: str,
        user_prompt: str,
    ) -> object:
        if purpose not in _PROVIDER_PURPOSES:
            raise ValueError("provider purpose is unsupported")
        if not endpoint_is_authorized(
            runtime_settings.base_url,
            official_hosts=DEFAULT_OFFICIAL_PROVIDER_HOSTS,
            confirmation_key=endpoint_confirmation_key,
        ):
            raise RuntimeError("endpoint_not_authorized")
        response = self._transport.post_json(
            url=build_chat_completions_url(runtime_settings.base_url),
            headers={
                "Authorization": f"Bearer {runtime_settings.api_key}",
                "Content-Type": "application/json",
            },
            payload={
                "model": runtime_settings.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.1,
            },
            timeout_seconds=runtime_settings.timeout_seconds,
        )
        status_code = getattr(response, "status_code", None)
        if not isinstance(status_code, int) or not 200 <= status_code < 300:
            raise RuntimeError("provider_request_failed")
        try:
            content = response.json_body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise RuntimeError("provider_output_invalid") from None
        if (
            not isinstance(content, str)
            or not content.strip()
            or len(content) > _MAX_PROVIDER_JSON_CHARS
        ):
            raise RuntimeError("provider_output_invalid")
        try:
            return json.loads(_strip_json_fence(content.strip()))
        except (json.JSONDecodeError, UnicodeError, RecursionError):
            raise RuntimeError("provider_output_invalid") from None


@dataclass(frozen=True, repr=False)
class BoundedProviderGenerationAdapter:
    """Provider callbacks whose every dispatch is reserved by the controller."""

    runtime_settings: BeginnerAIProviderRuntimeSettings = field(repr=False)
    generation_settings: GenerationSettings
    endpoint_confirmation_key: str | None = field(default=None, repr=False)
    provider_client_factory: object = field(
        default=_OpenAICompatibleJSONClient,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if not isinstance(
            self.runtime_settings,
            BeginnerAIProviderRuntimeSettings,
        ):
            raise TypeError("runtime_settings must be provider runtime settings")
        if not isinstance(self.generation_settings, GenerationSettings):
            raise TypeError("generation_settings must be GenerationSettings")
        if not callable(self.provider_client_factory):
            raise TypeError("provider_client_factory must be callable")

    def generation_batches(
        self,
        run: GenerationRun,
    ) -> tuple[tuple[str, ...], ...]:
        """Return contiguous bounded batches without making a Provider call."""

        _require_run(run)
        chunk_ids = tuple(chunk.chunk_id for chunk in run.chunks)
        batch_count = min(_MAX_GENERATION_BATCHES, len(chunk_ids))
        base, remainder = divmod(len(chunk_ids), batch_count)
        batches = []
        offset = 0
        for index in range(batch_count):
            size = base + (1 if index < remainder else 0)
            batches.append(chunk_ids[offset : offset + size])
            offset += size
        return tuple(batches)

    def generate_batch(
        self,
        run: GenerationRun,
        chunk_ids,
    ) -> dict[str, tuple[dict[str, str], ...]]:
        selected_ids = _validate_selected_chunks(run, chunk_ids)
        _require_reserved(run, CallPurpose.GENERATE)
        plan = _require_plan(run)
        points = tuple(
            point
            for point in plan.points
            if set(point.source_chunk_ids) & set(selected_ids)
        )
        if not points:
            raise ValueError("selected chunks have no knowledge points")
        max_cards = self._cards_for_batch(run, selected_ids)
        payload = self._complete(
            purpose="generate",
            system_prompt=(
                "Create source-grounded Anki cards. Return JSON only. "
                + _SETTINGS_INSTRUCTION
                + "Use only the supplied point IDs and evidence."
            ),
            user_prompt=json.dumps(
                {
                    "generation_settings": self.generation_settings.to_safe_dict(),
                    "schema": {
                        "cards": [
                            {
                                "point_id": "point-id",
                                "front": "question",
                                "back": "answer",
                                "source_excerpt": "exact source excerpt",
                            }
                        ]
                    },
                    "max_cards": max_cards,
                    "points": [
                        {
                            "point_id": point.point_id,
                            "title": point.title[:160],
                            "recommended_template": point.recommended_template,
                            "card_template": _effective_card_template(
                                self.generation_settings,
                                point.recommended_template,
                            ),
                            "evidence": _point_evidence(
                                run,
                                point,
                                selected_ids,
                                max_chars=700,
                            ),
                        }
                        for point in points
                    ],
                },
                ensure_ascii=False,
            ),
        )
        return _materialize_cards(
            run,
            payload,
            selected_chunk_ids=selected_ids,
            allowed_point_ids={point.point_id for point in points},
            max_cards=max_cards,
        )

    def planner_callback(self, run: GenerationRun) -> KnowledgePlan:
        """Make the optional planner call and safely fall back to local order."""

        _require_reserved(run, CallPurpose.PLANNER)
        plan = _require_plan(run)
        try:
            payload = self._complete(
                purpose="planner",
                system_prompt=(
                    "Prioritize the supplied grounded knowledge points. "
                    + _SETTINGS_INSTRUCTION
                    + "Return JSON only and never invent an ID."
                ),
                user_prompt=json.dumps(
                    {
                        "generation_settings": (
                            self.generation_settings.to_safe_dict()
                        ),
                        "schema": {"point_ids": ["point-id"]},
                        "points": [
                            {
                                "point_id": point.point_id,
                                "title": point.title[:100],
                                "priority": point.priority,
                                "recommended_template": (
                                    point.recommended_template
                                ),
                                "card_template": _effective_card_template(
                                    self.generation_settings,
                                    point.recommended_template,
                                ),
                                "evidence": _point_evidence(
                                    run,
                                    point,
                                    tuple(chunk.chunk_id for chunk in run.chunks),
                                    max_chars=120,
                                ),
                            }
                            for point in plan.points
                        ],
                    },
                    ensure_ascii=False,
                ),
            )
            point_ids = _planner_point_ids(payload, plan)
        except Exception:
            return plan
        by_id = {point.point_id: point for point in plan.points}
        ordered = tuple(by_id[point_id] for point_id in point_ids)
        ordered += tuple(
            point for point in plan.points if point.point_id not in point_ids
        )
        digest = hashlib.sha256(
            "\x1f".join(point.point_id for point in ordered).encode("utf-8")
        ).hexdigest()[:16]
        return KnowledgePlan(
            plan_id=f"plan-{digest}",
            document_id=plan.document_id,
            source="llm",
            chunk_ids=plan.chunk_ids,
            points=ordered,
        )

    def critic_callback(self, run: GenerationRun) -> dict[str, dict]:
        """Return bounded model decisions; local rules remain authoritative."""

        _require_reserved(run, CallPurpose.CRITIC)
        if not run.cards:
            return {}
        try:
            plan = _require_plan(run)
            by_point = {
                point.point_id: point for point in plan.points
            }
            payload = self._complete(
                purpose="critic",
                system_prompt=(
                    "Review source grounding and clarity. Return JSON only, "
                    + _SETTINGS_INSTRUCTION
                    + "Without reasoning, use actions: pass, flag, repair, reject."
                ),
                user_prompt=json.dumps(
                    {
                        "generation_settings": (
                            self.generation_settings.to_safe_dict()
                        ),
                        "schema": {
                            "decisions": [
                                {
                                    "candidate_id": "card-id",
                                    "action": "pass",
                                    "reason_codes": ["safe_reason"],
                                }
                            ]
                        },
                        "cards": [
                            {
                                "candidate_id": _card_value(
                                    card,
                                    "candidate_id",
                                ),
                                "front": _card_value(card, "front"),
                                "back": (
                                    _card_value(card, "back") or ""
                                )[:140],
                                "card_template": _effective_card_template(
                                    self.generation_settings,
                                    by_point[
                                        _card_value(card, "point_id")
                                    ].recommended_template,
                                ),
                                "evidence": _point_evidence(
                                    run,
                                    by_point[
                                        _card_value(card, "point_id")
                                    ],
                                    tuple(
                                        chunk.chunk_id
                                        for chunk in run.chunks
                                    ),
                                    max_chars=140,
                                ),
                            }
                            for card in run.cards
                        ],
                    },
                    ensure_ascii=False,
                ),
            )
            return _critic_decisions(payload, run)
        except Exception:
            return {}

    def repair_callback(self, card: object, source_text: str) -> dict:
        """Make one controller-reserved repair call for one candidate."""

        payload = self._complete(
            purpose="repair",
            system_prompt=(
                "Repair one Anki card using only the evidence. Return JSON only "
                + _SETTINGS_INSTRUCTION
                + "Preserve candidate_id, point_id, and section_id."
            ),
            user_prompt=json.dumps(
                {
                    "generation_settings": self.generation_settings.to_safe_dict(),
                    "schema": {
                        "candidate_id": "card-id",
                        "point_id": "point-id",
                        "section_id": "section-id",
                        "front": "question",
                        "back": "answer",
                        "source_excerpt": "exact source excerpt",
                    },
                    "card": dict(card) if isinstance(card, Mapping) else {},
                    "card_template": _effective_card_template(
                        self.generation_settings,
                        _card_value(card, "recommended_template"),
                    ),
                    "evidence": source_text[:4_000],
                },
                ensure_ascii=False,
            ),
        )
        return _validated_repaired_card(payload, card, source_text)

    def supplement_callback(
        self,
        run: GenerationRun,
        point_ids,
    ) -> dict[str, tuple[dict[str, str], ...]]:
        """Make the single controller-reserved Deep coverage supplement call."""

        _require_reserved(run, CallPurpose.SUPPLEMENT)
        plan = _require_plan(run)
        selected = tuple(point_ids)
        points = tuple(
            point for point in plan.points if point.point_id in selected
        )[:10]
        if (
            not points
            or len(set(selected)) != len(selected)
        ):
            raise ValueError("supplement points are invalid")
        remaining_card_slots = (
            card_limit_for_settings(self.generation_settings)
            - len(run.cards)
        )
        if remaining_card_slots < 1:
            raise ValueError("generation card limit reached")
        max_cards = min(len(points), 10, remaining_card_slots)
        selected_chunks = tuple(
            dict.fromkeys(
                chunk_id
                for point in points
                for chunk_id in point.source_chunk_ids
                if _chunk_succeeded(run, chunk_id)
            )
        )
        if not selected_chunks:
            raise ValueError("supplement points have no succeeded source chunks")
        payload = self._complete(
            purpose="supplement",
            system_prompt=(
                "Create only missing source-grounded Anki cards. "
                + _SETTINGS_INSTRUCTION
                + "Return JSON only."
            ),
            user_prompt=json.dumps(
                {
                    "generation_settings": self.generation_settings.to_safe_dict(),
                    "schema": {
                        "cards": [
                            {
                                "point_id": "point-id",
                                "front": "question",
                                "back": "answer",
                                "source_excerpt": "exact source excerpt",
                            }
                        ]
                    },
                    "max_cards": max_cards,
                    "points": [
                        {
                            "point_id": point.point_id,
                            "title": point.title[:160],
                            "recommended_template": point.recommended_template,
                            "card_template": _effective_card_template(
                                self.generation_settings,
                                point.recommended_template,
                            ),
                            "evidence": _point_evidence(
                                run,
                                point,
                                selected_chunks,
                                max_chars=700,
                            ),
                        }
                        for point in points
                    ],
                },
                ensure_ascii=False,
            ),
        )
        return _materialize_cards(
            run,
            payload,
            selected_chunk_ids=selected_chunks,
            allowed_point_ids=set(selected),
            max_cards=max_cards,
        )

    def __call__(
        self,
        run: GenerationRun,
        chunk_id: str | None = None,
    ):
        """Retry callback: dispatch only the explicitly failed chunk."""

        if chunk_id is None:
            raise ValueError(
                "grouped generation must be dispatched by the controller"
            )
        result = self.generate_batch(run, (chunk_id,))
        return result.get(chunk_id, ())

    def _cards_for_batch(
        self,
        run: GenerationRun,
        selected_ids: tuple[str, ...],
    ) -> int:
        batches = self.generation_batches(run)
        total = card_limit_for_settings(self.generation_settings)
        remaining = total - len(run.cards)
        if remaining < 1:
            raise ValueError("card limit reached")
        if selected_ids not in batches:
            quota = max(
                1,
                min(total, (total + len(run.chunks) - 1) // len(run.chunks)),
            )
        else:
            batch_index = batches.index(selected_ids)
            base, remainder = divmod(total, len(batches))
            quota = max(1, base + (1 if batch_index < remainder else 0))
        return min(remaining, quota)

    def _complete(self, **kwargs):
        validate_ai_material_text(
            kwargs["system_prompt"] + "\n" + kwargs["user_prompt"]
        )
        client = self.provider_client_factory()
        complete_json = getattr(client, "complete_json", None)
        if not callable(complete_json):
            raise TypeError("provider client must provide complete_json")
        return complete_json(
            runtime_settings=self.runtime_settings,
            endpoint_confirmation_key=self.endpoint_confirmation_key,
            **kwargs,
        )

    def __repr__(self) -> str:
        return (
            "BoundedProviderGenerationAdapter("
            f"level_settings={self.generation_settings.to_safe_dict()!r}, "
            f"endpoint_confirmed={self.endpoint_confirmation_key is not None})"
        )


def build_imported_generation_run(
    results,
    *,
    generation_settings: GenerationSettings,
    level: IntelligenceLevel | str,
    request_id: int,
) -> GenerationRun:
    selected = tuple(results)
    if not selected or not all(
        isinstance(result, DocumentImportWorkerResult) for result in selected
    ):
        raise ValueError("results must contain imported document results")
    if not isinstance(generation_settings, GenerationSettings):
        raise TypeError("generation_settings must be GenerationSettings")
    try:
        normalized_level = IntelligenceLevel(level)
    except (TypeError, ValueError):
        raise ValueError("level must be fast, standard, or deep") from None
    chunks = tuple(chunk for result in selected for chunk in result.chunks)
    if not chunks or len(chunks) > 48:
        raise ValueError("document_too_complex")
    if len({chunk.chunk_id for chunk in chunks}) != len(chunks):
        raise ValueError("duplicate chunk identity")
    local_plans = tuple(
        build_local_knowledge_plan(
            result.document,
            result.chunks,
            result.analysis,
        )
        for result in selected
    )
    points = tuple(
        replace(
            point,
            section_id=(
                "batch-section-"
                + hashlib.sha256(
                    f"{result.document.document_id}\x1f"
                    f"{point.section_id}".encode("utf-8")
                ).hexdigest()[:16]
            ),
        )
        for result, plan in zip(selected, local_plans)
        for point in plan.points
    )
    if not points or len(points) > 96:
        raise ValueError("planning_failed")
    digest_input = "\x1f".join(
        (
            *(result.document.document_id for result in selected),
            *(chunk.chunk_id for chunk in chunks),
            *(chunk.text for chunk in chunks),
        )
    )
    digest = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()
    document_id = f"batch-{digest[:16]}"
    plan = KnowledgePlan(
        plan_id=f"plan-{digest[16:32]}",
        document_id=document_id,
        source="local",
        chunk_ids=tuple(chunk.chunk_id for chunk in chunks),
        points=points,
    )
    source_span_by_point_id = _build_source_span_map(
        selected,
        chunks,
        points,
        batch_document_id=document_id,
    )
    run = create_generation_run(
        run_id=f"run-{digest[32:48]}",
        request_id=request_id,
        document_id=document_id,
        document_hash=digest,
        document_snapshot={
            "chunk_text_by_id": {
                chunk.chunk_id: chunk.text for chunk in chunks
            },
            "source_span_by_point_id": {
                point_id: span.to_safe_dict()
                for point_id, span in source_span_by_point_id.items()
            },
        },
        settings_snapshot={
            **generation_settings.to_safe_dict(),
            "intelligence_level": normalized_level.value,
            "document_count": len(selected),
        },
        level=normalized_level,
        chunk_ids=plan.chunk_ids,
    )
    return replace(run, plan=plan)


def drafts_from_generation_run(run: GenerationRun) -> tuple[BeginnerAICardDraft, ...]:
    _require_run(run)
    plan = _require_plan(run)
    location_by_point = {
        point.point_id: (
            point.source_locations[0]
            if point.source_locations
            else None
        )
        for point in plan.points
    }
    span_payloads = run.document_snapshot.get("source_span_by_point_id", {})
    drafts = []
    for index, card in enumerate(run.cards, start=1):
        if not isinstance(card, Mapping):
            continue
        front = card.get("front")
        back = card.get("back")
        source_excerpt = card.get("source_excerpt")
        if not all(
            isinstance(value, str) and value.strip()
            for value in (front, back, source_excerpt)
        ):
            continue
        drafts.append(
            BeginnerAICardDraft(
                id=f"universal-{index}",
                front=front,
                back=back,
                source_excerpt=source_excerpt,
                source_location=location_by_point.get(
                    card.get("point_id")
                ),
                source_span=_source_span_from_snapshot(
                    span_payloads,
                    card.get("point_id"),
                ),
            )
        )
    return tuple(drafts)


def _build_source_span_map(
    results,
    chunks,
    points,
    *,
    batch_document_id: str,
) -> dict[str, SourceSpan]:
    document_by_id = {result.document.document_id: result.document for result in results}
    chunk_by_id = {chunk.chunk_id: chunk for chunk in chunks}
    spans = {}
    for point in points:
        point_chunks = tuple(
            chunk_by_id[chunk_id]
            for chunk_id in point.source_chunk_ids
            if chunk_id in chunk_by_id
        )
        if len(point_chunks) == 1:
            chunk = point_chunks[0]
            document = document_by_id[chunk.document_id]
            spans[point.point_id] = source_span_from_chunk(
                chunk,
                source_label=document.source_label,
            )
            continue
        document_ids = tuple(dict.fromkeys(chunk.document_id for chunk in point_chunks))
        if len(document_ids) == 1:
            document_id = document_ids[0]
            source_label = document_by_id[document_id].source_label
        else:
            document_id = batch_document_id
            source_label = "Imported material"
        spans[point.point_id] = SourceSpan(
            document_id=document_id,
            source_label=source_label,
        )
    return spans


def _source_span_from_snapshot(span_payloads, point_id):
    if not isinstance(span_payloads, Mapping) or not isinstance(point_id, str):
        return None
    payload = span_payloads.get(point_id)
    if not isinstance(payload, Mapping):
        return None
    try:
        return SourceSpan.from_safe_dict(payload)
    except (TypeError, ValueError):
        return None


def _materialize_cards(
    run: GenerationRun,
    payload: object,
    *,
    selected_chunk_ids: tuple[str, ...],
    allowed_point_ids: set[str],
    max_cards: int,
) -> dict[str, tuple[dict[str, str], ...]]:
    if not isinstance(payload, Mapping) or set(payload) != {"cards"}:
        raise ValueError("generation output is invalid")
    raw_cards = payload.get("cards")
    if (
        isinstance(max_cards, bool)
        or not isinstance(max_cards, int)
        or not 1 <= max_cards <= 10
        or not isinstance(raw_cards, list)
        or len(raw_cards) > max_cards
    ):
        raise ValueError("generation output is invalid")
    plan = _require_plan(run)
    by_point = {
        point.point_id: point
        for point in plan.points
        if point.point_id in allowed_point_ids
    }
    chunk_text = _chunk_text_by_id(run)
    grouped = {chunk_id: [] for chunk_id in selected_chunk_ids}
    for index, raw in enumerate(raw_cards):
        if not isinstance(raw, Mapping) or set(raw) != {
            "point_id",
            "front",
            "back",
            "source_excerpt",
        }:
            raise ValueError("generation output is invalid")
        point_id = raw.get("point_id")
        point = by_point.get(point_id)
        if point is None:
            raise ValueError("generation point is not grounded")
        chunk_id = next(
            (
                item
                for item in point.source_chunk_ids
                if item in grouped
            ),
            None,
        )
        if chunk_id is None:
            raise ValueError("generation point is outside its batch")
        front = _bounded_text(raw.get("front"), 500)
        back = _bounded_text(raw.get("back"), 4_000)
        excerpt = _bounded_text(raw.get("source_excerpt"), 1_000)
        if _normalize_evidence(excerpt) not in _normalize_evidence(
            chunk_text[chunk_id]
        ):
            raise ValueError("generation excerpt is not grounded")
        digest = hashlib.sha256(
            f"{run.run_id}\x1f{run.call_budget.call_count}\x1f"
            f"{point_id}\x1f{index}\x1f{front}".encode("utf-8")
        ).hexdigest()[:16]
        grouped[chunk_id].append(
            {
                "candidate_id": f"card-{digest}",
                "point_id": point.point_id,
                "section_id": point.section_id,
                "front": front,
                "back": back,
                "source_excerpt": excerpt,
                "recommended_template": point.recommended_template,
            }
        )
    return {
        chunk_id: tuple(cards)
        for chunk_id, cards in grouped.items()
    }


def _planner_point_ids(payload: object, plan: KnowledgePlan) -> tuple[str, ...]:
    if not isinstance(payload, Mapping) or set(payload) != {"point_ids"}:
        raise ValueError("planner output is invalid")
    point_ids = payload.get("point_ids")
    known = {point.point_id for point in plan.points}
    if (
        not isinstance(point_ids, list)
        or not point_ids
        or len(point_ids) > len(known)
        or len(set(point_ids)) != len(point_ids)
        or any(point_id not in known for point_id in point_ids)
    ):
        raise ValueError("planner output is invalid")
    return tuple(point_ids)


def _critic_decisions(payload: object, run: GenerationRun) -> dict[str, dict]:
    if not isinstance(payload, Mapping) or set(payload) != {"decisions"}:
        raise ValueError("critic output is invalid")
    values = payload.get("decisions")
    candidate_ids = {
        _card_value(card, "candidate_id") for card in run.cards
    }
    if not isinstance(values, list) or len(values) > len(candidate_ids):
        raise ValueError("critic output is invalid")
    result = {}
    for value in values:
        if not isinstance(value, Mapping) or set(value) != {
            "candidate_id",
            "action",
            "reason_codes",
        }:
            raise ValueError("critic output is invalid")
        candidate_id = value.get("candidate_id")
        action = value.get("action")
        reasons = value.get("reason_codes")
        if (
            candidate_id not in candidate_ids
            or candidate_id in result
            or action not in {"pass", "flag", "repair", "reject"}
            or not isinstance(reasons, list)
            or len(reasons) > 8
        ):
            raise ValueError("critic output is invalid")
        safe_reasons = tuple(
            reason
            for reason in reasons
            if isinstance(reason, str) and _SAFE_REASON.fullmatch(reason)
        )
        result[candidate_id] = {
            "action": action,
            "reason_codes": safe_reasons,
        }
    return result


def _validated_repaired_card(
    payload: object,
    original: object,
    source_text: str,
) -> dict:
    fields = {
        "candidate_id",
        "point_id",
        "section_id",
        "front",
        "back",
        "source_excerpt",
    }
    if not isinstance(payload, Mapping) or set(payload) != fields:
        raise ValueError("repair output is invalid")
    for identity in ("candidate_id", "point_id", "section_id"):
        if payload.get(identity) != _card_value(original, identity):
            raise ValueError("repair changed identity")
    result = {
        identity: payload.get(identity)
        for identity in ("candidate_id", "point_id", "section_id")
    }
    result.update(
        {
            "front": _bounded_text(payload.get("front"), 500),
            "back": _bounded_text(payload.get("back"), 4_000),
            "source_excerpt": _bounded_text(
                payload.get("source_excerpt"),
                1_000,
            ),
        }
    )
    recommended_template = _card_value(original, "recommended_template")
    if isinstance(recommended_template, str):
        result["recommended_template"] = recommended_template
    if _normalize_evidence(result["source_excerpt"]) not in _normalize_evidence(
        source_text
    ):
        raise ValueError("repair excerpt is not grounded")
    return result


def _point_evidence(
    run: GenerationRun,
    point,
    selected_chunk_ids,
    *,
    max_chars: int = 2_000,
) -> str:
    chunk_text = _chunk_text_by_id(run)
    evidence = "\n".join(
        chunk_text[chunk_id]
        for chunk_id in point.source_chunk_ids
        if chunk_id in selected_chunk_ids
    )
    return evidence[:max_chars]


def _effective_card_template(
    settings: GenerationSettings,
    recommended_template: object,
) -> str:
    if settings.card_mode != "auto":
        return settings.card_mode
    if not isinstance(recommended_template, str):
        return "concept"
    try:
        GenerationSettings(card_mode=recommended_template)
    except ValueError:
        return "concept"
    return (
        "concept"
        if recommended_template == "auto"
        else recommended_template
    )


def _chunk_succeeded(run: GenerationRun, chunk_id: str) -> bool:
    return any(
        chunk.chunk_id == chunk_id
        and chunk.state.value == "succeeded"
        for chunk in run.chunks
    )


def _validate_selected_chunks(
    run: GenerationRun,
    chunk_ids,
) -> tuple[str, ...]:
    _require_run(run)
    if isinstance(chunk_ids, (str, bytes)):
        raise TypeError("chunk_ids must be a sequence")
    selected = tuple(chunk_ids)
    known = {chunk.chunk_id for chunk in run.chunks}
    if (
        not selected
        or len(set(selected)) != len(selected)
        or any(chunk_id not in known for chunk_id in selected)
    ):
        raise ValueError("selected chunks are invalid")
    return selected


def _require_reserved(run: GenerationRun, purpose: CallPurpose) -> None:
    _require_run(run)
    if (
        not run.call_budget.reservations
        or run.call_budget.reservations[-1].purpose is not purpose
    ):
        raise ValueError("provider call was not reserved")


def _require_plan(run: GenerationRun) -> KnowledgePlan:
    if not isinstance(run.plan, KnowledgePlan):
        raise ValueError("run has no grounded knowledge plan")
    return run.plan


def _chunk_text_by_id(run: GenerationRun) -> dict[str, str]:
    snapshot = run.document_snapshot
    try:
        values = snapshot["chunk_text_by_id"]
    except (KeyError, TypeError):
        raise ValueError("run snapshot has no chunk text") from None
    result = dict(values)
    if set(result) != {chunk.chunk_id for chunk in run.chunks} or not all(
        isinstance(text, str) and text for text in result.values()
    ):
        raise ValueError("run chunk text is incomplete")
    return result


def _require_run(run: GenerationRun) -> None:
    if not isinstance(run, GenerationRun):
        raise TypeError("run must be a GenerationRun")


def _bounded_text(value: object, max_chars: int) -> str:
    if not isinstance(value, str):
        raise ValueError("provider text is invalid")
    normalized = value.strip()
    if not normalized or len(normalized) > max_chars:
        raise ValueError("provider text is invalid")
    return normalized


def _normalize_evidence(value: str) -> str:
    return " ".join(value.casefold().split())


def _card_value(card: object, name: str):
    if isinstance(card, Mapping):
        return card.get(name)
    return getattr(card, name, None)


def _strip_json_fence(value: str) -> str:
    if value.startswith("```") and value.endswith("```"):
        lines = value.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()
    return value


__all__ = [
    "BoundedProviderGenerationAdapter",
    "build_imported_generation_run",
    "drafts_from_generation_run",
]
