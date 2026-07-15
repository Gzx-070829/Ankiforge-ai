"""Maintainable prompt guidance derived from generation settings."""

from dataclasses import dataclass
from typing import Optional

from .card_templates import default_template_for_mode, get_card_template
from .generation_settings import (
    GenerationSettings,
    card_limit_for_settings,
    coerce_generation_settings,
    get_card_mode_profile,
)


@dataclass(frozen=True, repr=False)
class PromptProfile:
    mode_id: str
    template_id: str
    card_limit: int
    guidance: str
    template_guidance: str
    answer_guidance: str
    language_guidance: str
    quality_rules: tuple[str, ...]

    def __repr__(self) -> str:
        return (
            "PromptProfile("
            f"mode_id={self.mode_id!r}, template_id={self.template_id!r}, "
            f"card_limit={self.card_limit}, "
            f"quality_rule_count={len(self.quality_rules)})"
        )

    def as_prompt_text(self) -> str:
        rules = "\n".join(f"- {rule}" for rule in self.quality_rules)
        return (
            f"Card mode: {self.mode_id}\n"
            f"Card template: {self.template_id}\n"
            f"Mode guidance: {self.guidance}\n"
            f"Template guidance: {self.template_guidance}\n"
            f"Answer guidance: {self.answer_guidance}\n"
            f"Language guidance: {self.language_guidance}\n"
            f"Quality rules:\n{rules}"
        )


def build_prompt_profile(
    settings: Optional[GenerationSettings] = None,
    template_id: Optional[str] = None,
) -> PromptProfile:
    resolved = coerce_generation_settings(settings)
    mode = get_card_mode_profile(resolved.card_mode)
    template = (
        default_template_for_mode(resolved.card_mode)
        if template_id is None
        else get_card_template(template_id)
    )
    if template.mode_id != resolved.card_mode:
        raise ValueError(
            f"template {template.template_id!r} is not compatible with "
            f"card mode {resolved.card_mode!r}."
        )
    answer_guidance = (
        "Keep the answer short and direct, normally one or two sentences."
        if resolved.answer_length == "short"
        else "Keep the answer concise but allow a few short sentences or bullet points."
    )
    language_guidance = {
        "auto": "Preserve the material's language unless a faithful answer requires otherwise.",
        "zh": "Write the cards in Simplified Chinese.",
        "en": "Write the cards in English.",
    }[resolved.language]
    return PromptProfile(
        mode_id=resolved.card_mode,
        template_id=template.template_id,
        card_limit=card_limit_for_settings(resolved),
        guidance=mode.prompt_guidance,
        template_guidance=(
            f"Front: {template.front_guidance} "
            f"Back: {template.back_guidance} "
            f"Ideal front shape: {template.ideal_front_shape}. "
            f"Ideal back shape: {template.ideal_back_shape}."
        ),
        answer_guidance=answer_guidance,
        language_guidance=language_guidance,
        quality_rules=(
            "Test exactly one knowledge point per card.",
            "Make the front specific and directly reviewable.",
            "Keep the back concise and answer the front directly.",
            "Do not combine multiple questions or knowledge points in one card.",
            "Do not use filler such as 'according to the material'.",
            "Do not invent facts beyond the supplied material.",
            "When uncertain, generate fewer and more conservative cards.",
            "Do not leave markdown table residue or formatting artifacts.",
            "Do not output prompt text, template instructions, or explanations.",
        ),
    )
