# Contributing to AnkiForge AI

Thank you for helping improve AnkiForge AI.

## Issues

Before creating an issue, search existing issues for the same problem. For a
bug, include the AnkiForge AI version, Anki version, operating system, steps to
reproduce, expected behavior, and actual behavior. Remove personal study
material, API keys, authorization headers, and other secrets from screenshots
and logs.

## Development checks

Run these commands from the repository root:

```bash
python -m unittest discover -s tests
python -m compileall .
```

## Pull requests

Keep pull requests focused and explain the user-visible behavior they change.
All contributions must preserve these boundaries:

- Never save an API key.
- Never write to Anki automatically.
- Require explicit user confirmation before every write.
- Do not modify existing notes, decks, or note types unless the user has
  explicitly authorized that behavior.
- Keep UI copy simple and direct.
- Add tests for new features and behavior changes.

Confirm that the development checks pass before requesting review.
