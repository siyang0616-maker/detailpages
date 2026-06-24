from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat

from detailpages.asset_registry import AssetRecord
from detailpages.privacy_masker import mask_image


def _write_text_image(path: Path) -> None:
    image = Image.new("RGB", (420, 220), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    for offset in range(0, 80, 14):
        draw.text((160, 118 + offset // 8), f"010-1234-56{offset:02d}", fill="black", font=font)
    image.save(path)


def _region_difference(original: Image.Image, masked: Image.Image, box: tuple[int, int, int, int]) -> float:
    diff = ImageChops.difference(original.crop(box), masked.crop(box)).convert("L")
    return float(ImageStat.Stat(diff).mean[0])


class PrivacyMaskerDetectionTest(unittest.TestCase):
    def test_mask_image_blurs_detected_text_region_not_only_fixed_strip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            library_root = base / "asset_library"
            source = library_root / "raw" / "phone.jpg"
            source.parent.mkdir(parents=True)
            _write_text_image(source)
            asset_index = library_root / "manifests" / "asset-index.jsonl"

            record = AssetRecord(
                asset_id="asset_000001",
                original_file="raw/phone.jpg",
                needs_masking=True,
                masking_targets=["phone_number"],
                risk_level="medium",
            )

            out_path, performed = mask_image(record, asset_index)

            self.assertIsNotNone(out_path)
            self.assertIn("text_detected_region_blur", performed)
            with Image.open(source).convert("RGB") as original, Image.open(out_path).convert("RGB") as masked:
                text_change = _region_difference(original, masked, (150, 105, 330, 170))
                top_strip_change = _region_difference(original, masked, (370, 10, 415, 55))
            self.assertGreater(text_change, 1.0)
            self.assertLess(top_strip_change, text_change)
            self.assertEqual(record.masking_performed[-1]["detection_used"]["text_regions_detected"], 1)

    def test_detected_face_overrides_missing_folder_target_and_escalates_risk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            library_root = base / "asset_library"
            source = library_root / "raw" / "interior.jpg"
            source.parent.mkdir(parents=True)
            image = Image.new("RGB", (320, 220), (210, 210, 210))
            draw = ImageDraw.Draw(image)
            draw.rectangle((120, 70, 200, 150), fill=(20, 20, 20))
            image.save(source)
            asset_index = library_root / "manifests" / "asset-index.jsonl"

            record = AssetRecord(
                asset_id="asset_000002",
                original_file="raw/interior.jpg",
                category="interior",
                needs_masking=False,
                masking_targets=[],
                risk_level="low",
            )

            with patch("detailpages.privacy_masker.detect_faces", return_value=[(120, 70, 200, 150)]), patch(
                "detailpages.privacy_masker.detect_text_regions", return_value=[]
            ):
                out_path, performed = mask_image(record, asset_index)

            self.assertIsNotNone(out_path)
            self.assertIn("face_detected_region_blur", performed)
            self.assertTrue(record.needs_masking)
            self.assertEqual(record.risk_level, "high")
            self.assertEqual(record.masking_performed[-1]["detection_used"]["faces_detected"], 1)


if __name__ == "__main__":
    unittest.main()
