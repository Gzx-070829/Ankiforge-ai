# Task 3 Report: Optional Local Backend Adapters and Companion Protocol

## Status

Complete. Task 3 adds absence-safe, explicitly enabled local adapters for
Docling, MarkItDown, and Pandoc; a bounded no-shell command runner; strict
versioned companion messages; and an optional importer bridge. No optional
backend is enabled by default.

## Changed files

- `ankiforge_ai/document/backends/__init__.py`
- `ankiforge_ai/document/backends/base.py`
- `ankiforge_ai/document/backends/detection.py`
- `ankiforge_ai/document/backends/command_runner.py`
- `ankiforge_ai/document/backends/docling_adapter.py`
- `ankiforge_ai/document/backends/markitdown_adapter.py`
- `ankiforge_ai/document/backends/pandoc_adapter.py`
- `ankiforge_ai/document/backends/companion_protocol.py`
- `ankiforge_ai/document/backends/output_validation.py`
- `ankiforge_ai/document/importers/optional_backends.py`
- `tests/test_document_backend_capabilities.py`
- `tests/test_document_backend_command_runner.py`
- `tests/test_document_backend_adapters.py`
- `tests/test_document_companion_protocol.py`
- `.superpowers/sdd/2026-07-25-universal-document-intelligence/task-3-report.md`

## RED evidence

The prior implementer recorded genuine RED before implementation:

- The capability and companion protocol tests failed because the backend
  modules did not exist.
- The command-runner security tests failed because the runner did not exist.
- The adapter-focused run discovered 16 tests and ended with 5 errors before
  the adapter/importer implementation was completed.

These failures are recoverable from the final tests: removing the new modules
reproduces the missing-module/runner failures, while the adapter tests directly
exercise the previously missing conversions and optional importer bridge.

## GREEN evidence

Focused Task 3 verification:

```text
> python -m unittest tests.test_document_backend_adapters tests.test_document_backend_command_runner tests.test_document_backend_capabilities tests.test_document_companion_protocol
................
----------------------------------------------------------------------
Ran 16 tests in 7.798s

OK
```

Build regression:

```text
> python -m unittest tests.test_build_ankiaddon
.......
----------------------------------------------------------------------
Ran 7 tests in 0.016s

OK
```

Syntax compilation:

```text
> python -m py_compile ankiforge_ai/document/backends/__init__.py ankiforge_ai/document/backends/base.py ankiforge_ai/document/backends/detection.py ankiforge_ai/document/backends/command_runner.py ankiforge_ai/document/backends/docling_adapter.py ankiforge_ai/document/backends/markitdown_adapter.py ankiforge_ai/document/backends/pandoc_adapter.py ankiforge_ai/document/backends/companion_protocol.py ankiforge_ai/document/importers/optional_backends.py tests/test_document_backend_adapters.py tests/test_document_backend_capabilities.py tests/test_document_backend_command_runner.py tests/test_document_companion_protocol.py
[no output; exit 0]
```

Whitespace validation:

```text
> git diff --check
[no output; exit 0]
```

Package-boundary scan:

```text
> Get-ChildItem -LiteralPath 'ankiforge_ai' -Recurse -File | Where-Object { $_.Extension -in '.exe','.dll','.so','.dylib','.bin','.onnx','.pt','.pth','.safetensors','.gguf','.model','.zip','.tar','.gz','.whl','.tmp','.temp','.download','.part' } | Select-Object FullName,Length
[no output; exit 0]

> git ls-files ankiforge_ai | Select-String -Pattern '\.(exe|dll|so|dylib|bin|onnx|pt|pth|safetensors|gguf|model|zip|tar|gz|whl|tmp|temp|download|part)$'
[no output; exit 0]
```

No third-party package, executable, model, downloaded file, or temporary
output is included under `ankiforge_ai/`.

## Requirement mapping

- Capability/version/health models, the `DocumentBackend` interface, commands,
  results, and safe probes:
  `backends/base.py`, `backends/detection.py`,
  `test_document_backend_capabilities.py`.
- Strict versioned and immutable request/progress/response JSON:
  `backends/companion_protocol.py`,
  `test_document_companion_protocol.py`.
- Literal argument vectors, `shell=False`, fixed absolute executables,
  sanitized environment, controlled temporary cwd, bounded output, timeout,
  cancellation, termination, cleanup, and output validation:
  `backends/command_runner.py`,
  `test_document_backend_command_runner.py`.
- Literal MarkItDown Markdown, Docling's fixed Markdown artifact CLI contract
  (plus an explicitly selected trusted JSON schema), and sandboxed Pandoc GFM
  mapping into validated `DocumentIR`:
  the three adapter modules, `importers/optional_backends.py`,
  `test_document_backend_adapters.py`.
- Absence-safe imports and explicit opt-in:
  `backends/__init__.py`, `importers/optional_backends.py`,
  capability and adapter tests.

## Security and package-boundary self-review

- Commands use an argument vector with `shell=False`; executable paths must be
  fixed absolute local files.
- Source paths must be validated local paths. URL-like paths, user-controlled
  switches, absolute output arguments, credentials, and remote fields are
  rejected or absent from the public models.
- The runner uses a sanitized environment and private temporary working
  directory, enforces timeout/cancellation and stdout/stderr limits, and cleans
  up after completion or failure.
- Error representations report stable codes and sizes rather than source text,
  captured payloads, or credentials.
- Docling OCR/plugins/remote/downloads are disabled; Pandoc arguments are fixed
  to `--sandbox --from ... --to gfm`; all adapter output is bounded and
  validated before conversion to `DocumentIR`.
- Optional Python modules are not imported by core import, and probes turn
  absence into stable unavailable results without a traceback.
- Only first-party Python source/tests/report files are added. The scan above
  found no vendored dependency, executable, model, archive, download, or temp
  artifact in the runtime package.

## Concerns

None. Optional backends remain unavailable until explicitly enabled and require
the caller to supply/install the corresponding trusted local backend.

## Review fix round 1

### RED evidence

The four review-blocker reproductions were written before the corresponding
runtime changes. The first combined RED run was:

```text
> python -m unittest tests.test_document_backend_command_runner tests.test_document_backend_adapters tests.test_document_companion_protocol
...
----------------------------------------------------------------------
Ran 17 tests in 0.073s

FAILED (failures=8, errors=17, skipped=1)
```

The exact failure categories were:

- `BackendCommand.__init__()` rejected the new
  `output_artifact_suffix` contract, so the artifact runner and Windows
  descendant-containment cases could not run.
- The Windows fail-closed assignment test had no `_WindowsJobObject` API.
- Docling treated valid Markdown beginning with `{` as guessed JSON and raised
  `backend_invalid_output`; its command lacked `--output .` and a Markdown
  artifact declaration.
- UNC, device, rooted Windows, and arbitrary POSIX absolute paths were not
  rejected by mapped adapter output.
- `CompanionRequest`, `CompanionProgress`, and `CompanionResponse` each
  accepted the float protocol version `1.0`.

The first implementation run then reached the new artifact reader and produced
one deterministic newline-expectation failure:

```text
Ran 18 tests in 15.706s
FAILED (failures=1, skipped=1)
```

The expectation was corrected to compare normalized Markdown newlines. A later
119-test regression run found that timer-driven cancellation could occur before
the test grandchild's readiness marker under suite load:

```text
Ran 119 tests in 19.190s
FAILED (failures=1)
```

Cancellation is now readiness-driven with a bounded deadline, so the Windows
test does not depend on scheduler timing or PID reuse.

### GREEN evidence

Focused Task 3 suite, with resource leaks promoted to errors:

```text
> python -W error::ResourceWarning -m unittest tests.test_document_backend_adapters tests.test_document_backend_command_runner tests.test_document_backend_capabilities tests.test_document_companion_protocol
.....................
----------------------------------------------------------------------
Ran 21 tests in 21.234s

OK
```

Task 1/Task 2 document import, Task 3 backend, and build regressions:

```text
> python -W error::ResourceWarning -m unittest tests.test_document_ir tests.test_document_errors_and_limits tests.test_document_registry tests.test_document_detection tests.test_document_importers_text_markup tests.test_document_importers_subtitles_code tests.test_document_importers_data_notebook tests.test_document_archive_xml_security tests.test_document_importers_office_epub tests.test_document_backend_adapters tests.test_document_backend_command_runner tests.test_document_backend_capabilities tests.test_document_companion_protocol tests.test_build_ankiaddon
.......................................................................................................................
----------------------------------------------------------------------
Ran 119 tests in 21.462s

OK
```

Changed runtime/tests compiled successfully:

```text
> python -m py_compile ankiforge_ai/document/backends/base.py ankiforge_ai/document/backends/command_runner.py ankiforge_ai/document/backends/companion_protocol.py ankiforge_ai/document/backends/docling_adapter.py ankiforge_ai/document/backends/output_validation.py ankiforge_ai/document/importers/optional_backends.py tests/test_document_backend_adapters.py tests/test_document_backend_command_runner.py tests/test_document_companion_protocol.py
[no output; exit 0]
```

Whitespace and package-boundary checks:

```text
> git diff --check
[no errors; exit 0]

> Get-ChildItem -LiteralPath 'ankiforge_ai' -Recurse -File | Where-Object { $_.Extension -in '.exe','.dll','.so','.dylib','.bin','.onnx','.pt','.pth','.safetensors','.gguf','.model','.zip','.tar','.gz','.whl','.tmp','.temp','.download','.part' } | Select-Object FullName,Length
[no output; exit 0]

> git ls-files ankiforge_ai | Select-String -Pattern '\.(exe|dll|so|dylib|bin|onnx|pt|pth|safetensors|gguf|model|zip|tar|gz|whl|tmp|temp|download|part)$'
[no output; exit 0]
```

### Review fix security self-review and mapping

- Windows processes are assigned immediately after `Popen` to a standard
  library `ctypes` Job Object configured with
  `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`. Assignment fails closed; timeout,
  cancellation, normal completion, and cleanup terminate and await the job
  before the controlled temporary directory is removed. Errors are stable
  codes without raw paths.
- Windows-gated tests spawn a child and grandchild, hold a file in the runner
  temp directory, and use readiness/survivor marker files rather than process
  identifiers. Both timeout and cancellation prove that descendants do not
  survive and the temp directory is released.
- `BackendCommand.output_artifact_suffix` is restricted to `.md`. The runner
  accepts exactly one root-level regular non-symlink Markdown artifact, bounds
  it before decoding, and rejects zero, multiple, nested, symlink, oversized,
  or unsafe artifacts before cleanup. Progress stdout remains bounded but is
  not returned as document content.
- Docling uses fixed `--to md --output . --no-ocr` arguments and consumes the
  controlled Markdown artifact. Markdown beginning with `[` or `{` is never
  guessed as JSON; the retained Docling JSON parser requires the explicit
  trusted `docling_json_v1` schema.
- Companion protocol versions now require `type(value) is int` and exact
  equality to version 1. Tests cover float, string, bool, NaN, positive and
  negative infinity, and oversized integers for every message type using the
  same non-leaking error.
- One centralized validator is used for runner stdout/artifacts and for
  adapter text/title before `DocumentIR` mapping. It rejects drive-absolute,
  UNC, device, rooted Windows, and arbitrary absolute POSIX paths while
  allowing relative Markdown links and ordinary slash-containing prose.
- The package scan remains empty: no backend installation, network call,
  third-party package, executable, model, download, or temp artifact was added.

### Review fix concerns

None.

## Review fix round 2

### RED evidence

The Windows gate-race and lexical validation tests were added before the
corresponding runtime changes. The first focused RED run was:

```text
> python -W error::ResourceWarning -m unittest tests.test_document_backend_command_runner.SafeCommandRunnerTests.test_windows_job_assignment_failure_is_fail_closed_and_sanitized tests.test_document_backend_command_runner.SafeCommandRunnerTests.test_rejects_short_rooted_and_punctuation_leading_absolute_paths tests.test_document_backend_adapters.DocumentBackendAdapterTests.test_adapters_reject_remote_paths_malformed_output_and_limit_overflow
FFFFFFFFFE
----------------------------------------------------------------------
Ran 3 tests in 6.297s

FAILED (failures=9, errors=1)
```

The failure categories were exact:

- The target launched before delayed Job assignment failed and its immediate
  descendant created the survivor-independent marker, proving the
  spawn-before-assignment race.
- Runner and adapter validation accepted the root-only `\` and `/`, short
  rooted `\secret.txt`, and slash-rooted `//server/share` forms.
- The non-path adapter control raised `backend_invalid_output` because the old
  POSIX regex falsely classified the HTML closing tag `</section>` as a path.

A drive/URI ambiguity mutation check then added `C://private/source.pdf` to
both boundaries before the scanner order was corrected:

```text
> python -m unittest tests.test_document_backend_command_runner.SafeCommandRunnerTests.test_rejects_invalid_utf8_json_document_ir_and_absolute_output tests.test_document_backend_adapters.DocumentBackendAdapterTests.test_adapters_reject_remote_paths_malformed_output_and_limit_overflow
FF
----------------------------------------------------------------------
Ran 2 tests in 3.672s

FAILED (failures=2)
```

### GREEN evidence

Focused Task 3 suite, including Windows gate assignment failure, immediate
descendant spawn, timeout/cancellation tree termination, output controls, and
resource-leak checks:

```text
> python -W error::ResourceWarning -m unittest tests.test_document_backend_adapters tests.test_document_backend_command_runner tests.test_document_backend_capabilities tests.test_document_companion_protocol
......................
----------------------------------------------------------------------
Ran 22 tests in 11.491s

OK
```

Task 1/Task 2 document import, Task 3 backend, and build regressions:

```text
> python -W error::ResourceWarning -m unittest tests.test_document_ir tests.test_document_errors_and_limits tests.test_document_registry tests.test_document_detection tests.test_document_importers_text_markup tests.test_document_importers_subtitles_code tests.test_document_importers_data_notebook tests.test_document_archive_xml_security tests.test_document_importers_office_epub tests.test_document_backend_adapters tests.test_document_backend_command_runner tests.test_document_backend_capabilities tests.test_document_companion_protocol tests.test_build_ankiaddon
........................................................................................................................
----------------------------------------------------------------------
Ran 120 tests in 11.776s

OK
```

Changed runtime/tests compiled successfully:

```text
> python -m py_compile ankiforge_ai/document/backends/base.py ankiforge_ai/document/backends/command_runner.py ankiforge_ai/document/backends/companion_protocol.py ankiforge_ai/document/backends/docling_adapter.py ankiforge_ai/document/backends/output_validation.py ankiforge_ai/document/importers/optional_backends.py tests/test_document_backend_adapters.py tests/test_document_backend_command_runner.py tests/test_document_companion_protocol.py
[no output; exit 0]
```

Whitespace and package-boundary checks:

```text
> git diff --check
[no errors; exit 0]

> Get-ChildItem -LiteralPath 'ankiforge_ai' -Recurse -File | Where-Object { $_.Extension -in '.exe','.dll','.so','.dylib','.bin','.onnx','.pt','.pth','.safetensors','.gguf','.model','.zip','.tar','.gz','.whl','.tmp','.temp','.download','.part' } | Select-Object FullName,Length
[no output; exit 0]

> git ls-files ankiforge_ai | Select-String -Pattern '\.(exe|dll|so|dylib|bin|onnx|pt|pth|safetensors|gguf|model|zip|tar|gz|whl|tmp|temp|download|part)$'
[no output; exit 0]
```

### Review fix security self-review and mapping

- On Windows the runner now launches a fixed, trusted internal Python gate
  with literal argv, `shell=False`, `close_fds=True`, the sanitized environment,
  and the controlled working directory. The gate blocks on a one-byte parent
  handshake before its only target `Popen`.
- The parent assigns the still-blocked gate to the kill-on-close Job Object
  before sending the handshake. Assignment failure kills, awaits, and closes
  the still-gated process, so no target or descendant exists. After successful
  assignment, the target inherits the Job and the gate forwards its
  stdout/stderr and return status while waiting.
- Windows tests use file markers rather than process identifiers. A delayed
  assignment failure proves that an immediate target descendant never starts;
  timeout and readiness-driven cancellation prove the target descendants are
  killed and the controlled temporary directory is released without
  `ResourceWarning`.
- The centralized output validator no longer uses path allowlist regexes. Its
  bounded lexical scanner rejects drive-absolute, UNC/device, slash- or
  backslash-rooted, root-only, and punctuation-leading POSIX tokens, including
  bracket- and parenthesis-leading names. Drive paths take precedence over the
  URI grammar.
- Runner and adapter tests cover every missed rooted form and assert stable
  `backend_invalid_output` errors do not echo content. Relative Markdown links,
  `input/output` prose, cited HTTPS URLs, and HTML closing tags remain valid
  non-path controls.
- The package scan remains empty: no third-party package, executable, model,
  download, or temporary artifact was added.

### Review fix round 2 concerns

None.

## Review fix round 3

### RED evidence

The self-closing HTML and suspended-target tests were added before the runtime
changes. The focused RED run was:

```text
> python -W error::ResourceWarning -m unittest tests.test_document_backend_command_runner.SafeCommandRunnerTests.test_allows_self_closing_html_and_rejects_path_near_misses tests.test_document_backend_adapters.DocumentBackendAdapterTests.test_adapters_reject_remote_paths_malformed_output_and_limit_overflow tests.test_document_backend_command_runner.SafeCommandRunnerTests.test_windows_runner_does_not_require_sys_executable_as_python tests.test_document_backend_command_runner.SafeCommandRunnerTests.test_windows_resume_failure_is_fail_closed_before_target_executes
EEEF
----------------------------------------------------------------------
Ran 4 tests in 2.586s

FAILED (failures=1, errors=3)
```

The failures reproduced both findings:

- The runner and adapter rejected legitimate `<br />` output as
  `backend_invalid_output`.
- Replacing `sys.executable` with a non-Python local path caused
  `backend_containment_failed` even though the validated target executable was
  independently supplied.
- The simulated resume failure hook was never called by the gate design. The
  target executed, created its immediate descendant marker, and the runner
  eventually returned `backend_timeout` instead of failing closed before
  execution.

### GREEN evidence

Focused Task 3 suite with resource leaks promoted to errors:

```text
> python -W error::ResourceWarning -m unittest tests.test_document_backend_adapters tests.test_document_backend_command_runner tests.test_document_backend_capabilities tests.test_document_companion_protocol
.........................
----------------------------------------------------------------------
Ran 25 tests in 34.037s

OK
```

Task 1/Task 2 document import, Task 3 backend, and build regressions:

```text
> python -W error::ResourceWarning -m unittest tests.test_document_ir tests.test_document_errors_and_limits tests.test_document_registry tests.test_document_detection tests.test_document_importers_text_markup tests.test_document_importers_subtitles_code tests.test_document_importers_data_notebook tests.test_document_archive_xml_security tests.test_document_importers_office_epub tests.test_document_backend_adapters tests.test_document_backend_command_runner tests.test_document_backend_capabilities tests.test_document_companion_protocol tests.test_build_ankiaddon
...........................................................................................................................
----------------------------------------------------------------------
Ran 123 tests in 36.601s

OK
```

Changed runtime/tests compiled successfully:

```text
> python -m py_compile ankiforge_ai/document/backends/command_runner.py ankiforge_ai/document/backends/output_validation.py tests/test_document_backend_adapters.py tests/test_document_backend_command_runner.py
[no output; exit 0]
```

Whitespace and package-boundary checks:

```text
> git diff --check
[no errors; exit 0]

> Get-ChildItem -LiteralPath 'ankiforge_ai' -Recurse -File | Where-Object { $_.Extension -in '.exe','.dll','.so','.dylib','.bin','.onnx','.pt','.pth','.safetensors','.gguf','.model','.zip','.tar','.gz','.whl','.tmp','.temp','.download','.part' } | Select-Object FullName,Length
[no output; exit 0]

> git ls-files ankiforge_ai | Select-String -Pattern '\.(exe|dll|so|dylib|bin|onnx|pt|pth|safetensors|gguf|model|zip|tar|gz|whl|tmp|temp|download|part)$'
[no output; exit 0]
```

### Review fix security self-review and mapping

- Windows now launches the actual validated target argv with `shell=False`,
  sanitized environment/cwd/handles, and the documented `CREATE_SUSPENDED`
  creation flag. It has no dependency on `sys.executable` or a Python command
  mode.
- The suspended process is assigned to the kill-on-close Job Object before any
  target instruction can execute. The documented Toolhelp thread snapshot,
  `OpenThread`, and `ResumeThread` APIs locate and resume its sole primary
  thread. No undocumented `NtResumeProcess` API is used.
- Assignment failure kills and awaits the uncontained but still-suspended
  target. Enumeration/open/resume failure terminates and awaits the contained
  suspended process. Both paths close process/pipe/Job handles and return the
  same non-leaking `backend_containment_failed` error.
- Tests prove a non-Python `sys.executable` is irrelevant, assignment and
  resume failure cannot create an immediate descendant marker, and
  timeout/readiness-driven cancellation still kill the complete descendant
  tree without PID assumptions or `ResourceWarning`.
- The lexical validator exempts `/` only when it is the terminal self-closing
  marker in a bounded, syntactically quoted `<.../>` tag. `<br />` and `<hr/>`
  are accepted, while standalone `text /`, `<tag /etc/passwd>`, and
  `<tag attr='/root/x'>` remain rejected without content leakage. Existing
  root-only, UNC/rooted path, relative Markdown link, slash-prose, URL, and
  closing-tag controls remain covered.
- The package scan remains empty.

### Review fix round 3 concerns

None.

## Review fix round 4

### RED evidence

Runner and adapter controls for terminal slashes used as empty unquoted
attribute values were added before the validator change. The focused RED run
was:

```text
> python -W error::ResourceWarning -m unittest tests.test_document_backend_command_runner.SafeCommandRunnerTests.test_allows_self_closing_html_and_rejects_path_near_misses tests.test_document_backend_adapters.DocumentBackendAdapterTests.test_adapters_reject_remote_paths_malformed_output_and_limit_overflow
FFFFFFFF
----------------------------------------------------------------------
Ran 2 tests in 5.842s

FAILED (failures=8)
```

All four forms, `<tag attr=/>`, `<tag attr = />`, `<tag attr= />`, and
`<tag attr =/>`, were accepted at both the command-runner and adapter
boundaries. Each subtest failed because `DocumentImportError` was not raised.
The same run's legitimate `<br />`, `<hr/>`, `<input disabled/>`, and
`<tag attr='x'/>` controls passed before execution reached the malformed
subtests.

### GREEN evidence

The exact focused boundary run after the minimal validator fix was:

```text
> python -W error::ResourceWarning -m unittest tests.test_document_backend_command_runner.SafeCommandRunnerTests.test_allows_self_closing_html_and_rejects_path_near_misses tests.test_document_backend_adapters.DocumentBackendAdapterTests.test_adapters_reject_remote_paths_malformed_output_and_limit_overflow
..
----------------------------------------------------------------------
Ran 2 tests in 5.756s

OK
```

Focused Task 3 suite with resource leaks promoted to errors:

```text
> python -W error::ResourceWarning -m unittest tests.test_document_backend_adapters tests.test_document_backend_command_runner tests.test_document_backend_capabilities tests.test_document_companion_protocol
.........................
----------------------------------------------------------------------
Ran 25 tests in 37.684s

OK
```

Task 1/Task 2 document import, Task 3 backend, and build regressions:

```text
> python -W error::ResourceWarning -m unittest tests.test_document_ir tests.test_document_errors_and_limits tests.test_document_registry tests.test_document_detection tests.test_document_importers_text_markup tests.test_document_importers_subtitles_code tests.test_document_importers_data_notebook tests.test_document_archive_xml_security tests.test_document_importers_office_epub tests.test_document_backend_adapters tests.test_document_backend_command_runner tests.test_document_backend_capabilities tests.test_document_companion_protocol tests.test_build_ankiaddon
...........................................................................................................................
----------------------------------------------------------------------
Ran 123 tests in 38.259s

OK
```

Changed runtime/tests compiled successfully:

```text
> python -m py_compile ankiforge_ai/document/backends/output_validation.py tests/test_document_backend_adapters.py tests/test_document_backend_command_runner.py
[no output; exit 0]
```

Whitespace and package-boundary checks:

```text
> git diff --check
[no errors; exit 0]

> Get-ChildItem -LiteralPath 'ankiforge_ai' -Recurse -File | Where-Object { $_.Extension -in '.exe','.dll','.so','.dylib','.bin','.onnx','.pt','.pth','.safetensors','.gguf','.model','.zip','.tar','.gz','.whl','.tmp','.temp','.download','.part' } | Select-Object FullName,Length
[no output; exit 0]

> git ls-files ankiforge_ai | Select-String -Pattern '\.(exe|dll|so|dylib|bin|onnx|pt|pth|safetensors|gguf|model|zip|tar|gz|whl|tmp|temp|download|part)$'
[no output; exit 0]
```

### Review fix security self-review and mapping

- `_is_html_self_closing_marker()` still requires a bounded, quote-balanced
  tag and a terminal `/>`. Before granting that exemption it now skips
  whitespace immediately before the slash and rejects an immediately
  preceding `=`, leaving the slash to the root-path validator.
- Runner and adapter controls cover four spacing variants of an empty
  unquoted attribute value and prove `backend_invalid_output` does not echo
  rejected content.
- Legitimate no-attribute, boolean-attribute, and quoted-attribute
  self-closing forms remain accepted at both validation boundaries.
- No general HTML parser, Windows containment code, package, executable,
  model, download, or temporary artifact was added.

### Review fix round 4 concerns

None.
