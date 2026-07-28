import sys

from ..limits import DEFAULT_DOCUMENT_LIMITS
from ..importers.optional_backends import (
    parse_docling_output,
    validate_local_backend_path,
    validated_backend_text,
)
from .base import BackendCapability, BackendCommand, DocumentBackend
from .command_runner import SafeCommandRunner
from .detection import probe_python_module


class DoclingBackend(DocumentBackend):
    backend_id = "docling"
    _CAPABILITY = BackendCapability(
        backend_id=backend_id,
        display_name="Docling",
        supported_extensions=(".pdf", ".docx", ".pptx", ".xlsx", ".html"),
        supports_structure=True,
        supports_tables=True,
        supports_pdf=True,
    )

    def __init__(self, *, runner=None):
        self._runner = runner

    def capabilities(self):
        return self._CAPABILITY

    def probe(self):
        return probe_python_module(self.backend_id, "docling")

    def convert_local_file(self, path, limits=DEFAULT_DOCUMENT_LIMITS):
        source = validate_local_backend_path(
            path,
            self._CAPABILITY.supported_extensions,
            limits,
        )
        runner = self._runner if self._runner is not None else SafeCommandRunner()
        result = runner.run(
            BackendCommand(
                executable=sys.executable,
                arguments=(
                    "-I",
                    "-m",
                    "docling",
                    "--to",
                    "md",
                    "--output",
                    ".",
                    "--no-ocr",
                ),
                source_path=source,
                output_format="text",
                output_artifact_suffix=".md",
            )
        )
        output = validated_backend_text(result, limits)
        return parse_docling_output(source, output, limits, schema="markdown")
