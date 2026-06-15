#!/usr/bin/env python
"""Create batched contact sheets for large local photo folders."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create batched contact sheets.")
    parser.add_argument("image_dir", help="Folder containing source images")
    parser.add_argument("output_dir", help="Folder to write contact sheets")
    parser.add_argument("--prefix", default="contact-sheet")
    parser.add_argument("--batch-size", type=int, default=40)
    parser.add_argument("--thumb-width", type=int, default=240)
    parser.add_argument("--thumb-height", type=int, default=220)
    parser.add_argument("--columns", type=int, default=4)
    return parser.parse_args()


def make_sheet(files: list[Path], output: Path, args: argparse.Namespace) -> None:
    label_h = 46
    cell_w = args.thumb_width
    cell_h = args.thumb_height + label_h
    rows = math.ceil(len(files) / args.columns)
    sheet = Image.new("RGB", (args.columns * cell_w, rows * cell_h), "white")
    draw = ImageDraw.Draw(sheet)

    for index, path in enumerate(files, 1):
        with Image.open(path) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
            img.thumbnail((args.thumb_width, args.thumb_height))
            col = (index - 1) % args.columns
            row = (index - 1) // args.columns
            x = col * cell_w + (cell_w - img.width) // 2
            y = row * cell_h + (args.thumb_height - img.height) // 2
            sheet.paste(img, (x, y))
            label = path.name
            draw.text((col * cell_w + 8, row * cell_h + args.thumb_height + 8), label[:34], fill="black")

    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=92)


def main() -> None:
    args = parse_args()
    image_dir = Path(args.image_dir)
    output_dir = Path(args.output_dir)
    files = sorted(
        [p for p in image_dir.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONS],
        key=lambda p: p.name.lower(),
    )
    if not files:
        raise SystemExit(f"No images found in {image_dir}")

    outputs = []
    for batch_index in range(0, len(files), args.batch_size):
        batch = files[batch_index : batch_index + args.batch_size]
        sheet_number = batch_index // args.batch_size + 1
        output = output_dir / f"{args.prefix}-{sheet_number:02d}.jpg"
        make_sheet(batch, output, args)
        outputs.append(output)

    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
