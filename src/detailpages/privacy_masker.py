from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

from .asset_registry import AssetRecord, DEFAULT_ASSET_INDEX, asset_index_library_root, read_jsonl, resolve_asset_path, write_jsonl


def _blur_box(image: Image.Image, box: tuple[int, int, int, int], radius: int = 18) -> None:
    x1, y1, x2, y2 = box
    region = image.crop((x1, y1, x2, y2)).filter(ImageFilter.GaussianBlur(radius))
    image.paste(region, (x1, y1))


def mask_image(record: AssetRecord, asset_index: Path = DEFAULT_ASSET_INDEX) -> tuple[Path | None, list[str]]:
    library_root = asset_index_library_root(asset_index)
    source = resolve_asset_path(record, library_root)
    if not source.exists():
        record.notes = (record.notes + "; source missing during masking").strip("; ")
        return None, []
    if not record.needs_masking:
        return None, []

    out_dir = library_root / "reviewed" / "masked"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{record.asset_id}{source.suffix.lower() if source.suffix else '.jpg'}"
    with Image.open(source) as original:
        image = ImageOps.exif_transpose(original).convert("RGB")
    w, h = image.size
    performed: list[str] = []
    targets = set(record.masking_targets)

    if "face" in targets:
        _blur_box(image, (w // 4, h // 8, w * 3 // 4, h * 2 // 3), radius=28)
        performed.append("face_center_region_blur")
    if "phone_number" in targets or "staff_name_tag" in targets or "private_document" in targets:
        _blur_box(image, (0, 0, w, max(80, h // 8)), radius=20)
        _blur_box(image, (0, h - max(90, h // 8), w, h), radius=20)
        performed.append("top_bottom_text_zone_blur")
    if "license_plate" in targets or "store_branch_name" in targets or "map_pin" in targets:
        _blur_box(image, (0, 0, w, max(95, h // 7)), radius=18)
        performed.append("signage_address_zone_blur")
    if "third_party_poster_or_campaign" in targets:
        _blur_box(image, (w // 10, h // 10, w * 9 // 10, h * 9 // 10), radius=12)
        performed.append("poster_area_soft_blur")

    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, min(w - 10, 360), 48), fill=(0, 0, 0))
    draw.text((20, 18), "MASKED REVIEW COPY", fill=(255, 255, 255))
    image.save(out_path, quality=92)

    record.masking_performed.append({"output_file": str(out_path.relative_to(library_root)), "targets": sorted(targets), "actions": performed})
    record.notes = (record.notes + "; automated masking is conservative and needs human QA").strip("; ")
    return out_path, performed


def mask_assets(asset_index: Path = DEFAULT_ASSET_INDEX) -> list[AssetRecord]:
    records = read_jsonl(asset_index)
    for record in records:
        mask_image(record, asset_index)
    write_jsonl(asset_index, records)
    return records

