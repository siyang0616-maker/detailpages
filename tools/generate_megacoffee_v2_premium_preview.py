from __future__ import annotations

import math
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


ROOT = Path(r"C:\Users\home\Documents\detailpages")
BASE = ROOT / "franchise-detail-page-outputs" / "20260617-uijeongbu-megacoffee-naver"
ASSETS = BASE / "assets"
OUT = BASE / "v2-premium-preview"

W = H = 1080
YELLOW = (255, 205, 0)
BLACK = (17, 17, 15)
INK = (31, 30, 27)
WARM = (248, 245, 238)
MUTED = (125, 118, 104)
LINE = (226, 221, 211)

FONT_REG = Path(r"C:\Windows\Fonts\NotoSansKR-VF.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\malgunbd.ttf")
FALLBACK_REG = Path(r"C:\Windows\Fonts\malgun.ttf")
FALLBACK_BOLD = Path(r"C:\Windows\Fonts\malgunbd.ttf")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_REG
    if not path.exists():
        path = FALLBACK_BOLD if bold else FALLBACK_REG
    return ImageFont.truetype(str(path), size)


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    size: int,
    fill: tuple[int, int, int],
    bold: bool = False,
    spacing: int = 0,
) -> None:
    draw.multiline_text(xy, text, font=font(size, bold), fill=fill, spacing=spacing)


def cover(path: Path, size: tuple[int, int], focal: tuple[float, float] = (0.5, 0.5)) -> Image.Image:
    img = Image.open(path)
    img = ImageOps.exif_transpose(img).convert("RGB")
    ratio = max(size[0] / img.width, size[1] / img.height)
    resized = img.resize((math.ceil(img.width * ratio), math.ceil(img.height * ratio)), Image.LANCZOS)
    max_left = resized.width - size[0]
    max_top = resized.height - size[1]
    left = int(max(0, min(max_left, max_left * focal[0])))
    top = int(max(0, min(max_top, max_top * focal[1])))
    return resized.crop((left, top, left + size[0], top + size[1]))


def polish(img: Image.Image, saturation: float = 1.05, contrast: float = 1.03, brightness: float = 1.0) -> Image.Image:
    img = ImageEnhance.Color(img).enhance(saturation)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    img = ImageEnhance.Brightness(img).enhance(brightness)
    return img


def gradient_bottom(size: tuple[int, int], strength: int = 215, start: float = 0.42) -> Image.Image:
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    pix = overlay.load()
    for y in range(size[1]):
        t = max(0, (y / size[1] - start) / (1 - start))
        alpha = int(strength * min(1, t**1.45))
        for x in range(size[0]):
            pix[x, y] = (0, 0, 0, alpha)
    return overlay


def rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
    return mask


def paste_rounded(base: Image.Image, img: Image.Image, xy: tuple[int, int], radius: int) -> None:
    mask = rounded_mask(img.size, radius)
    base.paste(img, xy, mask)


def brand_mark(draw: ImageDraw.ImageDraw, dark: bool = False) -> None:
    fill = WARM if dark else INK
    draw.rectangle((72, 70, 124, 76), fill=YELLOW)
    draw_text(draw, (72, 88), "MEGA MGC COFFEE", 20, fill, True)


def safe_footer(draw: ImageDraw.ImageDraw, dark: bool = False) -> None:
    fill = (235, 232, 224) if dark else (118, 111, 101)
    draw_text(draw, (72, 1018), "양도양수 상담/분석용 · 본사 공식 자료 아님", 22, fill, False)


def cut_01() -> Image.Image:
    photo = polish(cover(ASSETS / "exterior-angle.jpg", (W, H), (0.52, 0.5)), 1.08, 1.04, 1.0)
    img = Image.alpha_composite(photo.convert("RGBA"), gradient_bottom((W, H), 230, 0.34)).convert("RGB")
    draw = ImageDraw.Draw(img)

    brand_mark(draw, dark=True)
    draw_text(draw, (72, 690), "의정부\n메가커피", 90, WARM, True, spacing=4)
    draw_text(draw, (76, 898), "월매출 3,500만원 · 창업비용 1.7억원", 34, YELLOW, True)
    draw_text(draw, (76, 952), "신규창업 전, 먼저 비교해볼 조건", 30, WARM, True)
    safe_footer(draw, dark=True)
    return img


def cut_02() -> Image.Image:
    img = Image.new("RGB", (W, H), WARM)
    draw = ImageDraw.Draw(img)
    brand_mark(draw)

    photo = polish(cover(ASSETS / "exterior-main.jpg", (936, 345), (0.5, 0.18)), 1.04, 1.04, 1.0)
    paste_rounded(img, photo, (72, 150), 24)

    draw_text(draw, (72, 560), "조건은 간단하게,\n판단은 구체적으로", 62, INK, True, spacing=6)
    draw_text(draw, (76, 708), "숫자만 보는 매장이 아니라 사진과 자료를 같이 봐야 하는 조건입니다.", 28, MUTED, False)

    metrics = [
        ("월매출", "3,500만원"),
        ("창업비용", "1.7억원"),
        ("입지", "대로변 · 역세권"),
        ("상태", "최신 BI"),
    ]
    y = 798
    for idx, (label, value) in enumerate(metrics):
        x = 72 + (idx % 2) * 468
        yy = y + (idx // 2) * 104
        draw.rounded_rectangle((x, yy, x + 432, yy + 76), radius=18, fill=(255, 255, 255), outline=LINE, width=2)
        draw_text(draw, (x + 28, yy + 20), label, 23, MUTED, False)
        draw_text(draw, (x + 150, yy + 15), value, 30, INK, True)

    safe_footer(draw)
    return img


def cut_05() -> Image.Image:
    img = Image.new("RGB", (W, H), BLACK)
    draw = ImageDraw.Draw(img)
    brand_mark(draw, dark=True)

    photo = polish(cover(ASSETS / "interior-seat.jpg", (936, 720), (0.5, 0.52)), 1.02, 1.03, 1.0)
    paste_rounded(img, photo, (72, 148), 28)

    draw_text(draw, (72, 902), "최신 BI는 첫인상,\n상태 확인은 별도", 48, WARM, True, spacing=4)
    tags = ["내부 마감", "좌석", "조명", "관리 상태"]
    x = 610
    y = 916
    for tag in tags:
        tw, th = text_size(draw, tag, font(22, True))
        draw.rounded_rectangle((x, y, x + tw + 34, y + 46), radius=23, fill=(255, 205, 0))
        draw_text(draw, (x + 17, y + 8), tag, 22, BLACK, True)
        y += 58

    safe_footer(draw, dark=True)
    return img


def make_contact_sheet(paths: list[Path]) -> None:
    sheet = Image.new("RGB", (1120, 420), (255, 255, 255))
    draw = ImageDraw.Draw(sheet)
    for idx, path in enumerate(paths):
        im = Image.open(path).convert("RGB").resize((320, 320), Image.LANCZOS)
        x = 40 + idx * 360
        sheet.paste(im, (x, 36))
        draw_text(draw, (x, 370), path.name, 24, INK, True)
    sheet.save(OUT / "preview-contact-sheet.jpg", quality=94)


def write_copy() -> None:
    text = """의정부 메가커피 v2-premium 미리보기

cut-01.jpg
실제 외관 사진을 크게 사용해 매장감과 브랜드감을 먼저 보여주는 메인 컷입니다.

cut-02.jpg
월매출 3,500만원, 창업비용 1.7억원, 대로변, 역세권, 최신 BI 조건을 간결하게 정리한 컷입니다.

cut-05.jpg
내부 사진을 중심으로 최신 BI와 실제 관리 상태를 함께 확인해야 한다는 메시지를 담은 컷입니다.

본 콘텐츠는 양도양수 상담/분석용이며 본사 공식 자료가 아닙니다.
"""
    (OUT / "naver-upload-copy.txt").write_text(text, encoding="utf-8-sig")
    (OUT / "naver-upload-copy.md").write_text(text, encoding="utf-8")


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)

    outputs = [
        (OUT / "cut-01.jpg", cut_01()),
        (OUT / "cut-02.jpg", cut_02()),
        (OUT / "cut-05.jpg", cut_05()),
    ]
    for path, img in outputs:
        img.save(path, quality=95, optimize=True)
    make_contact_sheet([path for path, _ in outputs])
    write_copy()
    print(OUT)


if __name__ == "__main__":
    main()
