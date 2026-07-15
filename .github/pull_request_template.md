## Summary

Describe the user problem, the visible behavior, and why this scope is appropriate.

## Changes

-

## Tests and verification

- [ ] `python -m unittest discover`
- [ ] `python -m compileall .`
- [ ] `git diff --check`
- [ ] Relevant deterministic fixtures/benchmarks updated
- [ ] Real-Anki manual acceptance completed or explicitly deferred
- [ ] Package built twice and SHA-256 compared, if packaging is affected

## Safety and privacy checklist

- [ ] No real API key, credential, token, cookie, provider payload, or personal path is included
- [ ] No Anki user data, collection file, backup, config, log, or secret is included
- [ ] API keys remain session-only and are not saved or logged
- [ ] No automatic AI calls were added
- [ ] No automatic Anki writes or deletes were added
- [ ] Generated cards still require explicit review
- [ ] Duplicate check remains a hard gate
- [ ] Final confirmation remains a hard gate
- [ ] Existing notes/cards, decks, note types, and fields are not automatically mutated
- [ ] User messages do not expose traceback, raw IDs, full paths, internal quality IDs, or raw scores

## Documentation and i18n

- [ ] Chinese and English user-facing copy are aligned
- [ ] Canonical guides were updated without duplicating policy text
- [ ] Claims distinguish implemented behavior, manual acceptance, and roadmap items
- [ ] Claims do not imply review replacement, PDF text extraction, control over third-party data handling, or unattended operation

## Manual acceptance / screenshots

List the Anki version, OS, test profile/deck, scenarios, and redacted screenshot paths. Never include credentials or private material.

## Deferred items and risks

Describe any Provider, review, duplicate, mapping, write, source/tag, last-write, Undo, packaging, or migration risk that still needs human review.
