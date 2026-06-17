from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "generate_megacoffee_v2_premium_preview.py"
OUT = ROOT / "franchise-detail-page-outputs" / "20260617-uijeongbu-megacoffee-naver" / "v2-premium-preview"


class MegaCoffeeV2PreviewTest(unittest.TestCase):
    def test_preview_generates_three_square_jpgs_and_utf8_bom_copy(self) -> None:
        subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)

        jpgs = sorted(OUT.glob("cut-*.jpg"))
        self.assertEqual([p.name for p in jpgs], ["cut-01.jpg", "cut-02.jpg", "cut-05.jpg"])
        for jpg in jpgs:
            with Image.open(jpg) as image:
                self.assertEqual(image.size, (1080, 1080))
                self.assertEqual(image.mode, "RGB")

        txt = OUT / "naver-upload-copy.txt"
        self.assertTrue(txt.exists())
        raw = txt.read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        text = raw.decode("utf-8-sig")
        self.assertIn("의정부 메가커피", text)
        self.assertIn("월매출 3,500만원", text)
        self.assertIn("본사 공식 자료가 아닙니다", text)


if __name__ == "__main__":
    unittest.main()
