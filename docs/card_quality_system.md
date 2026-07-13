# Card Quality System

AnkiForge AI v0.12 evaluates generated cards locally before they can enter the write flow. The validator is deterministic Python: it does not call AI, access the network, read Anki, or change the card.

## What it checks

- Empty front or back: blocking
- Very short or generic front
- Answer length relative to the selected setting
- Multiple questions or likely multiple knowledge points
- Filler such as “according to the material” / “根据材料可知”
- Markdown residue
- Duplicate-like candidates within the current generated batch

Each card receives a score from 0.0 to 1.0, warning identifiers, short suggestions, and an `info`, `warning`, or `blocking` severity. Empty front/back is blocking. Other rules are warnings so the user remains in control.

This system is an assistant, not a correctness guarantee. It uses simple explainable heuristics and cannot verify every fact, ambiguity, or pedagogical choice. Always review AI-generated content before writing it to Anki.

## Card modes

- `concept`: concept understanding, causes, differences, and significance
- `definition`: terms, definitions, key traits, and essential examples
- `exam`: exam-style questions and concise scoring points
- `quick_review`: short question, short answer, one fact per card

Changing mode, card count, answer length, or output language invalidates older generated results. API keys are not part of generation settings and remain session-only.
