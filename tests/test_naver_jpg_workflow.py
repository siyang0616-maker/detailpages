from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "franchise-detail-page-outputs" / "20260617-uijeongbu-megacoffee-naver"
CUTS = OUTPUT / "cuts-jpg"
SCRIPT = ROOT / "tools" / "generate_naver_franchise_jpgs.py"


class NaverJpgWorkflowTest(unittest.TestCase):
    def test_generator_creates_square_jpg_cards_and_caption_copy(self) -> None:
        subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)

        jpgs = sorted(CUTS.glob("cut-*.jpg"))
        self.assertEqual(len(jpgs), 12)
        self.assertEqual([p.name for p in jpgs], [f"cut-{i:02d}.jpg" for i in range(1, 13)])

        for jpg in jpgs:
            with Image.open(jpg) as image:
                self.assertEqual(image.size, (1080, 1080))
                self.assertEqual(image.mode, "RGB")

        caption_copy = OUTPUT / "blog-caption-copy.md"
        self.assertTrue(caption_copy.exists())
        text = caption_copy.read_text(encoding="utf-8")
        self.assertIn("# 의정부 메가커피", text)
        for i in range(1, 13):
            self.assertIn(f"## cut-{i:02d}", text)
        self.assertIn("본 콘텐츠는 양도양수 상담/분석용이며 본사 공식 자료가 아닙니다.", text)


if __name__ == "__main__":
    unittest.main()
