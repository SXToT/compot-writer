from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    import fitz  # type: ignore
except ImportError:
    fitz = None

try:
    import pypdfium2 as pdfium  # type: ignore
except ImportError:
    pdfium = None


DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
CACHE_VERSION = 2


def fingerprint(path: Path) -> dict[str, int]:
    stat = path.stat()
    return {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def clean_doi(value: str) -> str:
    return value.rstrip(".,;:)]}，。；：）】}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract text and render every page of a source paper PDF.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--dpi", type=int, default=110, help="Preview DPI. Use 96-120 for fast all-page review.")
    parser.add_argument("--force", action="store_true", help="Ignore a valid existing inspection cache")
    parser.add_argument("--no-render", action="store_true", help="Extract text and metadata without page previews")
    args = parser.parse_args()

    pdf = args.pdf.expanduser().resolve()
    out_dir = args.out_dir.expanduser().resolve()
    if not pdf.is_file() or pdf.suffix.lower() != ".pdf":
        raise SystemExit(f"Not a readable PDF: {pdf}")
    if not args.no_render and (args.dpi < 100 or args.dpi > 400):
        raise SystemExit("--dpi must be between 100 and 400")
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "source.json"
    fp = fingerprint(pdf)
    if report_path.is_file() and not args.force:
        try:
            cached = json.loads(report_path.read_text(encoding="utf-8"))
            expected = cached.get("rendered_pages", [])
            if args.no_render:
                renders_ok = cached.get("dpi") is None and not expected
            else:
                renders_ok = (
                    cached.get("dpi") == args.dpi
                    and expected
                    and all((out_dir / name).is_file() for name in expected)
                )
            if (
                cached.get("cache_version") == CACHE_VERSION
                and cached.get("source_pdf") == str(pdf)
                and cached.get("fingerprint") == fp
                and (out_dir / "source.txt").is_file()
                and renders_ok
            ):
                cached["cache_hit"] = True
                print(json.dumps(cached, ensure_ascii=False, indent=2))
                return
        except (OSError, ValueError, TypeError):
            pass

    page_texts: list[str] = []
    page_rows: list[dict[str, object]] = []
    metadata: dict[str, str] = {}
    text_backend = None
    if pdfium is not None:
        pdf_doc = pdfium.PdfDocument(str(pdf))
        try:
            metadata = {str(k): str(v) for k, v in pdf_doc.get_metadata_dict().items() if v}
            for zero_index in range(len(pdf_doc)):
                page = pdf_doc[zero_index]
                text = page.get_textpage().get_text_range() or ""
                width, height = page.get_size()
                page_texts.append(text)
                page_rows.append(
                    {
                        "page": zero_index + 1,
                        "width_pt": float(width),
                        "height_pt": float(height),
                        "characters": len(text),
                    }
                )
        finally:
            pdf_doc.close()
        text_backend = "pypdfium2"
    elif PdfReader is not None:
        reader = PdfReader(pdf)
        metadata = {str(k): str(v) for k, v in (reader.metadata or {}).items()}
        for index, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""
            page_texts.append(text)
            page_rows.append(
                {
                    "page": index,
                    "width_pt": float(page.mediabox.width),
                    "height_pt": float(page.mediabox.height),
                    "characters": len(text),
                }
            )
        text_backend = "pypdf"
    else:
        raise SystemExit("No PDF text backend is available (need pypdfium2 or pypdf)")

    full_text = "\n\n".join(
        f"===== PAGE {index} =====\n\n{text}" for index, text in enumerate(page_texts, 1)
    )
    (out_dir / "source.txt").write_text(full_text, encoding="utf-8")

    rendered: list[str] = []
    if args.no_render:
        render_backend = None
    elif fitz is not None:
        pdf_doc = fitz.open(pdf)
        try:
            for index, page in enumerate(pdf_doc, 1):
                pixmap = page.get_pixmap(dpi=args.dpi, alpha=False)
                name = f"source-page-{index:02d}.png"
                pixmap.save(out_dir / name)
                rendered.append(name)
                page_rows[index - 1]["embedded_images"] = len(page.get_images(full=True))
        finally:
            pdf_doc.close()
        render_backend = "PyMuPDF"
    elif pdfium is not None:
        pdf_doc = pdfium.PdfDocument(str(pdf))
        scale = args.dpi / 72.0
        for zero_index in range(len(pdf_doc)):
            page = pdf_doc[zero_index]
            bitmap = page.render(scale=scale)
            image = bitmap.to_pil().convert("RGB")
            name = f"source-page-{zero_index + 1:02d}.png"
            image.save(out_dir / name, "PNG")
            rendered.append(name)
            page_rows[zero_index]["embedded_images"] = None
        render_backend = "pypdfium2"
    else:
        raise SystemExit("No PDF rendering backend is available (need PyMuPDF or pypdfium2)")

    dois = sorted({clean_doi(match.group(0)) for match in DOI_RE.finditer(full_text)})
    report = {
        "cache_version": CACHE_VERSION,
        "cache_hit": False,
        "source_pdf": str(pdf),
        "fingerprint": fp,
        "dpi": None if args.no_render else args.dpi,
        "page_count": len(page_texts),
        "metadata": metadata,
        "text_backend": text_backend,
        "doi_candidates": dois,
        "text_file": str(out_dir / "source.txt"),
        "rendered_pages": rendered,
        "render_backend": render_backend,
        "pages": page_rows,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
