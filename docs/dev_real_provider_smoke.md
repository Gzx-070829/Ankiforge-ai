# Developer Real Provider Smoke Harness

## Safety Notice

This is a **developer-only manual verification tool**. It is not a normal user
entry point and is not an Anki plugin UI feature.

- A real run sends the supplied text to the configured provider.
- It does not write to Anki or generate a final Anki card.
- It does not run as part of the automated test suite.
- Never commit an API key, paste one into source code, or add one to a fixture.
- Real API use, privacy, availability, and cost risks remain the developer's
  responsibility.

The harness stops at `KnowledgePointExtractionOutcome` and displays a safe
`ProviderDryRunSummary`. Human Selection, Quality Gate, Human Review, write
eligibility, and Anki writing are not performed.

## Set a Temporary API Key

The key is accepted only through the temporary environment variable
`ANKIFORGE_DEV_API_KEY`. Do not pass a key as a command-line argument.

In PowerShell, use a hidden prompt and convert the value only for the current
process:

```powershell
$secureKey = Read-Host "Temporary API key" -AsSecureString
$keyPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
try {
    $env:ANKIFORGE_DEV_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPtr)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPtr)
}
```

## Run Manually

Run from the repository root and supply every provider setting explicitly.
Replace the example URL and identifiers with values from the provider's
official documentation:

```powershell
python -m scripts.dev_real_provider_smoke `
  --provider-id "manual-provider" `
  --provider-name "Manual Provider" `
  --model-name "manual-model" `
  --base-url "https://provider.example/v1" `
  --confirm-send
```

The built-in sample is short and non-private. A different short input can be
passed with `--text`, but the harness will not echo the complete source text.
File input is deliberately unsupported.

Both the API key environment variable and `--confirm-send` are required before
the transport can be called. A successful run exits with code `0`; provider
failure exits with code `1`; missing consent, missing key, or invalid arguments
exit with code `2`.

Output is restricted to provider/model display data, safe extraction status,
knowledge-point count, safe error information, `will_write_to_anki=False`, and
knowledge-point titles. It does not print Authorization, the API key, raw JSON,
the complete source text, response bodies, or original exception messages.

## Clean Up

Remove the temporary environment variable after the manual smoke:

```powershell
Remove-Item Env:ANKIFORGE_DEV_API_KEY
```

If a call fails, inspect the safe dry-run summary. Do not add raw response or
credential logging while troubleshooting.

## Not Implemented

The harness does not provide UI consent, config/key storage, provider presets,
retry/backoff, rate-limit handling, token/cost accounting, card generation,
review workflow integration, or Anki writing.
