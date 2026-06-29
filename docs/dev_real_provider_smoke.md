# Developer Real Provider Smoke Harness

## Safety Notice

This is a **developer-only manual verification tool**. It is not a normal-user
entry point, a provider-settings feature, or an Anki plugin UI capability.

- A real run sends the explicitly supplied preview to the configured provider.
- It does not write to Anki or generate a final Anki card.
- It does not run as part of the automated test suite.
- Never commit an API key, paste one into source code, or add one to a fixture.
- Real API privacy, availability, and cost risks remain the developer's
  responsibility.

The v0.6 harness constructs `UserProviderProfile`, `ProviderSelection`,
`ProviderConsentRecord`, `ProviderDryRunRequest`, and
`ProviderDryRunExecutionInput`. It then uses the PR7b-1 executor through the
PR7a consent boundary and stops at `ProviderDryRunExecutionResult` for
KnowledgePoint extraction.

It does not generate `CardCandidate` or `HumanReview` values, modify
`self.cards`, call a writer, or create an Anki note. Any future product path
must still pass through Human Selection, Quality Gate, Human Review, Write
Eligibility, duplicate checks, and final human confirmation.

## Temporary API Key

The harness accepts a key only through the temporary environment variable
`ANKIFORGE_DEV_API_KEY`. It does not accept a command-line key.

The environment variable and the harness's private one-shot memory adapter are
not a formal key-storage solution. They do not encrypt the key. Python strings
cannot be reliably cleared from memory, and debuggers or crash dumps may still
observe runtime values. The harness minimizes references but cannot guarantee
memory erasure.

In PowerShell, use a hidden prompt for the current process:

```powershell
$secureKey = Read-Host "Temporary API key" -AsSecureString
$keyPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
try {
    $env:ANKIFORGE_DEV_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPtr)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPtr)
}
```

This does not modify Anki configuration or legacy `config.json`, and it does
not migrate an existing key.

## Run Manually

Run from the repository root and explicitly provide every provider setting:

```powershell
python -m scripts.dev_real_provider_smoke `
  --provider-id "manual-provider" `
  --provider-name "Manual Provider" `
  --model-name "manual-model" `
  --base-url "https://provider.example/v1" `
  --confirm-send
```

`--confirm-send` is mandatory. Without it, the harness does not read the API
key, create a transport or executor, or call a provider.

The built-in text is short and non-private. `--text` replaces it with one
explicit source preview. The preview is limited to 500 characters by the v0.6
request contract. Longer input fails safely and is never truncated or sent.
File, clipboard, UI, Anki deck, Obsidian, and full-source input are deliberately
unsupported.

After confirmation and key validation, the dev-only harness explicitly creates
the real HTTP transport. Automatic tests always inject a fake transport and
block network access.

A successful run exits with code `0`; a safely represented provider failure
exits with code `1`; missing confirmation, missing key, or invalid input exits
with code `2`.

Output is limited to provider/model display data, KnowledgePoint extraction
status, count, fixed safe error-display fields, write-disabled status, and
no provider-generated content. It never prints knowledge-point titles, the
key, Authorization header, source preview, prompt, raw JSON, response body,
stack trace, or original exception message.

## Clean Up

Remove the temporary environment variable immediately after the manual run:

```powershell
Remove-Item Env:ANKIFORGE_DEV_API_KEY
```

Do not add raw provider logging while troubleshooting. Use only the fixed safe
error display.

## Not Implemented

This harness does not provide ordinary-user provider UI, formal key storage,
provider presets, retry/backoff, token or cost accounting, card generation,
review workflow integration, or Anki writing. A structured SDK/HTTP exception
classifier is deferred to a separate future PR, such as PR7d or v0.7; PR7b-2
and PR7c do not implement one.
