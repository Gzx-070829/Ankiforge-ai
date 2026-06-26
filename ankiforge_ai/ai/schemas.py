"""
Card schema + card generation for AnkiForge AI.

`GeneratedCard` is the unit everything else (preview table, Anki writer)
operates on. `mock_generate_cards()` is a placeholder for v0.1: it produces
one simple Basic-style card per Markdown chunk, deterministically, with no
network calls.

v0.2 plan: replace `mock_generate_cards` with a real call to an AI API using
structured outputs / a JSON schema, so the model always returns a list of
dicts shaped like GeneratedCard. Keep the function signature
(chunk -> List[GeneratedCard]) the same so the UI code doesn't need to change.
"""

from dataclasses import dataclass, field
from typing import List

from ..importers.md_importer import MarkdownChunk


@dataclass
class GeneratedCard:
    card_type: str  # "basic" or "cloze"
    front: str
    back: str
    extra: str = ""
    tags: List[str] = field(default_factory=list)
    source: str = ""
    approved: bool = True


def mock_generate_cards(chunk: MarkdownChunk) -> List[GeneratedCard]:
    """
    Stand-in for the real AI call. Produces exactly one Basic card per chunk
    so you can test the full pipeline (import -> preview -> write -> style)
    before any API key is involved.
    """
    heading = chunk.heading
    snippet = " ".join(chunk.content.split())
    if len(snippet) > 160:
        snippet = snippet[:160].rstrip() + "..."

    return [
        GeneratedCard(
            card_type="basic",
            front=f"什么是「{heading}」？",
            back=snippet or "（该小节暂无正文内容，请手动编辑这张卡片）",
            extra="此卡片为 v0.1 模拟生成，正式版将调用 AI API 生成更高质量的内容。",
            tags=["AnkiForge", "mock"],
            source=f"{chunk.source_path} > {heading}",
        )
    ]
