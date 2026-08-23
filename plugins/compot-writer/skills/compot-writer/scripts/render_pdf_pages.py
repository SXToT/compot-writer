from __future__ import annotations

import argparse
import json
from pathlib import Path

import pypdfium2 as pdfium


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a QA PDF to one PNG per page.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--dpi", type=int, default=160)
    args = parser.parse_args()

    pdf = args.pdf.expanduser().resolve()
    out_dir = args.out_dir.expanduser().resolve()
    if not pdf.is_file() or pdf.suffix.lower() != ".pdf":
        raise SystemExit(f"Not a readable PDF: {pdf}")
    if not 100 <= args.dpi <= 300:
        raise SystemExit("--dpi must be between 100 and 300")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Remove only prior outputs created by this script in the same QA directory.
    for old in out_dir.glob("page-*.png"):
        old.unlink()

    document = pdfium.PdfDocument(str(pdf))
    outputs = []
    try:
        scale = args.dpi / 72.0
        width = max(2, len(str(len(document))))
        for zero_index in range(len(document)):
            page = document[zero_index]
            bitmap = page.render(scale=scale)
            image = bitmap.to_pil().convert("RGB")
            output = out_dir / f"page-{zero_index + 1:0{width}d}.png"
            image.save(output, "PNG")
            outputs.append(str(output))
    finally:
        document.close()

    print(json.dumps({"pdf": str(pdf), "dpi": args.dpi, "pages": outputs}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
