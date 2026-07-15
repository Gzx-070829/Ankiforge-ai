# Security Policy

## Responsible disclosure

Please report suspected vulnerabilities privately through the repository's **Security** tab by choosing **Report a vulnerability**. If private vulnerability reporting is unavailable, open a minimal public issue asking the maintainer for a private contact channel. Do not include exploit details, personal study material, credentials, logs, collection data, or screenshots containing sensitive information in that issue.

Please include the affected add-on version, Anki version, operating system, a minimal reproduction, the likely impact, and any safe remediation ideas. Allow the maintainer reasonable time to investigate before public disclosure.

## Never publish credentials

Do not place an API key, password, authorization header, bearer token, cookie, or provider response containing credentials in an issue, discussion, pull request, screenshot, fixture, or log. AnkiForge AI is designed to keep the API key in the active session only and not save it to config or logs.

If a secret may have been exposed, rotate or revoke it with the provider immediately. Removing a key from a later commit does not remove it from Git history.

## Product-specific security risks

Reports are especially useful when they concern:

- **API key handling:** persistence, logging, display, packaging, or accidental disclosure.
- **Anki data safety:** access to unrelated Anki data, note/card mutation outside a confirmed batch, schema mutation, or deletion.
- **Unintended write:** bypassing review, duplicate checking, write preview, or final confirmation.
- **Provider privacy:** material sent before an explicit Generate action, sent to a different endpoint, or exposed in diagnostics.
- **File import:** unsafe archive handling, unexpected network access, full local-path exposure, or parsing files outside the selected input.
- **Package integrity:** config, backups, credentials, logs, Anki collection files, caches, tests, or personal data included in `.ankiaddon`.

## Supported security boundary

The add-on does not claim that an AI provider is private or that AI-generated cards are correct. When the user clicks Generate, the current material is sent to the configured provider under that provider's policy. File import and deterministic quality checks run locally. Writing creates new notes only after explicit review, duplicate checking, a write summary, and final confirmation.

Full automatic Undo/delete is intentionally deferred. A report showing that the add-on edits or deletes existing notes/cards without narrow, explicit authorization should be treated as high priority.

## Provider endpoint and diagnostic boundary

The active product classifies Provider endpoints lexically before saving session settings and enforces the decision again before generation. Exact official DeepSeek/OpenAI HTTPS hosts are allowed. Other public HTTPS, HTTP, localhost, private, link-local, `.local`, and bare-host endpoints require explicit confirmation for the current window; known metadata endpoints, embedded credentials, query/fragment data, unsupported schemes, and invalid/unspecified/multicast addresses are denied. HTTP confirmation warns that material and the API key may travel unencrypted. Automatic authenticated redirects are disabled.

This is risk classification, not complete SSRF protection. Classification itself performs no DNS lookup, but an approved real request necessarily uses the operating system's DNS, proxy, and network stack. Local Provider support is intentional. Saving or confirming settings does not contact the endpoint; only the user's explicit Generate action starts a request.

For an HTTP failure, the shared transport reads at most 8,192 bytes. It extracts a short detail from `error.message`, top-level `message`, or `detail` when possible, or sanitizes a bounded text response. Authorization/Bearer/API-key-like values and the exact request credential are redacted, line breaks are collapsed, and the retained detail is limited to 300 characters. Raw bodies and headers are not retained in result objects, displayed, or logged. User-facing errors prefer stable status-code messages rather than Provider body text.

## Public bug reports

Ordinary UI, installation, import, or card-quality bugs can use the issue templates. Redact API keys, personal material, complete local paths, note IDs, collection files, and provider request/response bodies first. Security reports should not use public issue templates.
