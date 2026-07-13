"""Prompts for structured AI card generation."""

from typing import Optional

from ..pipeline.generation_settings import GenerationSettings
from ..pipeline.prompt_profile import build_prompt_profile

SYSTEM_PROMPT = """You are AnkiForge AI, a flashcard generation assistant.
Return only valid JSON. Do not include markdown fences or explanations.
Generate concise Basic Anki cards from the provided Markdown chunk.
Only use information present in the chunk. Do not invent facts.
Optimize cards for long-term spaced repetition review.
"""


def build_user_prompt(
    chunk,
    max_cards_per_chunk: int,
    settings: Optional[GenerationSettings] = None,
) -> str:
    """Build a provider-neutral prompt for one Markdown chunk."""
    profile = build_prompt_profile(settings)
    return (
        "Create Basic Anki flashcards from this Markdown chunk.\n"
        f"Maximum cards: {max_cards_per_chunk}\n"
        f"{profile.as_prompt_text()}\n"
        f"Heading: {chunk.heading}\n"
        f"Heading level: {chunk.level}\n"
        "Return JSON with this exact shape:\n"
        '{"cards":[{"card_type":"basic","front":"...","back":"...",'
        '"extra":"...","tags":["..."]}]}\n'
        "Rules:\n"
        "- card_type must be basic.\n"
        "- front and back must be non-empty strings.\n"
        "- Each card must test exactly one atomic knowledge point.\n"
        "- Front must be a clear single question suitable for long-term review.\n"
        "- Back must directly answer the question, without vague explanation.\n"
        "- Do not copy a whole Markdown paragraph into Back.\n"
        "- Do not write generic questions like 'Please explain the following content'.\n"
        "- Extra should include one of: a common confusion, example, limitation, or source context.\n"
        "- Tags should contain 2-5 short stable tags.\n"
        "- Do not include source; the app will add it locally.\n"
        "\nMarkdown content:\n"
        f"{chunk.content}"
    )


def response_format_payload() -> dict:
    """Return the OpenAI-compatible JSON response_format payload."""
    return {"type": "json_object"}
