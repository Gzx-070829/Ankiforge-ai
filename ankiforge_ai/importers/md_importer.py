"""
Markdown importer for AnkiForge AI.

Splits a Markdown file into chunks by ATX heading (#, ##, ###...). Each chunk
keeps its heading text, heading level, body content, and source path. The
parser deliberately has no Anki dependency, so it can be tested with plain
Python outside Anki.
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


_HEADING_PATTERN = re.compile(r"^\s{0,3}(#{1,6})[ \t]+(.+?)(?:[ \t]+#+[ \t]*)?$")
_FENCE_PATTERN = re.compile(r"^\s{0,3}(`{3,}|~{3,})")


def split_markdown_by_headings(file_path: str) -> List[MarkdownChunk]:
    """
    Read a Markdown file and split it into chunks, one per heading.

    Content before the first heading (if any) is grouped under "Untitled".
    Empty chunks (heading with no body text) are skipped. Headings inside
    fenced code blocks are treated as normal content.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    lines = text.splitlines()
    chunks: List[MarkdownChunk] = []

    current_heading = "Untitled"
    current_level = 0
    current_lines: List[str] = []
    in_fence = False
    fence_char = ""
    fence_len = 0

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
        fence_match = _FENCE_PATTERN.match(line)
        if fence_match:
            fence_marker = fence_match.group(1)
            marker_char = fence_marker[0]
            marker_len = len(fence_marker)
            if not in_fence:
                in_fence = True
                fence_char = marker_char
                fence_len = marker_len
            elif marker_char == fence_char and marker_len >= fence_len:
                in_fence = False
                fence_char = ""
                fence_len = 0

            current_lines.append(line)
            continue

        match = None if in_fence else _HEADING_PATTERN.match(line)
        if match:
            flush()
            current_level = len(match.group(1))
            current_heading = match.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    flush()
    return chunks
