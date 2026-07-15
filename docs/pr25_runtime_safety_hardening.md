# PR25 Runtime Safety Hardening

PR25 is a narrow pre-release hardening pass for the v0.13 Create → Review → Write workflow. It does not add a new feature surface, redesign the UI, persist credentials, or change the Anki write approval gates.

## 1. Scope

This change:

- moves the explicitly requested AI generation call to Anki's background task manager;
- rejects stale or late generation callbacks by request identity and panel lifecycle;
- enforces a 50,000-character material limit before task submission and again inside the generation core;
- classifies provider endpoints as `allow`, `confirm`, or `deny` and records confirmation only for the current window;
- disables automatic HTTP redirects for authenticated provider requests;
- reads at most 8,192 bytes of an HTTP error body and retains only a redacted, one-line, bounded diagnostic;
- renders card fields as safe plain-text Anki HTML at the writer boundary; and
- gives write rendering and duplicate comparison one shared normalization module.

It does not implement automatic retries, true request cancellation, advanced HTML/Markdown rendering, a general Provider rewrite, or background collection writes.

## 2. What remains valid from the external v0.11 review

Several findings were still relevant after the v0.13 product work:

- the active Generate handler could perform synchronous HTTP on the Qt main thread;
- there was no explicit paid-request material-size guard;
- custom endpoints needed an explicit trust decision because the session API key is sent to that endpoint;
- provider error bodies needed bounded, redacted handling instead of either raw display or total loss of useful status context;
- raw AI/user text needed an explicit policy at Anki's HTML field boundary; and
- duplicate comparison needed to understand the escaped HTML and line breaks produced by the writer.

The active v0.13 UI already required an explicit Generate click, review decisions, a current duplicate check, complete mapping, and final confirmation. PR25 preserves those controls.

## 3. Outdated or intentionally unadopted findings

- The v0.11 UI structure and screenshots no longer describe the v0.13 linear workbench.
- Qt `deleteLater()` is the normal safe lifecycle mechanism here; PR25 does not replace it.
- The existing Anki menu action registration is retained.
- Legacy Provider modules are not deleted or fully unified in this narrow pass. Their configuration loader now ignores and never writes `api_key`, and their HTTP transport uses the shared bounded/no-redirect behavior.
- Automatic retry is not enabled because it can repeat a paid request and can create ambiguous duplicate generations.
- Anki collection writes are not moved to an ordinary Python worker thread. Collection access must respect Anki's thread and operation model; a future `CollectionOp` migration requires real-Anki compatibility testing.
- No “reset and write the same batch again,” automatic deletion, or broad source editing action is added.

## 4. Why the API key is not persisted

The API key authorizes billable access and may expose private study material to the configured service. The active product keeps it only in the current dialog/panel/request lifetime. Closing or discarding the window clears product references and endpoint confirmations. The legacy JSON loader ignores an `api_key` found on disk, and its save path omits the field.

This is a best-effort in-process lifecycle, not a claim that Python or the operating system can instantly erase every memory copy while an HTTP request is still running. Keys must never enter Git, config, Anki fields, logs, error text, screenshots, or the package.

## 5. Endpoint policy and local providers

PR25 does **not** claim complete SSRF prevention. AnkiForge AI is a desktop add-on and intentionally supports local and private-network providers.

The policy is endpoint risk classification plus explicit confirmation:

- exact official HTTPS origins for DeepSeek and OpenAI are allowed;
- custom public HTTPS, HTTP, localhost, loopback, private, link-local, `.local`, and bare-host endpoints require confirmation;
- embedded credentials, query strings, fragments, unsupported schemes, missing/unspecified/multicast addresses, and known metadata endpoints are denied.

Classification is lexical and performs no DNS lookup. The warning displays only normalized scheme, host, and non-default port. Confirmation is represented by a hash of that normalized origin, remains in memory for the current session, and must match again at the actual generation boundary. Changing scheme, host, or port requires confirmation again. Authenticated HTTP redirects are not followed automatically.

An HTTP confirmation additionally warns that the study material and API key may travel unencrypted. Classification itself does not resolve DNS; an approved real request still uses the operating system's DNS, proxy, and network stack. Saving or confirming settings never contacts the endpoint.

Local/private endpoints are not permanently banned because users may deliberately run trusted local OpenAI-compatible services. Confirmation makes that trust decision visible without pretending the add-on can prove the remote service's identity or behavior.

## 6. Why there is no default retry

A timeout or ambiguous network failure does not prove that the Provider did no work. Retrying automatically could incur a second charge, create a second output, or make the UI state unclear. PR25 reports a short stable error and leaves retry as another explicit Generate action by the user.

## 7. Generation and Anki write thread models

AI generation uses `mw.taskman.run_in_background(..., uses_collection=False)`. The background callable receives only an immutable request snapshot and does not read widgets, mutable session state, or the Anki collection. Its Future completion callback is delivered through Anki's task manager and then checked before any UI/session update.

Anki writing remains on the existing guarded collection path. PR25 does not put collection writes on a generic background thread. Existing hard gates remain: kept non-blocking cards, valid target and mapping, current duplicate check, write summary, and final confirmation. The existing write state prevents repeated activation while a write is in progress.

## 8. Stale callback safety

Each submitted request receives a monotonically increasing ID. The frozen snapshot contains the material, provider/model/base URL/timeout, generation settings (mode, count, answer length, output language), and the matching in-memory endpoint confirmation key. The background task never rereads the UI.

Starting a newer request, changing upstream material/settings, discarding the session, or closing the panel invalidates the current request ID. A completion updates state only when its ID is still current and the controller/panel/session are alive. Old successes and old failures are silent no-ops. The completion closure holds only a weak panel reference.

PR25 implements responsive UI and stale-callback safety, **not true cancellation**. A urllib request that is already running may finish after the window closes; its result is ignored safely.

## 9. Plain-text fields and duplicate consistency

Session drafts, review edits, and write commands remain raw plain text. At the one writer boundary, text newlines are normalized, HTML metacharacters are escaped once, and newlines become `<br>`. Front, Back, and Source all use the same renderer. Raw `<script>`, `<img onerror>`, and other markup therefore appear as inert text instead of executable HTML.

Duplicate checking uses two explicit paths from the same helper module:

- candidate raw text → canonical plain-text key;
- existing Anki HTML → inert canonical plain text → the same key.

This lets raw `<tag>` match a previously written `&lt;tag&gt;`, and raw newlines match stored `<br>`, without sending already-rendered content through the writer again. It avoids double escaping by architecture rather than guessing whether an input entity was previously escaped. The existing case-folded, collapsed-whitespace, Front-or-Back duplicate rule is unchanged.

PR25 defaults to safe **plain-text** Anki fields. Advanced trusted HTML or Markdown rendering requires a separate allowlist/parser design and is deferred.

## 10. Manual Anki acceptance

Automatic tests cannot prove Qt responsiveness, wrapper lifetime behavior, Provider interoperability, or real collection rendering. Before merge or public release, complete the PR25 section in [manual_anki_acceptance.md](manual_anki_acceptance.md) using a disposable profile/test deck and a revocable test credential.

Merge and release must stop for any UI freeze, stale result overwrite, late-callback crash, missing endpoint confirmation, credential/raw-body disclosure, raw HTML execution, duplicate mismatch after safe writing, bypassed write gate, or unintended collection mutation.
