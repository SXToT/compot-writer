from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

try:
    import fitz  # type: ignore
except ImportError:
    fitz = None

try:
    import pypdfium2 as pdfium  # type: ignore
except ImportError:
    pdfium = None


def pad_to_ratio(image: Image.Image, ratio: float) -> Image.Image:
    current = image.width / image.height
    if abs(current / ratio - 1.0) < 0.002:
        return image
    if current < ratio:
        width = round(image.height * ratio)
        canvas = Image.new("RGB", (width, image.height), "white")
        canvas.paste(image, ((width - image.width) // 2, 0))
        return canvas
    height = round(image.width / ratio)
    canvas = Image.new("RGB", (image.width, height), "white")
    canvas.paste(image, (0, (height - image.height) // 2))
    return canvas


def fingerprint(path: Path) -> dict[str, int]:
    stat = path.stat()
    return {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def crop_key(pdf: Path, item: dict, dpi: int, optimize: bool) -> str:
    payload = {
        "pdf": fingerprint(pdf),
        "item": item,
        "dpi": dpi,
        "optimize": optimize,
        "version": 1,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render all selected PDF regions in one process from a JSON crop specification."
    )
    parser.add_argument("pdf", type=Path)
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--dpi", type=int, default=240)
    parser.add_argument("--optimize", action="store_true", help="Use slower final PNG optimization")
    parser.add_argument("--force", action="store_true", help="Re-render even when the crop cache matches")
    args = parser.parse_args()

    pdf = args.pdf.expanduser().resolve()
    spec_path = args.spec.expanduser().resolve()
    out_dir = args.out_dir.expanduser().resolve()
    if not pdf.is_file() or pdf.suffix.lower() != ".pdf":
        raise SystemExit(f"Not a readable PDF: {pdf}")
    if not spec_path.is_file():
        raise SystemExit(f"Crop specification not found: {spec_path}")
    if not 100 <= args.dpi <= 400:
        raise SystemExit("--dpi must be between 100 and 400")

    payload = json.loads(spec_path.read_text(encoding="utf-8"))
    crops = payload.get("crops") if isinstance(payload, dict) else payload
    if not isinstance(crops, list) or not crops:
        raise SystemExit("Crop specification must be a non-empty list or {'crops': [...]} object")

    out_dir.mkdir(parents=True, exist_ok=True)
    cache_path = out_dir / ".crop-cache.json"
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        if not isinstance(cache, dict):
            cache = {}
    except (OSError, ValueError, TypeError):
        cache = {}
    new_cache = {}
    results = []
    if fitz is None and pdfium is None:
        raise SystemExit("A PDF rendering backend is required (PyMuPDF or pypdfium2)")

    doc = fitz.open(pdf) if fitz is not None else pdfium.PdfDocument(str(pdf))
    try:
        for item in crops:
            if not isinstance(item, dict):
                raise ValueError("Each crop must be an object")
            page_number = int(item["page"])
            output_name = str(item["output"])
            box = item["box"]
            if page_number < 1 or page_number > len(doc):
                raise ValueError(f"Page {page_number} is outside 1..{len(doc)}")
            if not isinstance(box, list) or len(box) != 4:
                raise ValueError(f"Crop {output_name} must provide a four-value box")
            output = out_dir / output_name
            key = crop_key(pdf, item, args.dpi, args.optimize)
            if not args.force and output.is_file() and cache.get(output_name) == key:
                with Image.open(output) as cached_image:
                    results.append(
                        {
                            "output": str(output),
                            "page": page_number,
                            "width": cached_image.width,
                            "height": cached_image.height,
                            "ratio": round(cached_image.width / cached_image.height, 4),
                            "cache_hit": True,
                        }
                    )
                new_cache[output_name] = key
                continue

            page = doc[page_number - 1]
            left, top, right, bottom = (float(value) for value in box)
            relative = bool(item.get("relative", True))
            if relative and not all(0 <= value <= 1 for value in (left, top, right, bottom)):
                raise ValueError(f"Relative crop values for {output_name} must be between 0 and 1")

            if fitz is not None:
                if relative:
                    rect = page.rect
                    clip = fitz.Rect(
                        rect.x0 + left * rect.width,
                        rect.y0 + top * rect.height,
                        rect.x0 + right * rect.width,
                        rect.y0 + bottom * rect.height,
                    )
                else:
                    clip = fitz.Rect(left, top, right, bottom)
                if clip.is_empty or not page.rect.contains(clip):
                    raise ValueError(f"Crop box for {output_name} is invalid or outside page {page_number}")
                pixmap = page.get_pixmap(clip=clip, dpi=args.dpi, alpha=False)
                image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            else:
                width_pt, height_pt = page.get_size()
                if relative:
                    crop = (left * width_pt, top * height_pt, right * width_pt, bottom * height_pt)
                else:
                    crop = (left, top, right, bottom)
                if not (0 <= crop[0] < crop[2] <= width_pt and 0 <= crop[1] < crop[3] <= height_pt):
                    raise ValueError(f"Crop box for {output_name} is invalid or outside page {page_number}")
                # PDFium crop is the amount removed from (left, bottom, right, top),
                # while the specification uses a top-left crop rectangle.
                pdfium_crop = (
                    crop[0],
                    height_pt - crop[3],
                    width_pt - crop[2],
                    crop[1],
                )
                bitmap = page.render(scale=args.dpi / 72.0, crop=pdfium_crop)
                image = bitmap.to_pil().convert("RGB")
            ratio = item.get("ratio")
            if ratio is not None:
                image = pad_to_ratio(image, float(ratio))
            output.parent.mkdir(parents=True, exist_ok=True)
            image.save(output, "PNG", optimize=args.optimize)
            new_cache[output_name] = key
            results.append(
                {
                    "output": str(output),
                    "page": page_number,
                    "width": image.width,
                    "height": image.height,
                    "ratio": round(image.width / image.height, 4),
                    "cache_hit": False,
                }
            )
    finally:
        doc.close()

    cache_path.write_text(json.dumps(new_cache, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"pdf": str(pdf), "dpi": args.dpi, "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
