from ..limits import DEFAULT_DOCUMENT_LIMITS
from ..importers.optional_backends import (
    backend_error,
    document_from_backend_markdown,
    validate_local_backend_path,
    validated_backend_text,
)
from .base import BackendCapability, BackendCommand, DocumentBackend
from .command_runner import SafeCommandRunner
from .detection import probe_absolute_executable


class PandocBackend(DocumentBackend):
    backend_id = "pandoc"
    _CAPABILITY = BackendCapability(
        backend_id=backend_id,
        display_name="Pandoc",
        supported_extensions=(
            ".docx",
            ".odt",
            ".md",
            ".markdown",
            ".rst",
            ".org",
            ".tex",
        ),
        supports_structure=False,
        supports_tables=True,
        supports_pdf=False,
    )
    _INPUT_FORMATS = {
        ".docx": "docx",
        ".odt": "odt",
        ".md": "gfm",
        ".markdown": "gfm",
        ".rst": "rst",
        ".org": "org",
        ".tex": "latex",
    }

    def __init__(self, executable=None, *, runner=None):
        self._executable = executable
        self._runner = runner

    def capabilities(self):
        return self._CAPABILITY

    def probe(self):
        return probe_absolute_executable(self.backend_id, self._executable)

    def convert_local_file(self, path, limits=DEFAULT_DOCUMENT_LIMITS):
        source = validate_local_backend_path(
            path,
            self._CAPABILITY.supported_extensions,
            limits,
        )
        probe = self.probe()
        if not probe.available:
            raise backend_error("backend_unavailable", "enable_backend")
        runner = self._runner if self._runner is not None else SafeCommandRunner()
        input_format = self._INPUT_FORMATS[source.suffix.casefold()]
        result = runner.run(
            BackendCommand(
                executable=self._executable,
                arguments=(
                    "--sandbox",
                    "--from",
                    input_format,
                    "--to",
                    "gfm",
                ),
                source_path=source,
                output_format="text",
            )
        )
        output = validated_backend_text(result, limits)
        return document_from_backend_markdown(
            source,
            self.backend_id,
            output,
            limits,
        )
