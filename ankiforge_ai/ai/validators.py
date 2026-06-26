"""Validation and conversion for structured AI card JSON."""

import json
from typing import List

from .providers.mock_provider import format_source_display
from .schemas import GeneratedCard


class CardValidationError(ValueError):
    """Raised when an AI response is valid JSON but not valid card data."""


def parse_cards_json(text: str) -> dict:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        raise CardValidationError(f"AI 返回的 JSON 无法解析: {e}") from e

    if not isinstance(parsed, dict):
        raise CardValidationError("AI 返回的 JSON 顶层必须是 object。")
    return parsed


def validate_cards_payload(payload: dict, chunk, max_cards_per_chunk: int) -> List[GeneratedCard]:
    cards = payload.get("cards")
    if not isinstance(cards, list):
        raise CardValidationError("AI 返回 JSON 必须包含 cards 数组。")
    if len(cards) > max_cards_per_chunk:
        cards = cards[:max_cards_per_chunk]

    generated = []
    for index, card in enumerate(cards, start=1):
        if not isinstance(card, dict):
            raise CardValidationError(f"第 {index} 张卡片必须是 object。")

        card_type = _required_text(card.get("card_type"), f"第 {index} 张卡片 card_type")
        if card_type != "basic":
            raise CardValidationError("v0.2 只支持 basic card。")

        front = _required_text(card.get("front"), f"第 {index} 张卡片 front")
        back = _required_text(card.get("back"), f"第 {index} 张卡片 back")
        extra = _optional_text(card.get("extra"))
        tags = _normalize_tags(card.get("tags"))

        generated.append(
            GeneratedCard(
                card_type="basic",
                front=front,
                back=back,
                extra=extra,
                tags=tags,
                source=format_source_display(chunk.source_path, chunk.heading),
            )
        )

    if not generated:
        raise CardValidationError("AI 没有返回任何有效卡片。")
    return generated


def cards_from_json_text(text: str, chunk, max_cards_per_chunk: int) -> List[GeneratedCard]:
    return validate_cards_payload(parse_cards_json(text), chunk, max_cards_per_chunk)


def _required_text(value, label: str) -> str:
    text = _optional_text(value)
    if not text:
        raise CardValidationError(f"{label} 不能为空。")
    return text


def _optional_text(value) -> str:
    return str(value or "").strip()


def _normalize_tags(value) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise CardValidationError("tags 必须是数组。")

    tags = []
    seen = set()
    for tag in value:
        text = _optional_text(tag)
        if not text or text in seen:
            continue
        seen.add(text)
        tags.append(text)
    return tags
