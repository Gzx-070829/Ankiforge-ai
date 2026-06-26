"""Deterministic mock provider used by v0.1.1."""

from typing import List

from .base import AIProvider
from ..schemas import GeneratedCard


class MockAIProvider(AIProvider):
    """Local, deterministic provider with no network or API key dependency."""

    name = "mock"

    def generate_cards(self, chunk) -> List[GeneratedCard]:
        heading = chunk.heading
        snippet = " ".join(chunk.content.split())
        if len(snippet) > 160:
            snippet = snippet[:160].rstrip() + "..."

        return [
            GeneratedCard(
                card_type="basic",
                front=f"什么是「{heading}」？",
                back=snippet or "（该小节暂无正文内容，请手动编辑这张卡片）",
                extra=(
                    "此卡片由 v0.1.1 mock provider 本地生成；"
                    "当前版本不会调用真实 AI API。"
                ),
                tags=["AnkiForge", "mock"],
                source=f"{chunk.source_path} > {heading}",
            )
        ]
