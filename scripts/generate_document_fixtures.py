"""Generate deterministic, reviewable fixtures for native document importers."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = ROOT / "tests" / "fixtures" / "documents"
SECURITY = ROOT / "tests" / "fixtures" / "security"
ZIP_TIME = (2020, 1, 2, 3, 4, 6)


def write_text(name: str, text: str) -> None:
    (DOCUMENTS / name).write_text(text, encoding="utf-8", newline="\n")


def write_zip(name: str, members: list[tuple[str, bytes | str]]) -> None:
    path = DOCUMENTS / name
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for member_name, payload in members:
            info = zipfile.ZipInfo(member_name, ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(
                info,
                payload.encode("utf-8") if isinstance(payload, str) else payload,
            )


def office_content_types(
    part: str,
    media_type: str,
    *additional: tuple[str, str],
) -> str:
    overrides = "".join(
        f"<Override PartName='/{name}' ContentType='{kind}'/>"
        for name, kind in ((part, media_type), *additional)
    )
    return (
        "<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'>"
        "<Default Extension='xml' ContentType='application/xml'/>"
        f"{overrides}"
        "</Types>"
    )


def main() -> None:
    DOCUMENTS.mkdir(parents=True, exist_ok=True)
    SECURITY.mkdir(parents=True, exist_ok=True)
    write_text("plain.txt", "Alpha paragraph.\ncontinued\n\nBeta paragraph.\n")
    write_text(
        "structured.md",
        "---\ntitle: Safe Lesson\ntags: [alpha, beta]\n---\n"
        "# Topic\nIntro.\n\n## Details\n- first\n- second\n\n"
        "```python\nprint('not executed')\n```\n\n| A | B |\n|---|---|\n| 1 | 2 |\n",
    )
    write_text(
        "safe.html",
        "<html><head><title>HTML Lesson</title><style>SECRET_STYLE</style></head>"
        "<body><h1>Overview</h1><p>Safe <b>text</b>.</p>"
        "<script>FETCHED_SCRIPT</script><iframe src='https://example.invalid/x'>"
        "REMOTE_FRAME</iframe><ul><li>List item</li></ul>"
        "<table><tr><th>Name</th><th>Value</th></tr>"
        "<tr><td>Safe</td><td>1</td></tr></table>"
        "<img src='https://example.invalid/a.png' "
        "alt='Useful diagram'><blockquote>Quoted fact</blockquote>"
        "<pre><code>never_run()</code></pre></body></html>",
    )
    for name, text in {
        "notes.yaml": "title: YAML Notes\ninclude: never-read.txt\nitems:\n  - safe\n",
        "notes.rst": "RST Title\n=========\n\nParagraph.\n\n.. include:: never-read.txt\n",
        "notes.org": "* Org Title\nBody\n#+INCLUDE: \"never-read.txt\"\n",
        "notes.tex": "\\section{TeX Title}\nText\n\\input{never-read.txt}\n",
        "events.log": "INFO started\nWARNING stopped\n",
        "captions.srt": "1\n00:00:01,000 --> 00:00:02,500\nFirst caption.\n\n"
        "2\n00:00:02,600 --> 00:00:04,000\nSecond caption.\n",
        "captions.vtt": "WEBVTT\n\n00:00.000 --> 00:01.500\nOpening.\n\n"
        "00:02.000 --> 00:03.000\nClosing.\n",
    }.items():
        write_text(name, text)
    code = {
        "sample.py": "# comment\nvalue = 1\n\n# next\nprint(value)\n",
        "sample.js": "// comment\nconst value = 1;\n",
        "sample.ts": "// comment\nconst value: number = 1;\n",
        "Sample.java": "// comment\nclass Sample {}\n",
        "sample.c": "// comment\nint main(void) { return 0; }\n",
        "sample.h": "/* header */\nint value;\n",
        "sample.cpp": "// comment\nint main() { return 0; }\n",
        "sample.cc": "// comment\nint value = 1;\n",
        "sample.rs": "// comment\nfn main() {}\n",
        "sample.go": "// comment\npackage main\n",
        "sample.sql": "-- comment\nSELECT 1;\n",
        "sample.sh": "# comment\nprintf safe\n",
        "sample.ps1": "# comment\nWrite-Output safe\n",
    }
    for name, text in code.items():
        write_text(name, text)
    write_text("table.csv", "Name,Score\nAda,10\nLin,9\n")
    write_text("table.tsv", "Name\tScore\nAda\t10\nLin\t9\n")
    write_text("data.json", '{"topic":{"facts":["one","two"],"count":2}}\n')
    write_text("records.jsonl", '{"id":1,"value":"one"}\n{"id":2,"value":"two"}\n')
    write_text("safe.xml", "<catalog><item id='1'><name>Alpha</name></item></catalog>\n")
    write_text(
        "lesson.ipynb",
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "markdown",
                        "metadata": {},
                        "source": ["# Notebook Topic\n", "Explanation."],
                    },
                    {
                        "cell_type": "code",
                        "execution_count": None,
                        "metadata": {},
                        "source": ["raise RuntimeError('never executed')"],
                        "outputs": [
                            {"output_type": "stream", "name": "stdout", "text": ["safe output\n"]},
                            {
                                "output_type": "display_data",
                                "data": {"image/png": "aGVsbG8=", "text/plain": "<image>"},
                                "metadata": {},
                            },
                        ],
                    },
                ],
                "metadata": {},
                "nbformat": 4,
                "nbformat_minor": 5,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
    )
    write_zip(
        "lesson.docx",
        [
            (
                "[Content_Types].xml",
                office_content_types(
                    "word/document.xml",
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document.main+xml",
                ),
            ),
            (
                "word/document.xml",
                "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>"
                "<w:body><w:p><w:pPr><w:pStyle w:val='Heading1'/></w:pPr>"
                "<w:r><w:t>DOCX Topic</w:t></w:r></w:p>"
                "<w:p><w:pPr><w:numPr/></w:pPr><w:r><w:t>List item</w:t></w:r></w:p>"
                "<w:tbl><w:tr><w:tc><w:p><w:r><w:t>A</w:t></w:r></w:p></w:tc>"
                "<w:tc><w:p><w:r><w:t>B</w:t></w:r></w:p></w:tc></w:tr></w:tbl>"
                "</w:body></w:document>",
            ),
            (
                "_rels/.rels",
                "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>"
                "<Relationship Id='rId1' Target='word/document.xml' "
                "Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
                "officeDocument'/></Relationships>",
            ),
            (
                "word/_rels/document.xml.rels",
                "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>"
                "<Relationship Id='rId9' Target='https://example.invalid/remote' "
                "Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
                "hyperlink' TargetMode='External'/>"
                "</Relationships>",
            ),
        ],
    )
    write_zip(
        "slides.pptx",
        [
            (
                "[Content_Types].xml",
                office_content_types(
                    "ppt/presentation.xml",
                    "application/vnd.openxmlformats-officedocument."
                    "presentationml.presentation.main+xml",
                    (
                        "ppt/slides/slide1.xml",
                        "application/vnd.openxmlformats-officedocument."
                        "presentationml.slide+xml",
                    ),
                    (
                        "ppt/slides/slide2.xml",
                        "application/vnd.openxmlformats-officedocument."
                        "presentationml.slide+xml",
                    ),
                ),
            ),
            (
                "_rels/.rels",
                "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>"
                "<Relationship Id='rId1' Target='ppt/presentation.xml' "
                "Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
                "officeDocument'/></Relationships>",
            ),
            (
                "ppt/presentation.xml",
                "<p:presentation xmlns:p='http://schemas.openxmlformats.org/presentationml/2006/main' "
                "xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships'>"
                "<p:sldIdLst><p:sldId r:id='rId1'/><p:sldId r:id='rId2'/></p:sldIdLst></p:presentation>",
            ),
            (
                "ppt/_rels/presentation.xml.rels",
                "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>"
                "<Relationship Id='rId1' Target='slides/slide1.xml' "
                "Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
                "slide'/><Relationship Id='rId2' Target='slides/slide2.xml' "
                "Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
                "slide'/></Relationships>",
            ),
            (
                "ppt/slides/slide1.xml",
                "<p:sld xmlns:p='http://schemas.openxmlformats.org/presentationml/2006/main' "
                "xmlns:a='http://schemas.openxmlformats.org/drawingml/2006/main'>"
                "<p:cSld><p:spTree><p:sp><p:txBody>"
                "<a:p><a:r><a:t>First Slide</a:t></a:r></a:p>"
                "<a:p><a:r><a:t>Bullet one</a:t></a:r></a:p>"
                "</p:txBody></p:sp></p:spTree></p:cSld></p:sld>",
            ),
            (
                "ppt/slides/slide2.xml",
                "<p:sld xmlns:p='http://schemas.openxmlformats.org/presentationml/2006/main' "
                "xmlns:a='http://schemas.openxmlformats.org/drawingml/2006/main'>"
                "<p:cSld><p:spTree><p:sp><p:txBody>"
                "<a:p><a:r><a:t>Second Slide</a:t></a:r></a:p>"
                "</p:txBody></p:sp></p:spTree></p:cSld></p:sld>",
            ),
        ],
    )
    write_zip(
        "workbook.xlsx",
        [
            (
                "[Content_Types].xml",
                office_content_types(
                    "xl/workbook.xml",
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet.main+xml",
                    (
                        "xl/worksheets/sheet1.xml",
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.worksheet+xml",
                    ),
                    (
                        "xl/worksheets/sheet2.xml",
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.worksheet+xml",
                    ),
                ),
            ),
            (
                "_rels/.rels",
                "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>"
                "<Relationship Id='rId1' Target='xl/workbook.xml' "
                "Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
                "officeDocument'/></Relationships>",
            ),
            (
                "xl/workbook.xml",
                "<workbook xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main' "
                "xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships'>"
                "<sheets><sheet name='Visible' sheetId='1' r:id='rId1'/>"
                "<sheet name='Hidden' sheetId='2' state='hidden' r:id='rId2'/></sheets></workbook>",
            ),
            (
                "xl/_rels/workbook.xml.rels",
                "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>"
                "<Relationship Id='rId1' Target='worksheets/sheet1.xml' "
                "Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
                "worksheet'/><Relationship Id='rId2' Target='worksheets/sheet2.xml' "
                "Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
                "worksheet'/></Relationships>",
            ),
            (
                "xl/worksheets/sheet1.xml",
                "<worksheet xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'>"
                "<sheetData><row r='1'><c r='A1' t='inlineStr'><is><t>Name</t></is></c>"
                "<c r='B1' t='inlineStr'><is><t>Score</t></is></c></row>"
                "<row r='2'><c r='A2' t='inlineStr'><is><t>Ada</t></is></c>"
                "<c r='B2'><f>1+1</f><v>2</v></c></row></sheetData></worksheet>",
            ),
            (
                "xl/worksheets/sheet2.xml",
                "<worksheet xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'>"
                "<sheetData><row r='1'><c r='A1' t='inlineStr'><is><t>SECRET</t></is></c>"
                "</row></sheetData></worksheet>",
            ),
        ],
    )
    write_zip(
        "book.epub",
        [
            ("mimetype", "application/epub+zip"),
            (
                "META-INF/container.xml",
                "<container xmlns='urn:oasis:names:tc:opendocument:xmlns:container'>"
                "<rootfiles><rootfile full-path='OPS/book.opf'/></rootfiles></container>",
            ),
            (
                "OPS/book.opf",
                "<package xmlns='http://www.idpf.org/2007/opf'><metadata><title>Safe Book</title></metadata>"
                "<manifest><item id='c1' href='chapter1.xhtml' media-type='application/xhtml+xml'/>"
                "<item id='c2' href='chapter2.xhtml' media-type='application/xhtml+xml'/>"
                "<item id='remote' href='https://example.invalid/x' media-type='text/html'/></manifest>"
                "<spine><itemref idref='c2'/><itemref idref='c1'/></spine></package>",
            ),
            ("OPS/chapter1.xhtml", "<html><body><h1>First</h1><p>Chapter one.</p></body></html>"),
            ("OPS/chapter2.xhtml", "<html><body><h1>Second</h1><p>Chapter two.</p></body></html>"),
        ],
    )
    (SECURITY / "xxe.xml").write_text(
        '<!DOCTYPE root [<!ENTITY xxe SYSTEM "file:///never-read">]><root>&xxe;</root>',
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
