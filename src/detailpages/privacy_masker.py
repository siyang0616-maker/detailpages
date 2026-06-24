from __future__ import annotations

from pathlib import Path
import shutil
import importlib.util

from PIL import Image, ImageDraw, ImageFilter, ImageOps

from .asset_registry import AssetRecord, DEFAULT_ASSET_INDEX, RISK_ORDER, asset_index_library_root, read_jsonl, resolve_asset_path, write_jsonl
from .visual_detectors import detect_faces, detect_text_regions


def _blur_box(image: Image.Image, box: tuple[int, int, int, int], radius: int = 18) -> None:
    w, h = image.size
    x1, y1, x2, y2 = box
    x1 = max(0, min(w, x1))
    y1 = max(0, min(h, y1))
    x2 = max(0, min(w, x2))
    y2 = max(0, min(h, y2))
    if x2 <= x1 or y2 <= y1:
        return
    region = image.crop((x1, y1, x2, y2)).filter(ImageFilter.GaussianBlur(radius))
    image.paste(region, (x1, y1))


def _raise_risk_at_least(record: AssetRecord, level: str) -> None:
    if RISK_ORDER.get(record.risk_level, 0) < RISK_ORDER[level]:
        record.risk_level = level


def _append_note(record: AssetRecord, note: str) -> None:
    notes = [item.strip() for item in record.notes.split(";") if item.strip()]
    if note not in notes:
        notes.append(note)
    record.notes = "; ".join(notes)


def _detection_unavailable_notes() -> list[str]:
    notes: list[str] = []
    if importlib.util.find_spec("cv2") is None:
        notes.append("cv_detection_unavailable")
    if importlib.util.find_spec("pytesseract") is None or shutil.which("tesseract") is None:
        notes.append("ocr_detection_unavailable")
    return notes


def mask_image(record: AssetRecord, asset_index: Path = DEFAULT_ASSET_INDEX) -> tuple[Path | None, list[str]]:
    library_root = asset_index_library_root(asset_index)
    source = resolve_asset_path(record, library_root)
    if not source.exists():
        record.notes = (record.notes + "; source missing during masking").strip("; ")
        return None, []

    out_dir = library_root / "reviewed" / "masked"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{record.asset_id}{source.suffix.lower() if source.suffix else '.jpg'}"
    with Image.open(source) as original:
        image = ImageOps.exif_transpose(original).convert("RGB")
    w, h = image.size
    performed: list[str] = []
    targets = set(record.masking_targets)
    unavailable_notes = _detection_unavailable_notes()
    for note in unavailable_notes:
        _append_note(record, note)

    face_boxes = detect_faces(image)
    text_boxes = detect_text_regions(image)
    detection_used = {"faces_detected": len(face_boxes), "text_regions_detected": len(text_boxes)}
    text_targets = {"phone_number", "staff_name_tag", "private_document", "license_plate", "store_branch_name", "map_pin"}

    if face_boxes:
        record.needs_masking = True
        targets.add("face")
        record.masking_targets = sorted(targets)
        _raise_risk_at_least(record, "high")

    if text_boxes:
        record.needs_masking = True
        if not (targets & text_targets):
            targets.add("detected_text")
        record.masking_targets = sorted(targets)
        _raise_risk_at_least(record, "medium")

    if not record.needs_masking and not face_boxes and not text_boxes:
        return None, []

    if face_boxes:
        for box in face_boxes:
            _blur_box(image, box, radius=28)
        performed.append("face_detected_region_blur")
    elif "face" in targets:
        _blur_box(image, (w // 4, h // 8, w * 3 // 4, h * 2 // 3), radius=28)
        performed.append("face_center_region_blur")

    if text_boxes:
        for box in text_boxes:
            pad_x = max(4, (box[2] - box[0]) // 10)
            pad_y = max(4, (box[3] - box[1]) // 2)
            _blur_box(image, (box[0] - pad_x, box[1] - pad_y, box[2] + pad_x, box[3] + pad_y), radius=20)
        performed.append("text_detected_region_blur")
    elif "phone_number" in targets or "staff_name_tag" in targets or "private_document" in targets:
        _blur_box(image, (0, 0, w, max(80, h // 8)), radius=20)
        _blur_box(image, (0, h - max(90, h // 8), w, h), radius=20)
        performed.append("top_bottom_text_zone_blur")
    if not text_boxes and ("license_plate" in targets or "store_branch_name" in targets or "map_pin" in targets):
        _blur_box(image, (0, 0, w, max(95, h // 7)), radius=18)
        performed.append("signage_address_zone_blur")
    if "third_party_poster_or_campaign" in targets:
        _blur_box(image, (w // 10, h // 10, w * 9 // 10, h * 9 // 10), radius=12)
        performed.append("poster_area_soft_blur")

    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, min(w - 10, 360), 48), fill=(0, 0, 0))
    draw.text((20, 18), "MASKED REVIEW COPY", fill=(255, 255, 255))
    image.save(out_path, quality=92)

    record.masking_performed.append(
        {
            "output_file": str(out_path.relative_to(library_root)),
            "targets": sorted(targets),
            "actions": performed,
            "detection_used": detection_used,
        }
    )
    _append_note(record, "automated masking is conservative and needs human QA")
    return out_path, performed


def mask_assets(asset_index: Path = DEFAULT_ASSET_INDEX) -> list[AssetRecord]:
    records = read_jsonl(asset_index)
    for record in records:
        mask_image(record, asset_index)
    write_jsonl(asset_index, records)
    return records

