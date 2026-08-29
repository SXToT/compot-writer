from __future__ import annotations

import unittest

from build_package import validate_publication_metadata


class PublicationMetadataTests(unittest.TestCase):
    def test_canonical_sentence_is_accepted(self) -> None:
        text = (
            '研究团队提出了一种新方法。该成果以"Dynamic X-ray imaging with '
            'screen-printed perovskite CMOS array"为题，发表在'
            '"Nature Communications"上。'
        )
        self.assertEqual(
            validate_publication_metadata(text),
            (
                "Dynamic X-ray imaging with screen-printed perovskite CMOS array",
                "Nature Communications",
            ),
        )

    def test_chinese_curly_quotes_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_publication_metadata(
                "该成果以“Paper Title”为题，发表在“Journal Name”上。"
            )

    def test_book_title_marks_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_publication_metadata(
                "该成果以《Paper Title》为题，发表在《Journal Name》上。"
            )

    def test_unquoted_venue_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_publication_metadata(
                '该成果以"Paper Title"为题，发表在Journal Name上。'
            )

    def test_missing_english_title_or_venue_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_publication_metadata(
                '该成果以"中文题目"为题，发表在"中文期刊"上。'
            )


if __name__ == "__main__":
    unittest.main()
