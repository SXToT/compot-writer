from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


SLOT_RATIOS = {
    "封面": 4.301,
    "图片1": 1.680,
    "图片2": 2.098,
    "图片3": 0.967,
    "图片4": 1.729,
    "表1": 1.603,
    "图片5": 2.119,
}


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Crop a rendered PDF page into a Word image slot.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--box", nargs=4, type=float, metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"), required=True)
    parser.add_argument("--relative", action="store_true", help="Interpret box values as fractions from 0 to 1")
    parser.add_argument("--slot", choices=sorted(SLOT_RATIOS), help="Pad with white to the exact template-slot ratio")
    args = parser.parse_args()

    source = args.input.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not source.is_file():
        raise SystemExit(f"Image not found: {source}")

    image = Image.open(source).convert("RGB")
    left, top, right, bottom = args.box
    if args.relative:
        if not all(0 <= value <= 1 for value in args.box):
            raise SystemExit("Relative coordinates must be between 0 and 1")
        left, right = left * image.width, right * image.width
        top, bottom = top * image.height, bottom * image.height
    box = tuple(round(value) for value in (left, top, right, bottom))
    if not (0 <= box[0] < box[2] <= image.width and 0 <= box[1] < box[3] <= image.height):
        raise SystemExit(f"Crop box {box} is outside image size {image.size}")

    cropped = image.crop(box)
    if args.slot:
        cropped = pad_to_ratio(cropped, SLOT_RATIOS[args.slot])
    output.parent.mkdir(parents=True, exist_ok=True)
    cropped.save(output, "PNG", optimize=True)
    print(f"{output} {cropped.width}x{cropped.height} ratio={cropped.width / cropped.height:.3f}")


if __name__ == "__main__":
    main()
