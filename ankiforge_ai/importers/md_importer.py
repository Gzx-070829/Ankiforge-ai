"""
Markdown importer for AnkiForge AI.

Splits a Markdown file into chunks by heading (#, ##, ###...).
Each chunk keeps track of its heading text, heading level, body content,
and the source file path -- this metadata later becomes the "Source" field
on generated cards, so you always know which note a card came from.

This module has NO dependency on Anki itself, so it can be unit-tested
with plain `python3` outside of the Anki environment.
"""

import re
from dataclasses import dataclass
from typing import List


@dataclass
class MarkdownChunk:
    heading: str
    level: int
    content: str
    source_path: str


_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*)")


def split_markdown_by_headings(file_path: str) -> List[MarkdownChunk]:
    """
    Read a Markdown file and split it into chunks, one per heading.
    Content before the first heading (if any) is grouped under "Untitled".
    Empty chunks (heading with no body text) are skipped.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    lines = text.splitlines()
    chunks: List[MarkdownChunk] = []

    current_heading = "Untitled"
    current_level = 0
    current_lines: List[str] = []

    def flush():
        content = "\n".join(current_lines).strip()
        if content:
            chunks.append(
                MarkdownChunk(
                    heading=current_heading,
                    level=current_level,
                    content=content,
                    source_path=file_path,
                )
            )

    for line in lines:
        match = _HEADING_PATTERN.match(line)
        if match:
            flush()
            current_level = len(match.group(1))
            current_heading = match.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    flush()
    return chunks
