# Contributing to AnkiForge AI

Thank you for helping build a trustworthy local Anki card workbench. By participating, follow the [Code of Conduct](CODE_OF_CONDUCT.md) and preserve the safety boundaries below.

## Start with the right channel

- **Bug reports:** search existing issues, then use the bug template with the AnkiForge AI version, Anki version, operating system, reproduction steps, expected/actual behavior, and redacted screenshots.
- **Card-quality feedback:** use the quality template with a short synthetic or anonymized source, mode/template, candidate, desired outcome, and rule behavior.
- **Feature requests:** describe the learning problem and safety impact, not only a preferred implementation.
- **Security reports:** follow [SECURITY.md](SECURITY.md) and report privately. Never disclose a vulnerability or credential in a public issue.

## Code contributions

Keep changes focused, preserve public interfaces where practical, and add tests before implementation for new behavior. Pure-Python pipeline logic should remain deterministic and testable without Anki, a provider, or network access. UI code should expose short user messages rather than tracebacks, internal IDs, or raw quality scores.

Do not introduce automatic AI calls, automatic Anki writes, note/card deletion, note-type mutation, field creation, unrelated collection reads, background networking, or credential persistence.

## Documentation contributions

Use plain language, keep Chinese and English meaning aligned, and link to a single canonical guide rather than copying the same policy into several files. Documentation must distinguish implemented behavior, manual acceptance requirements, and future roadmap items.

Describe capabilities and limitations literally. Do not imply that generation replaces review, that PDF text is extracted, that third-party data handling is controlled by the add-on, or that the workflow can run unattended. Quality feedback is assistive; the user remains responsible for final cards.

## Card-quality fixture contributions

Fixtures should be small, deterministic, and based on public, synthetic, or clearly redistributable material. Include a recommended mode, expected good/bad patterns, a reasonable card-count range, notes, and representative mock candidates where appropriate.

There must be no real API keys and no user Anki data in tests, fixtures, snapshots, screenshots, or documentation. Also remove personal paths, private notes, collection exports, provider logs, authorization headers, and identifying information. Use obvious fake values such as `fake-test-key` where a credential-shaped input is required.

## Development checks

Run from the repository root:

```bash
python -m unittest discover
python -m compileall .
python scripts/build_ankiaddon.py
git diff --check
```

When packaging changes, build twice and compare SHA-256. Inspect the archive for config, backup, secrets, Anki data, caches, logs, tests, and docs.

## Pull requests

Explain:

1. the user problem and visible behavior;
2. the safety and privacy impact;
3. tests and manual acceptance performed;
4. deferred items or remaining risk;
5. documentation or fixture changes.

Every pull request must preserve these gates:

- API keys remain session-only and are never saved or logged.
- AI is called only after an explicit user action.
- Generated cards require review.
- Anki writes require duplicate checking, a preview, and final confirmation.
- Existing notes/cards, decks, note types, and fields are not automatically modified or deleted.
- New functionality includes tests and bilingual user-facing copy where applicable.

Maintainers may request a smaller fixture, stronger redaction, additional tests, or real-Anki manual acceptance before merge.
