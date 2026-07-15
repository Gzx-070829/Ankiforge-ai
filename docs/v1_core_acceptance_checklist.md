# v1-Core Acceptance Checklist

> Historical v0.12 checklist. Use the current [v1 Candidate Acceptance Checklist](v1_candidate_acceptance_checklist.md) and [Manual Anki Acceptance](manual_anki_acceptance.md) for the product-grade candidate.

## Automated gates

- [ ] `python -m unittest discover` passes
- [ ] `python -m compileall .` passes
- [ ] `git diff --check` passes
- [ ] two package builds have the same SHA-256
- [ ] forbidden package files: 0
- [ ] no config, backup, secret, log, cache, tests, docs, or Anki user data in the package

## Manual product acceptance

- [ ] Open the add-on in a separate/test Anki profile or test deck
- [ ] Confirm card mode is visible and other generation settings start collapsed
- [ ] Confirm Provider, Model, and API key remain readable and uncluttered
- [ ] Confirm no provider request occurs before clicking Generate Cards
- [ ] Generate in all four modes and compare prompt behavior
- [ ] Confirm every generated card starts unreviewed
- [ ] Confirm warning cards can be explicitly kept
- [ ] Edit a card and confirm quality, duplicate state, and write summary refresh
- [ ] Confirm blocking cards cannot be kept or written
- [ ] Confirm “discard blocked cards” changes only the current candidate list
- [ ] Map an existing test deck/note type/fields without schema changes
- [ ] Confirm possible duplicates are skipped
- [ ] Confirm write summary shows target, mapping, source, counts, duplicate policy, and tags
- [ ] Cancel final confirmation and verify no notes are created
- [ ] Confirm one test write and inspect source label/tags in Anki
- [ ] Confirm existing notes, decks, and note types remain unchanged
- [ ] Close the window and confirm the API key is not retained
- [ ] Confirm PDF remains fallback guidance and no OCR is claimed
- [ ] Confirm there is no Undo/delete action in v0.12
