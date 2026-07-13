# Review Workbench

Generated cards start in an unreviewed state. AnkiForge AI does not treat generation as approval.

For every card, the user can:

- inspect front, back, and the source excerpt;
- read the local quality score, warnings, and suggestions;
- edit front and back;
- explicitly keep or discard the card.

Editing immediately recalculates local quality and clears stale duplicate checks and write summaries. A blocking card cannot be kept for writing, but it can be edited or discarded. A warning card may be kept after explicit user review.

The “discard blocked cards” action removes only blocking candidates from the current in-memory session. It never deletes Anki notes or cards.

Writing remains unavailable until the current candidates have explicit review decisions, target fields are mapped, duplicate checking succeeds, and the final confirmation is accepted.
