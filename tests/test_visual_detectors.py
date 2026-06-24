from __future__ import annotations

import unittest

from PIL import Image, ImageDraw, ImageFont

from detailpages.visual_detectors import detect_faces, detect_text_regions


class VisualDetectorsTest(unittest.TestCase):
    def test_detect_faces_on_plain_image_returns_empty_list(self) -> None:
        image = Image.new("RGB", (240, 180), (220, 220, 220))

        self.assertEqual(detect_faces(image), [])

    def test_detect_text_regions_on_rendered_text_returns_containing_box(self) -> None:
        image = Image.new("RGB", (420, 180), "white")
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()
        draw.text((80, 72), "CALL 010-1234-5678", fill="black", font=font)

        boxes = detect_text_regions(image)

        self.assertTrue(boxes)
        self.assertTrue(any(left <= 95 and top <= 85 and right >= 170 and bottom >= 80 for left, top, right, bottom in boxes), boxes)

    def test_detectors_never_raise_on_tiny_image(self) -> None:
        image = Image.new("RGB", (1, 1), "white")

        self.assertIsInstance(detect_faces(image), list)
        self.assertIsInstance(detect_text_regions(image), list)


if __name__ == "__main__":
    unittest.main()
