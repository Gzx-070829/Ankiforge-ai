"""Prompts for structured AI card generation."""

SYSTEM_PROMPT = """You are AnkiForge AI, a flashcard generation assistant.
Return only valid JSON. Do not include markdown fences or explanations.
Generate concise Basic Anki cards from the provided Markdown chunk.
Only use information present in the chunk. Do not invent facts.
"""


def build_user_prompt(chunk, max_cards_per_chunk: int) -> str:
    """Build a provider-neutral prompt for one Markdown chunk."""
    return (
        "Create Basic Anki flashcards from this Markdown chunk.\n"
        f"Maximum cards: {max_cards_per_chunk}\n"
        f"Heading: {chunk.heading}\n"
        f"Heading level: {chunk.level}\n"
        "Return JSON with this exact shape:\n"
        '{"cards":[{"card_type":"basic","front":"...","back":"...",'
        '"extra":"...","tags":["..."]}]}\n'
        "Rules:\n"
        "- card_type must be basic.\n"
        "- front and back must be non-empty strings.\n"
        "- extra may be an empty string.\n"
        "- tags must be an array of short tag strings.\n"
        "- Do not include source; the app will add it locally.\n"
        "\nMarkdown content:\n"
        f"{chunk.content}"
    )


def response_format_payload() -> dict:
    """Return the OpenAI-compatible JSON response_format payload."""
    return {"type": "json_object"}
