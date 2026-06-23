from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image


BANNED_COPY = ["성공 보장", "무조건", "100% 수익", "확정 수익", "본사 추천 매물", "최고 수익", "실패 없음"]


def qa_output(output_dir: Path) -> dict[str, Any]:
    failures: list[str] = []
    jpgs = sorted(path for path in output_dir.glob("cut-*.jpg") if "-photo" not in path.name)
    if not jpgs:
        failures.append("no cut jpg files found")
    usage_path = output_dir / "asset-usage-report.json"
    if not usage_path.exists():
        failures.append("asset-usage-report.json missing")
        usage = {"items": []}
    else:
        usage = json.loads(usage_path.read_text(encoding="utf-8"))
    if not (output_dir / "blog-caption-copy.md").exists():
        failures.append("blog-caption-copy.md missing")
    if not (output_dir / "naver-upload-draft.md").exists():
        failures.append("naver-upload-draft.md missing")
    if not (output_dir / "contact-sheet.jpg").exists():
        failures.append("contact-sheet.jpg missing")

    all_text = ""
    for path in [output_dir / "blog-caption-copy.md", output_dir / "naver-upload-draft.md"]:
        if path.exists():
            all_text += "\n" + path.read_text(encoding="utf-8")
    if "본사 공식 자료가 아닙니다" not in all_text and "상담/분석용" not in all_text:
        failures.append("disclaimer missing")
    for banned in BANNED_COPY:
        if banned in all_text:
            failures.append(f"banned copy appears: {banned}")

    for item in usage.get("items", []):
        if item.get("rights_status") in {"review_required", "disallowed"}:
            failures.append(f"blocked asset used: {item.get('asset_id')} rights={item.get('rights_status')}")
        if item.get("risk_level") in {"high", "disallowed"}:
            failures.append(f"high risk asset used: {item.get('asset_id')} risk={item.get('risk_level')}")
        if not item.get("source_file"):
            failures.append(f"source metadata missing: {item.get('asset_id')}")
        if not item.get("transformed_file"):
            failures.append(f"transformed file missing from usage report: {item.get('asset_id')}")
        targets = set(item.get("masking_targets") or [])
        if {"face", "license_plate", "phone_number", "store_branch_name"} & targets and not item.get("masking_performed"):
            failures.append(f"masking required but not recorded: {item.get('asset_id')}")
        source_name = str(item.get("source_file", "")).lower()
        if "watermark" in source_name:
            failures.append(f"watermark source used: {item.get('asset_id')}")

    for jpg in jpgs:
        try:
            with Image.open(jpg) as image:
                if image.size not in {(1080, 1080), (1080, 1920)}:
                    failures.append(f"wrong output dimensions: {jpg.name} {image.size}")
        except Exception as exc:
            failures.append(f"cannot open output image: {jpg.name}: {exc}")

    layouts = [item.get("layout") for item in usage.get("items", []) if item.get("layout")]
    for layout in set(layouts):
        if layouts.count(layout) >= 3:
            failures.append(f"three or more cards use same layout: {layout}")

    report = {"passed": not failures, "failures": failures, "checked_files": [str(p) for p in jpgs]}
    (output_dir / "qa-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
