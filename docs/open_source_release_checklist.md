# Open Source Release Checklist

Complete this checklist immediately before publishing a release:

- [ ] `python -m unittest discover -s tests` passed
- [ ] `python -m compileall .` passed
- [ ] `git diff --check` passed
- [ ] `git status` is clean
- [ ] `config.json` is not tracked
- [ ] Anki collection files are not tracked
- [ ] Backups are not tracked
- [ ] No real API key is present
- [ ] No personal Anki data is present
- [ ] `LICENSE` is present
- [ ] `README.md` is present
- [ ] `SECURITY.md` is present
- [ ] `PRIVACY.md` is present
- [ ] `CONTRIBUTING.md` is present
- [ ] Repository visibility is intentionally public
