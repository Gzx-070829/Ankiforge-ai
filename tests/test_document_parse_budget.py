import unittest
from dataclasses import replace

from ankiforge_ai.document import DEFAULT_DOCUMENT_LIMITS, DocumentImportError
from ankiforge_ai.document.importers.html import _SafeHTMLParser


class DocumentParseBudgetTests(unittest.TestCase):
    def test_html_parser_rejects_before_retaining_more_than_the_block_limit(self):
        limits = replace(DEFAULT_DOCUMENT_LIMITS, max_document_blocks=2)
        parser = _SafeHTMLParser(limits)

        with self.assertRaises(DocumentImportError) as raised:
            parser.feed("<p>one</p><p>two</p><p>three</p>")

        self.assertEqual(raised.exception.code, "document_too_complex")
        self.assertLessEqual(len(parser.items), 2)


if __name__ == "__main__":
    unittest.main()
