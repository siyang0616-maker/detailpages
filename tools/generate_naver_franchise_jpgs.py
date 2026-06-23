from __future__ import annotations

import math
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "franchise-detail-page-outputs" / "20260617-uijeongbu-megacoffee-naver"
ASSETS = OUT / "assets"
CUTS = OUT / "cuts-jpg"

FONT_CANDIDATES_REG = [
    Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
    Path("/System/Library/Fonts/Supplemental/AppleGothic.ttf"),
    Path("/System/Library/Fonts/Supplemental/NotoSansGothic-Regular.ttf"),
    Path(r"C:\Windows\Fonts\malgun.ttf"),
]
FONT_CANDIDATES_BOLD = [
    Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
    Path("/System/Library/Fonts/Supplemental/AppleGothic.ttf"),
    Path(r"C:\Windows\Fonts\malgunbd.ttf"),
    Path(r"C:\Windows\Fonts\malgun.ttf"),
]

W = H = 1080
BG = (47, 20, 12)
BG_2 = (34, 16, 11)
YELLOW = (255, 205, 28)
INK = (24, 19, 15)
WHITE = (255, 255, 255)
SOFT = (245, 240, 230)
GRAY = (219, 219, 219)


@dataclass(frozen=True)
class Cut:
    kind: str
    image: str | None
    eyebrow: str
    title: str
    body: list[str]
    table: list[tuple[str, str]] | None = None


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES_BOLD if bold else FONT_CANDIDATES_REG:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def text_box(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont) -> tuple[int, int]:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=fnt)
    return right - left, bottom - top


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for raw in text.split("\n"):
        current = ""
        for token in raw.split(" "):
            candidate = token if not current else f"{current} {token}"
            if text_box(draw, candidate, fnt)[0] <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
            current = ""
            chunk = ""
            for char in token:
                candidate = chunk + char
                if text_box(draw, candidate, fnt)[0] <= max_width:
                    chunk = candidate
                else:
                    if chunk:
                        lines.append(chunk)
                    chunk = char
            current = chunk
        if current:
            lines.append(current)
    return lines


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    fnt: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    max_width: int,
    line_gap: int,
) -> int:
    x, y = xy
    for line in wrap(draw, text, fnt, max_width):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += text_box(draw, line, fnt)[1] + line_gap
    return y


def cover(path: Path, size: tuple[int, int]) -> Image.Image:
    img = Image.open(path)
    img = ImageOps.exif_transpose(img).convert("RGB")
    ratio = max(size[0] / img.width, size[1] / img.height)
    resized = img.resize((math.ceil(img.width * ratio), math.ceil(img.height * ratio)), Image.LANCZOS)
    left = (resized.width - size[0]) // 2
    top = (resized.height - size[1]) // 2
    return resized.crop((left, top, left + size[0], top + size[1]))


def rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
    return mask


def paste_round(base: Image.Image, img: Image.Image, box: tuple[int, int, int, int], radius: int) -> None:
    w, h = box[2] - box[0], box[3] - box[1]
    crop = ImageOps.fit(img, (w, h), method=Image.LANCZOS)
    base.paste(crop, (box[0], box[1]), rounded_mask((w, h), radius))


def add_top_contact(draw: ImageDraw.ImageDraw) -> None:
    draw.text((844, 28), "상담/분석용 초안", font=font(22, False), fill=(180, 168, 158))


def draw_title_card(cut: Cut) -> Image.Image:
    img = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(img)
    add_top_contact(draw)

    draw.rectangle((0, 0, W, 290), fill=WHITE)
    draw.text((82, 72), "의정부", font=font(42, True), fill=INK)
    draw.text((82, 126), "메가커피", font=font(74, True), fill=INK)
    draw.rectangle((0, 282, W, 326), fill=BG)
    draw.text((82, 292), "월매출 3,500만원 · 창업비용 1.7억원 조건 검토", font=font(28, True), fill=WHITE)

    if cut.image:
        photo = cover(ASSETS / cut.image, (W, 754))
        img.paste(photo, (0, 326))

    badge = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(badge)
    bdraw.rounded_rectangle((70, 812, 1010, 978), radius=26, fill=(47, 20, 12, 218))
    bdraw.text((106, 846), "신규창업보다 먼저 비교할 조건", font=font(42, True), fill=WHITE)
    bdraw.text((106, 910), "대로변 · 역세권 · 최신 BI · 기존 매출 자료", font=font(30, True), fill=YELLOW)
    return Image.alpha_composite(img.convert("RGBA"), badge).convert("RGB")


def draw_photo_card(cut: Cut) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    add_top_contact(draw)
    if cut.image:
        paste_round(img, cover(ASSETS / cut.image, (890, 700)), (80, 170, 1000, 805), 30)

    draw.text((80, 74), cut.eyebrow, font=font(32, True), fill=YELLOW)
    draw.text((80, 828), cut.title, font=font(52, True), fill=WHITE)
    y = 902
    for item in cut.body:
        draw.text((94, y), "·", font=font(34, True), fill=YELLOW)
        y = draw_wrapped(draw, (124, y), item, font(30, True), SOFT, 800, 10) + 14
    return img


def draw_text_card(cut: Cut) -> Image.Image:
    bg = Image.new("RGB", (W, H), BG_2)
    if cut.image:
        photo = cover(ASSETS / cut.image, (W, H)).convert("L").filter(ImageFilter.GaussianBlur(1.4)).convert("RGB")
        overlay = Image.new("RGBA", (W, H), (30, 12, 8, 205))
        bg = Image.alpha_composite(photo.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(bg)
    add_top_contact(draw)
    draw.text((80, 120), cut.eyebrow, font=font(34, True), fill=YELLOW)
    y = draw_wrapped(draw, (80, 180), cut.title, font(64, True), WHITE, 870, 16)
    y += 56
    for item in cut.body:
        draw.rounded_rectangle((80, y, 1000, y + 104), radius=10, fill=(72, 42, 32))
        y = draw_wrapped(draw, (118, y + 26), item, font(30, True), SOFT, 835, 8) + 22
    return bg


def draw_table_card(cut: Cut) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    add_top_contact(draw)
    draw.text((80, 118), cut.title, font=font(60, True), fill=WHITE)

    table = cut.table or []
    x1, y1, x2 = 180, 310, 900
    row_h = 92
    draw.rounded_rectangle((x1, y1, x2, y1 + row_h * (len(table) + 1)), radius=10, fill=WHITE)
    draw.rectangle((x1, y1, x2, y1 + row_h), fill=GRAY)
    draw.text((x1 + 250, y1 + 26), "조건 요약", font=font(32, True), fill=INK)
    for idx, (label, value) in enumerate(table):
        y = y1 + row_h * (idx + 1)
        draw.line((x1, y, x2, y), fill=(210, 210, 210), width=2)
        draw.line((x1 + 250, y, x1 + 250, y + row_h), fill=(210, 210, 210), width=2)
        draw.text((x1 + 42, y + 28), label, font=font(27, True), fill=(90, 90, 90))
        draw.text((x1 + 292, y + 28), value, font=font(29, True), fill=INK)

    y = 812
    for item in cut.body:
        draw_wrapped(draw, (100, y), item, font(30, True), SOFT, 880, 10)
        y += 62
    return img


def draw_cta_card(cut: Cut) -> Image.Image:
    img = draw_text_card(cut)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((84, 840, 996, 950), radius=16, fill=(255, 255, 255, 238))
    draw.text((126, 872), "사진과 조건을 기준으로 먼저 검토하세요", font=font(36, True), fill=INK)
    draw.text((126, 926), "본 콘텐츠는 양도양수 상담/분석용이며 본사 공식 자료가 아닙니다.", font=font(22, False), fill=(90, 80, 70))
    return img


def save_cut(index: int, cut: Cut) -> None:
    if cut.kind == "title":
        img = draw_title_card(cut)
    elif cut.kind == "photo":
        img = draw_photo_card(cut)
    elif cut.kind == "table":
        img = draw_table_card(cut)
    elif cut.kind == "cta":
        img = draw_cta_card(cut)
    else:
        img = draw_text_card(cut)
    img.save(CUTS / f"cut-{index:02d}.jpg", quality=94, optimize=True)


def write_caption_copy() -> None:
    captions = [
        "의정부 메가커피 양도양수 조건은 월매출 3,500만원, 창업비용 1.7억원이라는 숫자만으로 판단하기보다 매출이 나온 입지와 운영 상태를 함께 봐야 합니다.",
        "조건표는 독자가 가장 먼저 확인하는 부분입니다. 창업비용, 기존 매출, 입지 조건, 최신 BI 여부를 먼저 정리해두면 이후 설명을 따라가기 쉽습니다.",
        "외관 사진에서는 간판 노출, 출입 접근성, 보행 동선이 중요합니다. 대로변과 역세권이라는 표현도 실제 이동 흐름과 함께 확인해야 설득력이 생깁니다.",
        "신규창업은 예상 매출로 출발하지만 양도양수는 기존 매출 자료를 확인할 수 있다는 차이가 있습니다. 다만 매출 자료의 기간과 계절성을 함께 확인해야 합니다.",
        "최신 BI 매장은 첫인상과 관리 상태를 판단하는 데 도움이 됩니다. 간판, 내부 마감, 좌석, 조명 상태를 사진으로 함께 보여주는 것이 좋습니다.",
        "월매출 3,500만원은 장점으로 볼 수 있지만 보장 표현으로 쓰면 안 됩니다. 월별 흐름, 평일과 주말 차이, 주변 경쟁점을 함께 검토해야 합니다.",
        "역세권과 대로변은 단어보다 실제 노출 방향과 유입 동선이 중요합니다. 사진으로 주변 환경을 보여주면 현장감이 살아납니다.",
        "상권 설명은 과장보다 체크 항목으로 정리하는 편이 신뢰를 줍니다. 배후수요, 유동인구, 경쟁점, 시간대별 흐름을 나눠서 설명합니다.",
        "카운터와 메뉴 사진은 운영 난이도를 설명할 때 유용합니다. 주문, 제조, 픽업, 재료 관리 동선이 단순한지 확인하는 흐름으로 연결합니다.",
        "창업비용 1.7억원은 포함 범위가 핵심입니다. 집기, 설비, 간판, 인테리어 상태와 추가 비용 가능성을 나눠서 봐야 합니다.",
        "계약 전에는 매출 자료, 본사 양도양수 승인 가능성, 시설 상태, 인수 범위, 임대 조건, 주변 경쟁점을 확인해야 합니다.",
        "결론은 무조건 추천이 아니라 검토할 만한 조건으로 정리하는 것이 좋습니다. 사진과 제공 조건을 기준으로 창업비용의 적정성과 리스크를 먼저 분석하는 방향이 안전합니다.",
    ]

    lines = [
        "# 의정부 메가커피 블로그 이미지 사이 설명글",
        "",
        "아래 문장은 12장 JPG 사이에 넣는 본문 초안입니다. 이미지는 시각 자료, 본문은 검색과 AI 브리핑이 이해할 수 있는 설명 역할로 분리합니다.",
        "",
    ]
    for index, caption in enumerate(captions, 1):
        lines.extend([f"## cut-{index:02d}", caption, ""])
    lines.append("본 콘텐츠는 양도양수 상담/분석용이며 본사 공식 자료가 아닙니다.")
    (OUT / "blog-caption-copy.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    if CUTS.exists():
        shutil.rmtree(CUTS)
    CUTS.mkdir(parents=True, exist_ok=True)

    cuts = [
        Cut("title", "exterior-main.jpg", "", "", []),
        Cut(
            "table",
            None,
            "조건 요약",
            "의정부 메가커피 창업",
            ["숫자보다 중요한 것은 매출 자료와 현장 조건의 연결입니다."],
            [
                ("월매출", "3,500만원"),
                ("창업비용", "1.7억원"),
                ("입지", "대로변 · 역세권"),
                ("매장상태", "최신 BI"),
            ],
        ),
        Cut("photo", "exterior-angle.jpg", "입지 사진", "대로변과 역세권은\n사진으로 먼저 확인", ["간판 노출", "출입 접근성", "보행 흐름"]),
        Cut("text", "interior-seat.jpg", "신규창업 전 비교", "예상보다\n확인 가능한 조건", ["기존 매출 자료를 기준으로 흐름 확인", "시설과 운영 상태를 사진으로 검토"]),
        Cut("photo", "interior-seat.jpg", "최신 BI", "첫인상은 좋지만\n상태 확인은 별도", ["내부 마감", "좌석과 조명", "관리 상태"]),
        Cut("text", "street-area.jpg", "매출 검토", "월매출 3,500만원,\n보장이 아니라 확인 포인트", ["월별 흐름", "평일/주말 차이", "경쟁점 영향"]),
        Cut("photo", "street-area.jpg", "상권 사진", "역세권 표현보다\n실제 유입 동선", ["배후수요", "주변 업종", "시간대별 흐름"]),
        Cut("text", "exterior-main.jpg", "상권 체크", "좋은 위치일수록\n더 구체적으로 봐야 합니다", ["대로변 방향", "경쟁 브랜드", "점심·퇴근 수요"]),
        Cut("photo", "counter-flow.jpg", "운영 동선", "카운터와 제조 흐름은\n운영 난이도와 연결", ["주문", "제조", "픽업"]),
        Cut("text", "equipment.jpg", "창업비용 검토", "1.7억원은\n포함 범위가 핵심", ["집기·설비 상태", "추가 비용 가능성", "인수 범위"]),
        Cut("text", "menu-product.jpg", "계약 전 체크", "좋아 보일수록\n자료 확인이 먼저", ["매출 자료", "본사 승인", "시설 상태", "계약 조건"]),
        Cut("cta", "exterior-angle.jpg", "결론", "의정부 메가커피,\n검토할 만한 조건입니다", ["좋다/나쁘다보다 먼저 분석", "사진과 조건으로 창업비용 적정성 확인"]),
    ]

    for index, cut in enumerate(cuts, 1):
        save_cut(index, cut)
    write_caption_copy()
    print(f"created {len(cuts)} jpg files in {CUTS}")
    print(OUT / "blog-caption-copy.md")


if __name__ == "__main__":
    main()
