from __future__ import annotations

import csv
from pathlib import Path

from PIL import Image, ImageOps

from .asset_classifier import classify_path
from .asset_registry import (
    AssetRecord,
    DEFAULT_ASSET_INDEX,
    DEFAULT_LIBRARY_ROOT,
    ensure_library_dirs,
    is_image,
    next_asset_id,
    read_jsonl,
    sha256_file,
    write_jsonl,
)


def _relative_or_absolute(path: Path, library_root: Path) -> str:
    try:
        return path.resolve().relative_to(library_root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _image_size(path: Path) -> tuple[int | None, int | None]:
    try:
        with Image.open(path) as image:
            return image.size
    except Exception:
        return None, None


def _thumbnail(path: Path, out: Path, size: tuple[int, int] = (360, 240)) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail(size)
        canvas = Image.new("RGB", size, "white")
        canvas.paste(image, ((size[0] - image.width) // 2, (size[1] - image.height) // 2))
        canvas.save(out, quality=88)


def make_contact_sheet(records: list[AssetRecord], asset_index: Path = DEFAULT_ASSET_INDEX, limit: int = 60) -> Path | None:
    if not records:
        return None
    library_root = asset_index.parent.parent if asset_index.parent.name == "manifests" else DEFAULT_LIBRARY_ROOT
    thumbs_dir = library_root / "reviewed" / "thumbnails"
    sheet_dir = library_root / "reviewed" / "contact-sheets"
    sheet_dir.mkdir(parents=True, exist_ok=True)
    tile_w, tile_h = 240, 190
    cols = 5
    picked = records[:limit]
    rows = (len(picked) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tile_w, rows * tile_h + 48), "#f5f5f5")
    from PIL import ImageDraw, ImageFont

    draw = ImageDraw.Draw(sheet)
    try:
        fnt = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 16)
    except Exception:
        fnt = ImageFont.load_default()
    draw.text((16, 14), f"Asset review contact sheet ({len(picked)} of {len(records)})", fill="#111", font=fnt)
    for idx, record in enumerate(picked):
        thumb = thumbs_dir / f"{record.asset_id}.jpg"
        if not thumb.exists():
            continue
        with Image.open(thumb).convert("RGB") as image:
            x = (idx % cols) * tile_w
            y = 48 + (idx // cols) * tile_h
            sheet.paste(image.resize((tile_w, 150)), (x, y))
            draw.text((x + 8, y + 154), f"{record.asset_id} | {record.category} | {record.risk_level}", fill="#222", font=fnt)
    out = sheet_dir / "contact-sheet-001.jpg"
    sheet.save(out, quality=90)
    return out


def ingest_assets(
    input_dir: Path,
    output: Path = DEFAULT_ASSET_INDEX,
    source_type: str = "unknown",
    source_url: str = "",
) -> list[AssetRecord]:
    library_root = output.parent.parent if output.parent.name == "manifests" else DEFAULT_LIBRARY_ROOT
    ensure_library_dirs(library_root)

    existing = read_jsonl(output)
    by_hash = {record.file_sha256: record for record in existing if record.file_sha256}
    records = list(existing)
    new_records: list[AssetRecord] = []
    next_id = next_asset_id(records)
    next_num = int(next_id.split("_")[-1])

    for path in sorted(input_dir.rglob("*")):
        if not is_image(path):
            continue
        digest = sha256_file(path)
        if digest in by_hash:
            continue
        classification = classify_path(path, source_type=source_type)
        width, height = _image_size(path)
        record = AssetRecord(
            asset_id=f"asset_{next_num:06d}",
            original_file=_relative_or_absolute(path, library_root),
            source_type=source_type,
            source_url=source_url,
            file_sha256=digest,
            width=width,
            height=height,
            notes="auto-ingested; manual approval required before rendering" if source_type == "unknown" else "",
            **classification,
        )
        records.append(record)
        by_hash[digest] = record
        new_records.append(record)
        next_num += 1
        try:
            _thumbnail(path, library_root / "reviewed" / "thumbnails" / f"{record.asset_id}.jpg")
        except Exception as exc:
            record.notes = (record.notes + f"; thumbnail failed: {exc}").strip("; ")

    write_jsonl(output, records)
    make_contact_sheet(new_records or records, output)
    return new_records


def make_review_sheet(asset_index: Path = DEFAULT_ASSET_INDEX, output_csv: Path | None = None) -> Path:
    library_root = asset_index.parent.parent if asset_index.parent.name == "manifests" else DEFAULT_LIBRARY_ROOT
    output_csv = output_csv or library_root / "review-sheet.csv"
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    rows = read_jsonl(asset_index)
    fields = [
        "asset_id",
        "original_file",
        "brand_detected",
        "category",
        "visual_role",
        "source_type",
        "source_url",
        "rights_status",
        "commercial_use_allowed",
        "derivative_allowed",
        "needs_masking",
        "masking_targets",
        "risk_level",
        "approved_for_generation",
        "notes",
    ]
    with output_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for record in rows:
            data = record.to_dict()
            data["masking_targets"] = ",".join(record.masking_targets)
            writer.writerow({field: data.get(field, "") for field in fields})
    return output_csv

