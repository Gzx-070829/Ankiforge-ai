# PR25 Runtime Safety Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the remaining v0.13 release blockers around responsive AI generation, paid-request bounds, endpoint consent, safe diagnostics, and Anki HTML/duplicate consistency without changing the product workflow.

**Architecture:** Keep the v0.13 UI and write gates intact. Add small pure-Python policy/normalization modules, integrate them at the actual network and writer boundaries, and put only Provider generation—not Anki collection mutation—behind Anki taskman using immutable snapshots and stale-result rejection.

**Tech Stack:** Python 3 standard library, Anki `mw.taskman`, Qt through `aqt.qt`, `unittest`, deterministic ZIP packaging.

## Global Constraints

- Branch: `v0.13.1-pr25-runtime-safety-hardening` from current `main`.
- `MAX_AI_MATERIAL_CHARS = 50000`; no truncation and no Provider call on rejection.
- API keys remain session-only and never enter config, logs, Anki fields, docs output, or the package.
- Endpoint handling is risk classification plus explicit confirmation, not a complete SSRF claim.
- No automatic retry and no true network-request cancellation.
- No ordinary background-thread Anki collection writes; existing duplicate/final-confirm/mapping gates remain.
- No main merge, public/main push, AnkiWeb upload, tag, or GitHub Release.

---

### Task 1: Bound AI material and classify endpoints

**Files:**
- Create: `ankiforge_ai/pipeline/ai_generation_limits.py`
- Create: `ankiforge_ai/pipeline/provider_endpoint_safety.py`
- Modify: `ankiforge_ai/ui/ai_settings_dialog.py`
- Modify: `ankiforge_ai/ui/beginner_ai_card_drafts.py`
- Test: `tests/test_pr25_material_limits.py`
- Test: `tests/test_provider_endpoint_safety.py`

**Interfaces:**
- Produces: `validate_ai_material_text(text)`, `assess_provider_endpoint(url, official_hosts=...)`, `endpoint_confirmation_key(url)`, `endpoint_is_authorized(...)`.
- Consumes: frozen `BeginnerAIProviderRuntimeSettings` and existing generation payload builder.

- [x] **Step 1: Write failing pure-policy and boundary tests**

```python
def test_core_blocks_before_transport(self):
    result = BeginnerAICardDraftGenerator(transport).generate(settings, over_limit)
    self.assertEqual(result.error_code.value, "material_too_long")
    self.assertEqual(transport.calls, [])

def test_metadata_is_denied(self):
    decision = assess_provider_endpoint(
        "http://169.254.169.254/latest/meta-data",
        official_hosts={"api.deepseek.com"},
    )
    self.assertEqual(decision.kind, "deny")
```

- [x] **Step 2: Verify the new imports fail before implementation**

Run: `python -m unittest tests.test_pr25_material_limits tests.test_provider_endpoint_safety`

Expected: import failures for the missing policy modules.

- [x] **Step 3: Implement lexical allow/confirm/deny and dual material guards**

```python
MAX_AI_MATERIAL_CHARS = 50_000

def validate_ai_material_text(material_text: str) -> int:
    count = len(material_text)
    if count > MAX_AI_MATERIAL_CHARS:
        raise AIGenerationInputError("material_too_long", count)
    return count
```

- [x] **Step 4: Re-run the focused tests**

Run: `python -m unittest tests.test_pr25_material_limits tests.test_provider_endpoint_safety tests.test_ai_settings_endpoint_confirmation`

Expected: all tests pass without DNS or network access.

### Task 2: Sanitize Provider HTTP failures

**Files:**
- Create: `ankiforge_ai/pipeline/http_error_sanitization.py`
- Modify: `ankiforge_ai/pipeline/openai_compatible_http_transport.py`
- Modify: `ankiforge_ai/pipeline/openai_compatible_provider.py`
- Test: `tests/test_http_error_sanitization.py`
- Test: `tests/test_pr25_http_diagnostics.py`

**Interfaces:**
- Produces: bounded `sanitize_provider_error_body()` and `OpenAICompatibleTransportResponse.error_detail` excluded from repr.
- Consumes: Authorization values only as exact redaction inputs; no raw error body is retained.

- [x] **Step 1: Add failing 8,192-byte, redaction, mapping, and repr tests**

```python
result = transport.post_json(url, {"Authorization": f"Bearer {secret}"}, {}, 5)
self.assertEqual(stream.requested_sizes, [8192])
self.assertNotIn(secret, result.error_detail)
self.assertFalse(hasattr(result, "raw_body"))
```

- [x] **Step 2: Implement bounded extraction and disable redirects**

```python
class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
```

- [x] **Step 3: Map status codes to stable bilingual UI keys**

Run: `python -m unittest tests.test_http_error_sanitization tests.test_pr25_http_diagnostics tests.test_openai_compatible_http_transport`

Expected: all tests pass; no Provider body or key appears in repr.

### Task 3: Render safe plain-text Anki fields and share duplicate semantics

**Files:**
- Create: `ankiforge_ai/anki_writer/field_content.py`
- Modify: `ankiforge_ai/anki_writer/minimal_write.py`
- Modify: `ankiforge_ai/ui/read_only_duplicate_check.py`
- Test: `tests/test_anki_field_content.py`
- Test: `tests/test_beginner_read_only_duplicate_check.py`

**Interfaces:**
- Produces: `render_plain_text_anki_html`, `plain_text_from_anki_html`, and canonical duplicate-key helpers.
- Consumes: raw plain-text session/write-command fields and existing Anki HTML fields.

- [x] **Step 1: Write escaping, newline, Source, entity, and duplicate regression tests**

```python
rendered = render_plain_text_anki_html("<tag>\r\nA & B")
self.assertEqual(rendered, "&lt;tag&gt;<br>A &amp; B")
self.assertEqual(
    duplicate_key_from_plain_text("<tag>"),
    duplicate_key_from_anki_html("&lt;tag&gt;"),
)
```

- [x] **Step 2: Render exactly once at note assignment and precompute existing keys**

```python
note[command.front_field] = render_plain_text_anki_html(card.front)
note[command.back_field] = render_plain_text_anki_html(card.back)
```

- [x] **Step 3: Confirm hard gates and existing duplicate policy remain unchanged**

Run: `python -m unittest tests.test_anki_field_content tests.test_beginner_read_only_duplicate_check tests.test_beginner_minimal_real_anki_write tests.test_v1_core_ui_contract`

Expected: safe round trips pass; Front-or-Back matching and duplicate/final-confirm gates remain.

### Task 4: Move generation to taskman with stale-callback safety

**Files:**
- Create: `ankiforge_ai/ui/generation_task_controller.py`
- Modify: `ankiforge_ai/ui/card_maker_panel.py`
- Modify: `ankiforge_ai/ui/main_dialog.py`
- Test: `tests/test_generation_task_controller.py`
- Test: `tests/test_async_card_generation.py`

**Interfaces:**
- Produces: frozen `GenerationRequestSnapshot`, monotonic request IDs, safe `GenerationTaskCompletion`, `invalidate()`, and `close()`.
- Consumes: `mw.taskman.run_in_background` with Future callback semantics and `uses_collection=False`.

- [x] **Step 1: Write a controllable FakeTaskman and reverse-order tests**

```python
def run_in_background(self, task, on_done, *, uses_collection=True):
    future = Future()
    self.pending.append((task, on_done, future, uses_collection))
    return future
```

- [x] **Step 2: Submit only frozen values and ignore stale/closed completions**

```python
if not self._alive or completion.request_id != self._current_request_id:
    return
```

- [x] **Step 3: Make dialog teardown idempotent and panel callback weak**

Run: `python -m unittest tests.test_generation_task_controller tests.test_async_card_generation tests.test_v1_core_ui_contract`

Expected: background submission, reverse-order completion, close, snapshot, and safe exception tests pass.

### Task 5: Remove legacy credential persistence and document boundaries

**Files:**
- Modify: `ankiforge_ai/config_loader.py`
- Modify: `ankiforge_ai/config.example.json`
- Modify: `ankiforge_ai/config.md`
- Create: `docs/pr25_runtime_safety_hardening.md`
- Modify: `docs/manual_anki_acceptance.md`
- Modify: `docs/ai_settings_and_privacy.md`
- Modify: `docs/write_safety_and_traceability.md`
- Modify: `docs/future_roadmap.md`
- Modify: `docs/troubleshooting.md`
- Test: `tests/test_config_loader.py`
- Test: `tests/test_pr25_docs.py`

**Interfaces:**
- Produces: legacy config that always returns an empty runtime key and omits `api_key` on save; auditable release boundaries and 13-item manual acceptance.
- Consumes: existing non-secret legacy preferences only.

- [x] **Step 1: Test that load ignores and save discards a legacy key**

```python
save_config({"api_key": secret, "model": "model-b"}, path)
self.assertNotIn("api_key", json.load(open(path, encoding="utf-8")))
```

- [x] **Step 2: Write the security decision record and manual checklist**

- [x] **Step 3: Run config and documentation contracts**

Run: `python -m unittest tests.test_config_loader tests.test_pr25_docs`

Expected: key persistence is impossible through the legacy loader and every required limitation is documented.

### Task 6: Full verification, deterministic package, commit, and branch-only push

**Files:**
- Build output only: `dist/ankiforge_ai.ankiaddon` (ignored by Git)

**Interfaces:**
- Consumes: complete source tree and `scripts/build_ankiaddon.py`.
- Produces: one audited deterministic candidate package and one PR25 branch commit.

- [ ] **Step 1: Run the complete validation suite**

Run: `python -m unittest discover`

Expected: all tests pass.

Run: `python -m compileall .`

Expected: exit 0.

Run: `git diff --check`

Expected: no output and exit 0.

- [ ] **Step 2: Build twice and compare SHA-256**

Run: `python scripts/build_ankiaddon.py` twice, recording file count and byte size after each run.

Run: `Get-FileHash dist/ankiforge_ai.ankiaddon -Algorithm SHA256`

Expected: identical hashes and build validation passed both times.

- [ ] **Step 3: Inspect package and repository for forbidden data**

Check ZIP members and tracked files for config, backups, tests/docs, cache, logs, `.anki2`, `.apkg`, and credential patterns. Confirm package members equal the runtime source build plan.

Expected: forbidden files 0, real secrets 0, Anki user data 0, source/package consistency true.

- [ ] **Step 4: Commit once and push only the PR25 branch**

Run: `git commit -m "Fix runtime safety blockers before v0.13 release"`

Run: `git push public v0.13.1-pr25-runtime-safety-hardening`

Expected: clean worktree; `public/main` unchanged; no tag, Release, or AnkiWeb update.
