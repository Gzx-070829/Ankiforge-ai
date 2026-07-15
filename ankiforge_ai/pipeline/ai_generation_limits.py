"""Deterministic material-size guard for paid AI generation calls."""

from __future__ import annotations


MAX_AI_MATERIAL_CHARS = 50_000


class AIGenerationInputError(ValueError):
    """Safe validation error that never retains the rejected material."""

    def __init__(self, code: str, char_count: int):
        self.code = str(code)
        self.char_count = int(char_count)
        super().__init__(f"{self.code} (characters={self.char_count})")

    def __repr__(self) -> str:
        return (
            "AIGenerationInputError("
            f"code={self.code!r}, char_count={self.char_count})"
        )


def validate_ai_material_text(material_text: str) -> int:
    """Return the character count or raise a content-free validation error."""

    if not isinstance(material_text, str):
        raise AIGenerationInputError("material_not_text", 0)
    char_count = len(material_text)
    if char_count > MAX_AI_MATERIAL_CHARS:
        raise AIGenerationInputError("material_too_long", char_count)
    return char_count


def ai_material_is_too_long(material_text: object) -> bool:
    """Cheap UI preflight that does not copy or retain material content."""

    return isinstance(material_text, str) and len(material_text) > MAX_AI_MATERIAL_CHARS
