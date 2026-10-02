from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from pypdf import PdfWriter

from render_pdf_pages import render_pages


class RenderCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.pdf = self.root / "论文.pdf"
        self.pages = self.root / "pages"
        self.write_pdf()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_pdf(self, count: int = 1) -> None:
        writer = PdfWriter()
        for _ in range(count):
            writer.add_blank_page(width=72, height=72)
        writer.add_metadata({"/Title": "编码®诊断"})
        with self.pdf.open("wb") as stream:
            writer.write(stream)

    def test_hit_skips_pdf_open_and_preserves_pages(self) -> None:
        first = render_pages(self.pdf, self.pages, 100)
        self.assertFalse(first["cache_hit"])
        output = Path(first["pages"][0])
        original_mtime = output.stat().st_mtime_ns
        with patch("render_pdf_pages.pdfium.PdfDocument", side_effect=AssertionError("cache must skip rendering")):
            second = render_pages(self.pdf, self.pages, 100)
        self.assertTrue(second["cache_hit"])
        self.assertEqual(original_mtime, output.stat().st_mtime_ns)

    def test_dpi_change_invalidates_cache(self) -> None:
        render_pages(self.pdf, self.pages, 100)
        result = render_pages(self.pdf, self.pages, 110)
        self.assertFalse(result["cache_hit"])
        with Image.open(result["pages"][0]) as image:
            self.assertEqual((110, 110), image.size)

    def test_source_change_invalidates_cache(self) -> None:
        render_pages(self.pdf, self.pages, 100)
        self.write_pdf(2)
        result = render_pages(self.pdf, self.pages, 100)
        self.assertFalse(result["cache_hit"])
        self.assertEqual(2, len(result["pages"]))

    def test_changed_or_missing_page_is_repaired(self) -> None:
        result = render_pages(self.pdf, self.pages, 100)
        output = Path(result["pages"][0])
        output.write_bytes(b"broken generated page")
        self.assertFalse(render_pages(self.pdf, self.pages, 100)["cache_hit"])
        with Image.open(output) as image:
            image.verify()
        output.unlink()
        self.assertFalse(render_pages(self.pdf, self.pages, 100)["cache_hit"])
        self.assertTrue(output.is_file())

    def test_force_ignores_valid_cache(self) -> None:
        render_pages(self.pdf, self.pages, 100)
        self.assertFalse(render_pages(self.pdf, self.pages, 100, force=True)["cache_hit"])

    def test_malformed_cache_preserves_unrelated_files(self) -> None:
        render_pages(self.pdf, self.pages, 100)
        unrelated = self.pages / "page-notes.png"
        unrelated.write_bytes(b"keep user notes")
        (self.pages / "page-render-cache.json").write_text("{broken", encoding="utf-8")
        self.assertFalse(render_pages(self.pdf, self.pages, 100)["cache_hit"])
        self.assertEqual(b"keep user notes", unrelated.read_bytes())

    def test_truncated_page_list_is_not_a_hit(self) -> None:
        self.write_pdf(2)
        render_pages(self.pdf, self.pages, 100)
        cache = self.pages / "page-render-cache.json"
        content = json.loads(cache.read_text(encoding="utf-8"))
        content["outputs"] = content["outputs"][:1]
        cache.write_text(json.dumps(content), encoding="utf-8")
        result = render_pages(self.pdf, self.pages, 100)
        self.assertFalse(result["cache_hit"])
        self.assertEqual(2, len(result["pages"]))

    def test_inspector_console_is_utf8_even_under_gbk(self) -> None:
        env = os.environ.copy()
        env.update(PYTHONUTF8="0", PYTHONIOENCODING="gbk:strict")
        result = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("inspect_pdf.py")), str(self.pdf),
             "--out-dir", str(self.root / "source"), "--no-render"],
            capture_output=True, env=env, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr.decode("utf-8", errors="replace"))
        report = json.loads(result.stdout.decode("utf-8"))
        self.assertEqual("编码®诊断", report["metadata"]["Title"])


if __name__ == "__main__":
    unittest.main()
