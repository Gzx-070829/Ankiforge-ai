from __future__ import annotations

from ..archive_safety import open_validated_archive
from ..limits import DEFAULT_DOCUMENT_LIMITS
from ..models import DocumentSection
from ..source_labels import get_safe_source_label
from ..xml_safety import local_name, parse_xml_bounded
from .base import DocumentImporter, ImportInspection
from .html import _SafeHTMLParser
from .text import (
    DocumentParseBudget,
    block,
    import_error,
    location,
    make_document,
)


def _attrs(element):
    return {local_name(name): value for name, value in element.attrib.items()}


class EpubImporter(DocumentImporter):
    importer_id = "epub"
    supported_extensions = (".epub",)

    def availability(self):
        return True

    def inspect(self, path, limits=DEFAULT_DOCUMENT_LIMITS):
        with open_validated_archive(path, limits):
            pass
        return ImportInspection(
            importer_id=self.importer_id,
            source_label=get_safe_source_label(path),
            detected_file_type="epub",
        )

    def import_document(self, path, limits=DEFAULT_DOCUMENT_LIMITS):
        label = get_safe_source_label(path)
        budget = DocumentParseBudget(limits)
        with open_validated_archive(path, limits) as archive:
            if not archive.contains("mimetype") or not archive.contains(
                "META-INF/container.xml"
            ):
                raise import_error("malformed_file")
            if archive.read("mimetype").strip() != b"application/epub+zip":
                raise import_error("malformed_file")
            container = parse_xml_bounded(
                archive.read("META-INF/container.xml"), limits
            )
            rootfile = next(
                (
                    _attrs(item).get("full-path")
                    for item in container.iter()
                    if local_name(item.tag) == "rootfile"
                ),
                None,
            )
            if not rootfile:
                raise import_error("malformed_file")
            try:
                opf_member = archive.member_name(rootfile)
            except Exception:
                opf_member = None
            if opf_member is None:
                raise import_error("malformed_file")
            opf = parse_xml_bounded(archive.read(opf_member), limits)
            title = next(
                (
                    (item.text or "").strip()
                    for item in opf.iter()
                    if local_name(item.tag) == "title" and (item.text or "").strip()
                ),
                None,
            )
            manifest = {}
            for item in (
                node for node in opf.iter() if local_name(node.tag) == "item"
            ):
                attrs = _attrs(item)
                item_id, href = attrs.get("id"), attrs.get("href")
                if item_id and href:
                    resolved = archive.resolve(opf_member, href)
                    manifest[item_id] = (
                        resolved,
                        attrs.get("media-type", "application/octet-stream"),
                    )
            spine = [
                _attrs(item).get("idref")
                for item in opf.iter()
                if local_name(item.tag) == "itemref"
            ]
            sections = []
            block_index = 0
            for item_id in spine:
                budget.consume_section()
                manifest_item = manifest.get(item_id)
                if manifest_item is None or manifest_item[0] is None:
                    raise import_error("malformed_file")
                member, media_type = manifest_item
                chapter_payload = archive.read(member)
                if media_type.casefold() == "application/xhtml+xml":
                    chapter_root = parse_xml_bounded(chapter_payload, limits)
                    if local_name(chapter_root.tag).casefold() != "html":
                        raise import_error("malformed_file")
                try:
                    if chapter_payload.startswith((b"\xff\xfe", b"\xfe\xff")):
                        chapter_text = chapter_payload.decode("utf-16")
                    else:
                        chapter_text = chapter_payload.decode("utf-8-sig")
                except UnicodeDecodeError:
                    raise import_error("malformed_file") from None
                parser = _SafeHTMLParser(limits, budget=budget)
                parser.feed(chapter_text)
                parser.close()
                blocks = []
                for kind, value, start, end in parser.items:
                    block_index += 1
                    blocks.append(
                        block(
                            block_index,
                            kind,
                            value,
                            label,
                            line_start=start,
                            line_end=end,
                            section=member,
                            metadata={"media_type": media_type[:120]},
                        )
                    )
                heading = next(
                    (
                        item.text
                        for item in blocks
                        if item.kind.value == "heading"
                    ),
                    f"Chapter {len(sections) + 1}",
                )
                sections.append(
                    DocumentSection(
                        section_id=f"section-{len(sections) + 1:05d}",
                        heading=heading,
                        heading_path=(heading,),
                        location=location(label, section=member),
                        blocks=tuple(blocks),
                    )
                )
        extracted = "\n".join(
            item.text for section in sections for item in section.blocks
        )
        return make_document(
            path,
            "epub",
            extracted,
            sections,
            title=title,
            limits=limits,
        )
