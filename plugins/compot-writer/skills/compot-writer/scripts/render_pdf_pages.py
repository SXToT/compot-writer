from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pypdfium2 as pdfium


CACHE_VERSION = 1
PAGE_NAME = re.compile(r"page-\d{2,}\.png")


def fingerprint(path: Path) -> dict[str, int]:
    stat = path.stat()
    return {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def render_pages(pdf: Path, out_dir: Path, dpi: int = 160, force: bool = False) -> dict:
    pdf = pdf.expanduser().resolve()
    out_dir = out_dir.expanduser().resolve()
    if not pdf.is_file() or pdf.suffix.lower() != ".pdf":
        raise SystemExit(f"Not a readable PDF: {pdf}")
    if not 100 <= dpi <= 300:
        raise SystemExit("--dpi must be between 100 and 300")
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_path = out_dir / "page-render-cache.json"
    source = {"pdf": str(pdf), "fingerprint": fingerprint(pdf), "dpi": dpi}

    if cache_path.is_file() and not force:
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            outputs = cached.get("outputs", [])
            if (
                cached.get("cache_version") == CACHE_VERSION
                and cached.get("source") == source
                and isinstance(outputs, list)
                and outputs
                and cached.get("page_count") == len(outputs)
                and [item.get("name") for item in outputs if isinstance(item, dict)]
                == [f"page-{i + 1:0{max(2, len(str(len(outputs))))}d}.png" for i in range(len(outputs))]
                and all(
                    isinstance(item, dict)
                    and isinstance(item.get("name"), str)
                    and PAGE_NAME.fullmatch(item["name"])
                    and (out_dir / item["name"]).is_file()
                    and fingerprint(out_dir / item["name"]) == item.get("fingerprint")
                    for item in outputs
                )
            ):
                return {
                    "pdf": str(pdf), "dpi": dpi, "cache_hit": True,
                    "pages": [str(out_dir / item["name"]) for item in outputs],
                }
        except (OSError, ValueError, TypeError, AttributeError):
            pass

    document = pdfium.PdfDocument(str(pdf))
    outputs = []
    try:
        # Restrict cleanup to the numbered outputs owned by this renderer.
        for old in out_dir.glob("page-*.png"):
            if old.is_file() and PAGE_NAME.fullmatch(old.name):
                old.unlink()
        scale = dpi / 72.0
        width = max(2, len(str(len(document))))
        for zero_index in range(len(document)):
            page = document[zero_index]
            bitmap = page.render(scale=scale)
            image = bitmap.to_pil().convert("RGB")
            output = out_dir / f"page-{zero_index + 1:0{width}d}.png"
            image.save(output, "PNG")
            outputs.append({"name": output.name, "fingerprint": fingerprint(output)})
    finally:
        document.close()

    cache_path.write_text(
        json.dumps({"cache_version": CACHE_VERSION, "source": source, "page_count": len(outputs), "outputs": outputs}, indent=2),
        encoding="utf-8",
    )
    return {
        "pdf": str(pdf), "dpi": dpi, "cache_hit": False,
        "pages": [str(out_dir / item["name"]) for item in outputs],
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Render a QA PDF to one PNG per page, with cache reuse.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--dpi", type=int, default=160)
    parser.add_argument("--force", action="store_true", help="Ignore the unchanged PDF/page cache")
    args = parser.parse_args()
    print(json.dumps(render_pages(args.pdf, args.out_dir, args.dpi, args.force), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
