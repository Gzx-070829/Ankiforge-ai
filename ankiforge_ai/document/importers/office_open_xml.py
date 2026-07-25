from __future__ import annotations

import re
from pathlib import Path

from ..archive_safety import open_validated_archive
from ..errors import DocumentImportError
from ..limits import DEFAULT_DOCUMENT_LIMITS
from ..models import BlockKind, DocumentSection
from ..source_labels import get_safe_source_label
from ..xml_safety import local_name, parse_xml_bounded
from .base import DocumentImporter, ImportInspection
from .text import block, import_error, location, make_document, warning


CONTENT_TYPES_NAMESPACE = (
    "http://schemas.openxmlformats.org/package/2006/content-types"
)
PACKAGE_RELATIONSHIPS_NAMESPACE = (
    "http://schemas.openxmlformats.org/package/2006/relationships"
)
OFFICE_RELATIONSHIPS_NAMESPACE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
)
OFFICE_DOCUMENT_RELATIONSHIP = (
    f"{OFFICE_RELATIONSHIPS_NAMESPACE}/officeDocument"
)
SLIDE_RELATIONSHIP = f"{OFFICE_RELATIONSHIPS_NAMESPACE}/slide"
WORKSHEET_RELATIONSHIP = f"{OFFICE_RELATIONSHIPS_NAMESPACE}/worksheet"
WORD_NAMESPACE = (
    "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
)
PRESENTATION_NAMESPACE = (
    "http://schemas.openxmlformats.org/presentationml/2006/main"
)
SPREADSHEET_NAMESPACE = (
    "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
)
WORD_MAIN = (
    "application/vnd.openxmlformats-officedocument."
    "wordprocessingml.document.main+xml"
)
PRESENTATION_MAIN = (
    "application/vnd.openxmlformats-officedocument."
    "presentationml.presentation.main+xml"
)
WORKBOOK_MAIN = (
    "application/vnd.openxmlformats-officedocument."
    "spreadsheetml.sheet.main+xml"
)
SLIDE_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument."
    "presentationml.slide+xml"
)
WORKSHEET_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument."
    "spreadsheetml.worksheet+xml"
)


def _qname(namespace, name):
    return f"{{{namespace}}}{name}"


def _attrs(element):
    return {local_name(name): value for name, value in element.attrib.items()}


def _invalid_office():
    return import_error("invalid_office_archive")


def _office_xml(
    archive,
    member,
    limits,
    *,
    expected_namespace=None,
    expected_root=None,
):
    try:
        root = parse_xml_bounded(archive.read(member), limits)
    except DocumentImportError as error:
        if error.code == "xml_not_safe":
            raise
        raise _invalid_office() from None
    if (
        expected_namespace is not None
        and expected_root is not None
        and root.tag != _qname(expected_namespace, expected_root)
    ):
        raise _invalid_office()
    return root


def _declared_content_type(index, member):
    defaults, overrides = index
    if member in overrides:
        return overrides[member]
    extension = member.rsplit(".", 1)[-1].casefold() if "." in member else ""
    return defaults.get(extension)


def _require_content_type(index, member, expected):
    if _declared_content_type(index, member) != expected:
        raise _invalid_office()


def _validate_content_types(
    archive,
    required_member,
    required_content_type,
    limits,
):
    if not archive.contains("[Content_Types].xml") or not archive.contains(
        required_member
    ):
        raise _invalid_office()
    root = _office_xml(
        archive,
        "[Content_Types].xml",
        limits,
        expected_namespace=CONTENT_TYPES_NAMESPACE,
        expected_root="Types",
    )
    defaults = {}
    overrides = {}
    for item in root:
        if item.tag == _qname(CONTENT_TYPES_NAMESPACE, "Default"):
            extension = item.attrib.get("Extension")
            content_type = item.attrib.get("ContentType")
            if not extension or not content_type:
                raise _invalid_office()
            key = extension.casefold()
            if key in defaults:
                raise _invalid_office()
            defaults[key] = content_type
            continue
        if item.tag != _qname(CONTENT_TYPES_NAMESPACE, "Override"):
            raise _invalid_office()
        part_name = item.attrib.get("PartName")
        content_type = item.attrib.get("ContentType")
        if not part_name or not part_name.startswith("/") or not content_type:
            raise _invalid_office()
        relative = part_name[1:]
        try:
            resolved = archive.member_name(relative)
        except DocumentImportError:
            raise _invalid_office() from None
        if resolved is None or resolved in overrides:
            raise _invalid_office()
        overrides[resolved] = content_type
    index = (defaults, overrides)
    _require_content_type(index, required_member, required_content_type)
    return index


def _relationships(
    archive,
    member,
    limits,
    *,
    required=False,
    expected_type=None,
):
    if not archive.contains(member):
        if required:
            raise _invalid_office()
        return {}
    root = _office_xml(
        archive,
        member,
        limits,
        expected_namespace=PACKAGE_RELATIONSHIPS_NAMESPACE,
        expected_root="Relationships",
    )
    result = {}
    seen_ids = set()
    for relation in root:
        if relation.tag != _qname(
            PACKAGE_RELATIONSHIPS_NAMESPACE, "Relationship"
        ):
            raise _invalid_office()
        relation_id = relation.attrib.get("Id")
        target = relation.attrib.get("Target")
        relation_type = relation.attrib.get("Type")
        if (
            not relation_id
            or not target
            or not relation_type
            or relation_id in seen_ids
        ):
            raise _invalid_office()
        seen_ids.add(relation_id)
        if relation.attrib.get("TargetMode", "").casefold() == "external":
            continue
        base = member.replace("_rels/", "").removesuffix(".rels")
        resolved = archive.resolve(base, target)
        if resolved is None:
            raise _invalid_office()
        if expected_type is None or relation_type == expected_type:
            result[relation_id] = resolved
    return result


def _validate_root_relationship(archive, required_member, limits):
    relations = _relationships(
        archive,
        "_rels/.rels",
        limits,
        required=True,
        expected_type=OFFICE_DOCUMENT_RELATIONSHIP,
    )
    if (
        len(relations) != 1
        or next(iter(relations.values()), None) != required_member
    ):
        raise _invalid_office()


def _element_text(element, max_chars=None):
    parts = []
    size = 0
    for node in element.iter():
        name = local_name(node.tag)
        if name == "t" and node.text:
            value = node.text
        elif name == "tab":
            value = "\t"
        elif name in {"br", "cr"}:
            value = "\n"
        else:
            continue
        size += len(value)
        if max_chars is not None and size > max_chars:
            raise import_error("table_too_large")
        parts.append(value)
    return "".join(parts).strip()


class _OfficeImporter(DocumentImporter):
    def availability(self):
        return True

    def inspect(self, path, limits=DEFAULT_DOCUMENT_LIMITS):
        with open_validated_archive(path, limits):
            pass
        return ImportInspection(
            importer_id=self.importer_id,
            source_label=get_safe_source_label(path),
            detected_file_type=self.importer_id,
        )


class DocxImporter(_OfficeImporter):
    importer_id = "docx"
    supported_extensions = (".docx",)

    def import_document(self, path, limits=DEFAULT_DOCUMENT_LIMITS):
        label = get_safe_source_label(path)
        with open_validated_archive(path, limits) as archive:
            _validate_content_types(
                archive,
                "word/document.xml",
                WORD_MAIN,
                limits,
            )
            _validate_root_relationship(
                archive, "word/document.xml", limits
            )
            _relationships(
                archive,
                "word/_rels/document.xml.rels",
                limits,
            )
            root = _office_xml(
                archive,
                "word/document.xml",
                limits,
                expected_namespace=WORD_NAMESPACE,
                expected_root="document",
            )
            body = next(
                (item for item in root.iter() if local_name(item.tag) == "body"),
                None,
            )
            if body is None:
                raise import_error("invalid_office_archive")
            blocks = []
            heading = None
            for child in body:
                name = local_name(child.tag)
                if name == "p":
                    value = _element_text(child)
                    if not value:
                        continue
                    style = next(
                        (
                            _attrs(node).get("val", "")
                            for node in child.iter()
                            if local_name(node.tag) == "pStyle"
                        ),
                        "",
                    )
                    has_number = any(
                        local_name(node.tag) == "numPr" for node in child.iter()
                    )
                    if style.casefold().startswith("heading"):
                        kind = BlockKind.HEADING
                        heading = value
                    elif has_number:
                        kind = BlockKind.LIST
                    else:
                        kind = BlockKind.PARAGRAPH
                    blocks.append(
                        block(
                            len(blocks) + 1,
                            kind,
                            value,
                            label,
                            section="word/document.xml",
                        )
                    )
                elif name == "tbl":
                    rows = []
                    for row_index, row in enumerate((
                        item for item in child if local_name(item.tag) == "tr"
                    ), 1):
                        if row_index > limits.max_table_rows:
                            raise import_error("table_too_large")
                        cells = []
                        logical_columns = 0
                        for cell in (
                            (
                                item
                                for item in row
                                if local_name(item.tag) == "tc"
                            )
                        ):
                            span_value = next(
                                (
                                    _attrs(item).get("val", "1")
                                    for item in cell.iter()
                                    if local_name(item.tag) == "gridSpan"
                                ),
                                "1",
                            )
                            if (
                                not span_value.isdigit()
                                or int(span_value) < 1
                            ):
                                raise _invalid_office()
                            logical_columns += int(span_value)
                            if logical_columns > limits.max_table_columns:
                                raise import_error("table_too_large")
                            value = _element_text(
                                cell, limits.max_cell_chars
                            )
                            if len(value) > limits.max_cell_chars:
                                raise import_error("table_too_large")
                            cells.append(value)
                        if cells:
                            rows.append("\t".join(cells))
                    if rows:
                        blocks.append(
                            block(
                                len(blocks) + 1,
                                BlockKind.TABLE,
                                "\n".join(rows),
                                label,
                                section="word/document.xml",
                            )
                        )
        section = DocumentSection(
            section_id="section-00001",
            heading=heading,
            heading_path=(heading,) if heading else (),
            location=location(label, section="word/document.xml"),
            blocks=tuple(blocks),
        )
        extracted = "\n".join(item.text for item in blocks)
        return make_document(
            path,
            "docx",
            extracted,
            (section,),
            title=heading,
            limits=limits,
        )


def _ppt_tables(slide, limits):
    tables = []
    table_paragraph_ids = set()
    for table in (
        item for item in slide.iter() if local_name(item.tag) == "tbl"
    ):
        rows = []
        for row_index, row in enumerate(
            (
                item
                for item in table
                if local_name(item.tag) == "tr"
            ),
            1,
        ):
            if row_index > limits.max_table_rows:
                raise import_error("table_too_large")
            cells = []
            for cell_index, cell in enumerate(
                (
                    item
                    for item in row
                    if local_name(item.tag) == "tc"
                ),
                1,
            ):
                if cell_index > limits.max_table_columns:
                    raise import_error("table_too_large")
                value = _element_text(cell, limits.max_cell_chars)
                if len(value) > limits.max_cell_chars:
                    raise import_error("table_too_large")
                cells.append(value)
                table_paragraph_ids.update(
                    id(item)
                    for item in cell.iter()
                    if local_name(item.tag) == "p"
                )
            if cells:
                rows.append("\t".join(cells))
        if rows:
            tables.append("\n".join(rows))
    return tables, table_paragraph_ids


class PptxImporter(_OfficeImporter):
    importer_id = "pptx"
    supported_extensions = (".pptx",)

    def import_document(self, path, limits=DEFAULT_DOCUMENT_LIMITS):
        label = get_safe_source_label(path)
        with open_validated_archive(path, limits) as archive:
            required = "ppt/presentation.xml"
            content_types = _validate_content_types(
                archive,
                required,
                PRESENTATION_MAIN,
                limits,
            )
            _validate_root_relationship(archive, required, limits)
            root = _office_xml(
                archive,
                required,
                limits,
                expected_namespace=PRESENTATION_NAMESPACE,
                expected_root="presentation",
            )
            slide_ids = [
                _attrs(item).get("id")
                for item in root.iter()
                if local_name(item.tag) == "sldId"
            ]
            if any(not relation_id for relation_id in slide_ids):
                raise _invalid_office()
            relations = _relationships(
                archive,
                "ppt/_rels/presentation.xml.rels",
                limits,
                required=bool(slide_ids),
                expected_type=SLIDE_RELATIONSHIP,
            )
            sections = []
            block_index = 0
            for slide_number, relation_id in enumerate(slide_ids, 1):
                member = relations.get(relation_id)
                if member is None:
                    raise _invalid_office()
                _require_content_type(
                    content_types, member, SLIDE_CONTENT_TYPE
                )
                slide = _office_xml(
                    archive,
                    member,
                    limits,
                    expected_namespace=PRESENTATION_NAMESPACE,
                    expected_root="sld",
                )
                tables, table_paragraph_ids = _ppt_tables(slide, limits)
                paragraphs = []
                for paragraph in (
                    item for item in slide.iter() if local_name(item.tag) == "p"
                ):
                    if id(paragraph) in table_paragraph_ids:
                        continue
                    value = _element_text(paragraph)
                    if value:
                        paragraphs.append(value)
                blocks = []
                for paragraph_index, value in enumerate(paragraphs):
                    block_index += 1
                    blocks.append(
                        block(
                            block_index,
                            BlockKind.HEADING
                            if paragraph_index == 0
                            else BlockKind.LIST,
                            value,
                            label,
                            slide=slide_number,
                            section=member,
                        )
                    )
                for value in tables:
                    block_index += 1
                    blocks.append(
                        block(
                            block_index,
                            BlockKind.TABLE,
                            value,
                            label,
                            slide=slide_number,
                            section=member,
                        )
                    )
                heading = paragraphs[0] if paragraphs else f"Slide {slide_number}"
                sections.append(
                    DocumentSection(
                        section_id=f"section-{slide_number:05d}",
                        heading=heading,
                        heading_path=(heading,),
                        location=location(
                            label, slide=slide_number, section=member
                        ),
                        blocks=tuple(blocks),
                    )
                )
        extracted = "\n".join(
            item.text for section in sections for item in section.blocks
        )
        return make_document(
            path,
            "pptx",
            extracted,
            sections,
            title=sections[0].heading if sections else None,
            limits=limits,
        )


def _column_number(reference):
    letters = re.match(r"[A-Za-z]+", reference or "")
    result = 0
    for character in letters.group(0).upper() if letters else "":
        result = result * 26 + ord(character) - ord("A") + 1
    return result


def _column_label(number):
    result = []
    while number > 0:
        number, remainder = divmod(number - 1, 26)
        result.append(chr(ord("A") + remainder))
    return "".join(reversed(result))


def _validate_merged_ranges(root, limits):
    pattern = re.compile(
        r"^([A-Za-z]+)([1-9]\d*):([A-Za-z]+)([1-9]\d*)$"
    )
    for item in (
        node for node in root.iter() if local_name(node.tag) == "mergeCell"
    ):
        reference = _attrs(item).get("ref", "")
        match = pattern.fullmatch(reference)
        if match is None:
            raise _invalid_office()
        if (
            _column_number(match.group(1)) > limits.max_table_columns
            or _column_number(match.group(3)) > limits.max_table_columns
            or int(match.group(2)) > limits.max_table_rows
            or int(match.group(4)) > limits.max_table_rows
        ):
            raise import_error("table_too_large")


class XlsxImporter(_OfficeImporter):
    importer_id = "xlsx"
    supported_extensions = (".xlsx",)

    def import_document(self, path, limits=DEFAULT_DOCUMENT_LIMITS):
        label = get_safe_source_label(path)
        warnings = []
        with open_validated_archive(path, limits) as archive:
            required = "xl/workbook.xml"
            content_types = _validate_content_types(
                archive,
                required,
                WORKBOOK_MAIN,
                limits,
            )
            _validate_root_relationship(archive, required, limits)
            workbook = _office_xml(
                archive,
                required,
                limits,
                expected_namespace=SPREADSHEET_NAMESPACE,
                expected_root="workbook",
            )
            sheets = [
                item
                for item in workbook.iter()
                if local_name(item.tag) == "sheet"
            ]
            relations = _relationships(
                archive,
                "xl/_rels/workbook.xml.rels",
                limits,
                required=bool(sheets),
                expected_type=WORKSHEET_RELATIONSHIP,
            )
            shared = []
            if archive.contains("xl/sharedStrings.xml"):
                shared_root = _office_xml(
                    archive, "xl/sharedStrings.xml", limits
                )
                for item in shared_root:
                    shared.append(_element_text(item, limits.max_cell_chars))
            sections = []
            block_index = 0
            for sheet in sheets:
                attrs = _attrs(sheet)
                sheet_name = get_safe_source_label(attrs.get("name", "Sheet"))
                relation_id = attrs.get("id")
                if not relation_id:
                    raise _invalid_office()
                member = relations.get(relation_id)
                if member is None:
                    raise _invalid_office()
                _require_content_type(
                    content_types, member, WORKSHEET_CONTENT_TYPE
                )
                if attrs.get("state", "visible").casefold() != "visible":
                    warnings.append(warning("hidden_sheet_skipped", label, sheet=sheet_name))
                    continue
                root = _office_xml(
                    archive,
                    member,
                    limits,
                    expected_namespace=SPREADSHEET_NAMESPACE,
                    expected_root="worksheet",
                )
                _validate_merged_ranges(root, limits)
                rows = []
                formulas = []
                maximum_columns = 0
                for row_index, row in enumerate(
                    (item for item in root.iter() if local_name(item.tag) == "row"),
                    1,
                ):
                    row_reference = _attrs(row).get("r", "")
                    effective_row = (
                        int(row_reference)
                        if row_reference.isdigit()
                        else row_index
                    )
                    if (
                        row_index > limits.max_table_rows
                        or effective_row > limits.max_table_rows
                    ):
                        raise import_error("table_too_large")
                    cells = []
                    for cell_index, cell in enumerate(
                        (
                            item
                            for item in row
                            if local_name(item.tag) == "c"
                        ),
                        1,
                    ):
                        cell_attrs = _attrs(cell)
                        supplied_reference = cell_attrs.get("r", "")
                        referenced_column = _column_number(
                            supplied_reference
                        )
                        effective_column = referenced_column or cell_index
                        if (
                            cell_index > limits.max_table_columns
                            or effective_column > limits.max_table_columns
                        ):
                            raise import_error("table_too_large")
                        maximum_columns = max(
                            maximum_columns, effective_column
                        )
                        reference = supplied_reference or (
                            f"{_column_label(effective_column)}{effective_row}"
                        )
                        formula = next(
                            (
                                item.text or ""
                                for item in cell
                                if local_name(item.tag) == "f"
                            ),
                            None,
                        )
                        raw = next(
                            (
                                item.text or ""
                                for item in cell
                                if local_name(item.tag) == "v"
                            ),
                            "",
                        )
                        inline = next(
                            (
                                _element_text(item, limits.max_cell_chars)
                                for item in cell
                                if local_name(item.tag) == "is"
                            ),
                            "",
                        )
                        if (
                            (formula is not None and len(formula) > limits.max_cell_chars)
                            or len(raw) > limits.max_cell_chars
                            or len(inline) > limits.max_cell_chars
                        ):
                            raise import_error("table_too_large")
                        if cell_attrs.get("t") == "s" and raw.isdigit():
                            index = int(raw)
                            value = shared[index] if index < len(shared) else ""
                        else:
                            value = inline or raw
                        if len(value) > limits.max_cell_chars:
                            raise import_error("table_too_large")
                        cells.append(value)
                        if formula is not None:
                            formulas.append((reference, formula, raw))
                    rows.append("\t".join(cells))
                blocks = []
                if rows:
                    block_index += 1
                    blocks.append(
                        block(
                            block_index,
                            BlockKind.TABLE,
                            "\n".join(rows),
                            label,
                            sheet=sheet_name,
                            row_start=1,
                            row_end=len(rows),
                            section=member,
                            metadata={"column_count": maximum_columns},
                        )
                    )
                for reference, formula, cached in formulas:
                    block_index += 1
                    suffix = f" (cached: {cached})" if cached else ""
                    blocks.append(
                        block(
                            block_index,
                            BlockKind.FORMULA,
                            f"={formula}{suffix}",
                            label,
                            sheet=sheet_name,
                            cell_range=reference,
                            section=member,
                        )
                    )
                sections.append(
                    DocumentSection(
                        section_id=f"section-{len(sections) + 1:05d}",
                        heading=sheet_name,
                        heading_path=(sheet_name,),
                        location=location(label, sheet=sheet_name, section=member),
                        blocks=tuple(blocks),
                    )
                )
        extracted = "\n".join(
            item.text for section in sections for item in section.blocks
        )
        return make_document(
            path,
            "xlsx",
            extracted,
            sections,
            warnings=warnings,
            limits=limits,
        )
