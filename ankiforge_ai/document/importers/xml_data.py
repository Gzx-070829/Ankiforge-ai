from __future__ import annotations

from ..limits import DEFAULT_DOCUMENT_LIMITS
from ..models import BlockKind, DocumentSection
from ..source_labels import get_safe_source_label
from ..xml_safety import local_name, parse_xml_bounded
from .base import DocumentImporter, ImportInspection
from .text import block, location, make_document, read_text_bounded


class XmlDataImporter(DocumentImporter):
    importer_id = "xml"
    supported_extensions = (".xml",)

    def availability(self):
        return True

    def inspect(self, path, limits=DEFAULT_DOCUMENT_LIMITS):
        read_text_bounded(path, limits)
        return ImportInspection(
            importer_id=self.importer_id,
            source_label=get_safe_source_label(path),
            detected_file_type="xml",
        )

    def import_document(self, path, limits=DEFAULT_DOCUMENT_LIMITS):
        text, _ = read_text_bounded(path, limits)
        label = get_safe_source_label(path)
        root = parse_xml_bounded(text.encode("utf-8"), limits)
        values = []
        stack = [(root, f"/{local_name(root.tag)}")]
        while stack:
            element, path_value = stack.pop()
            for name, value in element.attrib.items():
                values.append(
                (
                    f"{path_value}/@{local_name(name)} = {value}",
                    path_value.lstrip("/"),
                )
                )
            content = (element.text or "").strip()
            if content:
                values.append(
                    (f"{path_value} = {content}", path_value.lstrip("/"))
                )
            children = list(element)
            for child in reversed(children):
                stack.append((child, f"{path_value}/{local_name(child.tag)}"))
        blocks = tuple(
            block(
                index,
                BlockKind.METADATA,
                value,
                label,
                section=section_path,
            )
            for index, (value, section_path) in enumerate(values, 1)
        )
        section = DocumentSection(
            section_id="section-00001",
            heading=local_name(root.tag),
            heading_path=(local_name(root.tag),),
            location=location(label, section=local_name(root.tag)),
            blocks=blocks,
        )
        return make_document(path, "xml", text, (section,), limits=limits)
