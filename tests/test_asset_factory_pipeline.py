from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]


def make_image(path: Path, color: tuple[int, int, int], label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (900, 650), color)
    draw = ImageDraw.Draw(image)
    draw.rectangle((80, 80, 820, 220), fill=(255, 255, 255))
    draw.text((120, 125), label, fill=(0, 0, 0))
    image.save(path)


class AssetFactoryPipelineTest(unittest.TestCase):
    def test_ingest_approve_mask_render_and_qa(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            lib = base / "data" / "asset_library"
            raw = lib / "raw"
            asset_index = lib / "manifests" / "asset-index.jsonl"
            project = base / "data" / "projects" / "sample-compose" / "manifest.json"

            make_image(raw / "composecoffee" / "01-exterior-signage" / "front.jpg", (240, 180, 0), "COMPOSE EXTERIOR")
            make_image(raw / "composecoffee" / "02-interior-seating" / "inside.jpg", (60, 60, 60), "COMPOSE INTERIOR")
            make_image(raw / "composecoffee" / "03-counter-kiosk-order" / "counter.jpg", (80, 70, 40), "COMPOSE COUNTER")
            make_image(raw / "composecoffee" / "05-food-drink-menu" / "drink.jpg", (220, 210, 190), "COMPOSE MENU")

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "detailpages.cli",
                    "ingest-assets",
                    "--input",
                    str(raw),
                    "--output",
                    str(asset_index),
                    "--source-type",
                    "self_shot",
                ],
                cwd=ROOT,
                check=True,
            )
            subprocess.run(
                [sys.executable, "-m", "detailpages.cli", "make-review-sheet", "--asset-index", str(asset_index)],
                cwd=ROOT,
                check=True,
            )
            review_sheet = lib / "review-sheet.csv"
            with review_sheet.open("r", encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
            for row in rows:
                row["rights_status"] = "owned"
                row["commercial_use_allowed"] = "true"
                row["derivative_allowed"] = "true"
                row["approved_for_generation"] = "true"
                if row["risk_level"] == "high":
                    row["approved_for_generation"] = "false"
            with review_sheet.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "detailpages.cli",
                    "approve-assets",
                    "--review-sheet",
                    str(review_sheet),
                    "--asset-index",
                    str(asset_index),
                ],
                cwd=ROOT,
                check=True,
            )
            subprocess.run(
                [sys.executable, "-m", "detailpages.cli", "mask-assets", "--asset-index", str(asset_index)],
                cwd=ROOT,
                check=True,
            )

            project.parent.mkdir(parents=True, exist_ok=True)
            project.write_text(
                json.dumps(
                    {
                        "project_slug": "sample-compose",
                        "asset_index": str(asset_index),
                        "output_root": str(base / "outputs"),
                        "brand": "컴포즈커피",
                        "region": "테스트구",
                        "monthly_sales": "확인 필요",
                        "startup_cost": "확인 필요",
                        "consultant": {"phone": "010-4359-7864", "name": "양승인", "title": "과장", "show_name": False},
                        "asset_query": {
                            "brand": "컴포즈커피",
                            "categories": ["exterior", "interior", "counter", "menu"],
                            "rights_status": ["owned"],
                            "risk_level_max": "medium",
                            "approved_for_generation": True,
                        },
                        "visual_preset": "realistic_store_review",
                        "output": {"sizes": ["1080x1080"], "card_count": 10, "format": "jpg"},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            subprocess.run([sys.executable, "-m", "detailpages.cli", "render-preview", "--manifest", str(project)], cwd=ROOT, check=True)
            subprocess.run([sys.executable, "-m", "detailpages.cli", "render-full", "--manifest", str(project)], cwd=ROOT, check=True)
            output = base / "outputs" / "sample-compose" / "latest"
            subprocess.run([sys.executable, "-m", "detailpages.cli", "qa", "--output", str(output)], cwd=ROOT, check=True)

            jpgs = sorted(path for path in output.glob("cut-*.jpg") if "-photo" not in path.name)
            self.assertEqual(len(jpgs), 10)
            self.assertTrue((output / "asset-usage-report.json").exists())
            self.assertTrue((output / "qa-report.json").exists())
            report = json.loads((output / "qa-report.json").read_text(encoding="utf-8"))
            self.assertTrue(report["passed"], report["failures"])


if __name__ == "__main__":
    unittest.main()
