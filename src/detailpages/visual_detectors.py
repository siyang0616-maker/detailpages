from __future__ import annotations

from PIL import Image, ImageOps


Box = tuple[int, int, int, int]


def _clamp_box(box: Box, width: int, height: int) -> Box | None:
    left, top, right, bottom = box
    left = max(0, min(width, int(left)))
    top = max(0, min(height, int(top)))
    right = max(0, min(width, int(right)))
    bottom = max(0, min(height, int(bottom)))
    if right <= left or bottom <= top:
        return None
    return left, top, right, bottom


def _intersects_or_near(a: Box, b: Box, gap: int = 8) -> bool:
    return not (a[2] + gap < b[0] or b[2] + gap < a[0] or a[3] + gap < b[1] or b[3] + gap < a[1])


def _merge_boxes(boxes: list[Box], gap: int = 8) -> list[Box]:
    merged: list[Box] = []
    for box in boxes:
        current = box
        changed = True
        while changed:
            changed = False
            keep: list[Box] = []
            for existing in merged:
                if _intersects_or_near(current, existing, gap=gap):
                    current = (
                        min(current[0], existing[0]),
                        min(current[1], existing[1]),
                        max(current[2], existing[2]),
                        max(current[3], existing[3]),
                    )
                    changed = True
                else:
                    keep.append(existing)
            merged = keep
        merged.append(current)
    return sorted(merged, key=lambda item: (item[1], item[0]))


def detect_faces(image: "Image.Image") -> list[Box]:
    """Return face boxes as (left, top, right, bottom). Never raises."""
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore

        rgb = ImageOps.exif_transpose(image).convert("RGB")
        width, height = rgb.size
        if width < 24 or height < 24:
            return []
        gray = cv2.cvtColor(np.array(rgb), cv2.COLOR_RGB2GRAY)
        cascade_names = ["haarcascade_frontalface_default.xml", "haarcascade_frontalface_alt2.xml", "haarcascade_profileface.xml"]
        boxes: list[Box] = []
        for name in cascade_names:
            cascade_path = cv2.data.haarcascades + name
            cascade = cv2.CascadeClassifier(cascade_path)
            if cascade.empty():
                continue
            detected = cascade.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=4, minSize=(24, 24))
            for x, y, w, h in detected:
                clamped = _clamp_box((x, y, x + w, y + h), width, height)
                if clamped:
                    boxes.append(clamped)
        return _merge_boxes(boxes, gap=12)
    except Exception:
        return []


def _merge_text_line_boxes(boxes: list[Box]) -> list[Box]:
    if not boxes:
        return []
    boxes = sorted(boxes, key=lambda item: (item[1], item[0]))
    lines: list[list[Box]] = []
    for box in boxes:
        center_y = (box[1] + box[3]) / 2
        placed = False
        for line in lines:
            line_top = min(item[1] for item in line)
            line_bottom = max(item[3] for item in line)
            line_center = (line_top + line_bottom) / 2
            tolerance = max(10, (line_bottom - line_top) * 0.9)
            if abs(center_y - line_center) <= tolerance:
                line.append(box)
                placed = True
                break
        if not placed:
            lines.append([box])

    merged: list[Box] = []
    for line in lines:
        line = sorted(line, key=lambda item: item[0])
        groups: list[Box] = []
        current = line[0]
        for box in line[1:]:
            gap = box[0] - current[2]
            if gap <= max(45, (current[3] - current[1]) * 3):
                current = (min(current[0], box[0]), min(current[1], box[1]), max(current[2], box[2]), max(current[3], box[3]))
            else:
                groups.append(current)
                current = box
        groups.append(current)
        merged.extend(groups)
    return _merge_boxes(merged, gap=4)


def _detect_text_by_contrast(image: Image.Image) -> list[Box]:
    """Small dependency-free fallback for high-contrast printed text regions."""
    try:
        gray = ImageOps.exif_transpose(image).convert("L")
        width, height = gray.size
        if width < 2 or height < 2:
            return []
        pixels = gray.load()
        dark_points: list[tuple[int, int]] = []
        step = 1
        for y in range(0, height, step):
            for x in range(0, width, step):
                if pixels[x, y] < 100:
                    dark_points.append((x, y))
        if not dark_points:
            return []

        visited: set[tuple[int, int]] = set()
        components: list[Box] = []
        dark = set(dark_points)
        for point in dark_points:
            if point in visited:
                continue
            stack = [point]
            visited.add(point)
            xs: list[int] = []
            ys: list[int] = []
            while stack:
                x, y = stack.pop()
                xs.append(x)
                ys.append(y)
                for nx in (x - 1, x, x + 1):
                    for ny in (y - 1, y, y + 1):
                        neighbor = (nx, ny)
                        if neighbor in dark and neighbor not in visited:
                            visited.add(neighbor)
                            stack.append(neighbor)
            left, right = min(xs), max(xs) + 1
            top, bottom = min(ys), max(ys) + 1
            comp_w = right - left
            comp_h = bottom - top
            if 1 <= comp_w <= width * 0.75 and 3 <= comp_h <= height * 0.35:
                components.append((left, top, right, bottom))
        text_like = [box for box in components if (box[2] - box[0]) <= 80 and (box[3] - box[1]) <= 80]
        return _merge_text_line_boxes(text_like)
    except Exception:
        return []


def detect_text_regions(image: "Image.Image") -> list[Box]:
    """Return likely text boxes as (left, top, right, bottom). Never raises."""
    try:
        import pytesseract  # type: ignore
        from pytesseract import Output  # type: ignore

        rgb = ImageOps.exif_transpose(image).convert("RGB")
        width, height = rgb.size
        if width < 2 or height < 2:
            return []
        data = pytesseract.image_to_data(rgb, output_type=Output.DICT)
        boxes: list[Box] = []
        for idx, raw_conf in enumerate(data.get("conf", [])):
            try:
                confidence = float(raw_conf)
            except (TypeError, ValueError):
                continue
            text = str(data.get("text", [""])[idx]).strip()
            if confidence < 40 or not text:
                continue
            left = int(data["left"][idx])
            top = int(data["top"][idx])
            w = int(data["width"][idx])
            h = int(data["height"][idx])
            clamped = _clamp_box((left, top, left + w, top + h), width, height)
            if clamped:
                boxes.append(clamped)
        if boxes:
            return _merge_text_line_boxes(boxes)
    except Exception:
        pass
    return _detect_text_by_contrast(image)
