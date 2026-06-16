from __future__ import annotations

import math
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


ROOT = Path("/Users/yangseung-in/Documents/상세페이지 자동화")
OUT = ROOT / "compose-coffee-transfer-guide"
IMG_OUT = OUT / "images"
SOURCE = Path("/Users/yangseung-in/Downloads/26년5월기준/컴포즈커피")

W, H = 1080, 1528
YELLOW = "#f5b400"
YELLOW_DARK = "#e5a400"
BLACK = "#111111"
CHARCOAL = "#303030"
GRAY = "#737373"
LIGHT = "#f6f6f6"
LINE = "#dddddd"
WHITE = "#ffffff"

FONT = "/System/Library/Fonts/AppleSDGothicNeo.ttc"


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT, size)


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    fnt: ImageFont.FreeTypeFont,
    fill: str = BLACK,
    bold: bool = False,
    anchor: str | None = None,
    align: str = "left",
) -> None:
    x, y = xy
    if not bold:
        draw.text((x, y), text, font=fnt, fill=fill, anchor=anchor, align=align)
        return
    offsets = [(0, 0), (1, 0), (0, 1), (1, 1)]
    for ox, oy in offsets:
        draw.text((x + ox, y + oy), text, font=fnt, fill=fill, anchor=anchor, align=align)


def wrap_ko(text: str, width: int) -> str:
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=False, replace_whitespace=False))


def paragraph(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    fnt: ImageFont.FreeTypeFont,
    fill: str = GRAY,
    width: int = 30,
    line_gap: int = 8,
    bold: bool = False,
) -> int:
    x, y = xy
    lines = wrap_ko(text, width).split("\n")
    for line in lines:
        draw_text(draw, (x, y), line, fnt, fill=fill, bold=bold)
        _, h = text_size(draw, line, fnt)
        y += h + line_gap
    return y


def load_photo(name: str) -> Image.Image:
    return Image.open(SOURCE / name).convert("RGB")


def fit_crop(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    return ImageOps.fit(im, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def rounded_photo(
    base: Image.Image,
    im: Image.Image,
    box: tuple[int, int, int, int],
    radius: int = 22,
    shadow: bool = True,
    border: str | None = None,
) -> None:
    x, y, w, h = box
    crop = fit_crop(im, (w, h)).convert("RGBA")
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((0, 0, w, h), radius=radius, fill=255)
    if shadow:
        sh = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        sd.rounded_rectangle((20, 20, w + 20, h + 20), radius=radius, fill=(0, 0, 0, 50))
        sh = sh.filter(ImageFilter.GaussianBlur(12))
        base.alpha_composite(sh, (x - 20, y - 14))
    base.paste(crop, (x, y), mask)
    if border:
        d = ImageDraw.Draw(base)
        d.rounded_rectangle((x, y, x + w, y + h), radius=radius, outline=border, width=2)


def draw_header(draw: ImageDraw.ImageDraw, page: int) -> None:
    draw.rounded_rectangle((36, 34, 70, 68), radius=8, fill=YELLOW)
    draw_text(draw, (53, 42), "C", font(26), fill=WHITE, bold=True, anchor="ma")
    draw_text(draw, (84, 42), "컴포즈커피", font(24), fill=BLACK, bold=True)
    draw.line((250, 55, 985, 55), fill=YELLOW, width=2)
    draw_text(draw, (1018, 36), f"{page:02d}", font(28), fill=BLACK, bold=True)


def draw_footer(draw: ImageDraw.ImageDraw, page: int) -> None:
    y = H - 58
    draw_text(draw, (44, y), f"{page:02d}", font(25), fill=BLACK, bold=True)
    draw.line((84, y + 7, 84, y + 33), fill="#bdbdbd", width=2)
    draw_text(draw, (102, y + 5), "COMPOSE COFFEE DETAIL PAGE GUIDE", font(16), fill="#9a9a9a")
    draw_text(draw, (690, y + 5), "* 본 페이지는 상담 가이드 샘플로 실제 조건과 다를 수 있습니다.", font(15), fill="#9a9a9a")


def new_page(page: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    im = Image.new("RGBA", (W, H), WHITE)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W - 1, H - 1), outline="#242424", width=2)
    draw_header(d, page)
    return im, d


def hline(draw: ImageDraw.ImageDraw, x: int, y: int, w: int = 990) -> None:
    draw.line((x, y, x + w, y), fill=YELLOW, width=2)


def title_block(draw: ImageDraw.ImageDraw, kicker: str, title_lines: list[tuple[str, str]], y: int = 112) -> int:
    draw_text(draw, (54, y), kicker, font(28), fill=BLACK, bold=True)
    y += 44
    for text, color in title_lines:
        draw_text(draw, (54, y), text, font(76), fill=color, bold=True)
        y += 84
    return y


def section_title(draw: ImageDraw.ImageDraw, num: str, text: str, y: int) -> int:
    draw_text(draw, (54, y), num, font(31), fill=YELLOW, bold=True)
    draw_text(draw, (96, y), text, font(31), fill=BLACK, bold=True)
    hline(draw, 54, y + 47)
    return y + 66


def draw_icon(draw: ImageDraw.ImageDraw, kind: str, cx: int, cy: int, scale: float = 1.0) -> None:
    lw = max(3, int(4 * scale))
    r = int(34 * scale)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=YELLOW, width=lw)
    col = BLACK
    if kind == "coin":
        draw.ellipse((cx - 18, cy - 12, cx + 18, cy + 12), outline=col, width=lw)
        draw.line((cx - 18, cy, cx + 18, cy), fill=col, width=lw)
        draw_text(draw, (cx, cy - 12), "W", font(int(20 * scale)), fill=col, bold=True, anchor="ma")
    elif kind == "pin":
        draw.ellipse((cx - 13, cy - 24, cx + 13, cy + 2), outline=col, width=lw)
        draw.polygon([(cx, cy + 24), (cx - 13, cy), (cx + 13, cy)], outline=col)
        draw.ellipse((cx - 5, cy - 16, cx + 5, cy - 6), fill=YELLOW)
    elif kind == "cup":
        draw.rounded_rectangle((cx - 15, cy - 20, cx + 15, cy + 20), radius=5, outline=col, width=lw)
        draw.line((cx - 20, cy - 12, cx + 20, cy - 12), fill=col, width=lw)
        draw.line((cx - 11, cy - 28, cx - 11, cy - 38), fill=YELLOW, width=lw)
    elif kind == "chart":
        for i, h in enumerate([18, 30, 44]):
            x = cx - 26 + i * 23
            draw.rectangle((x, cy + 24 - h, x + 13, cy + 24), outline=col, width=lw)
        draw.line((cx - 30, cy + 26, cx + 36, cy + 26), fill=col, width=lw)
    elif kind == "people":
        for dx in [-18, 18]:
            draw.ellipse((cx + dx - 9, cy - 26, cx + dx + 9, cy - 8), outline=col, width=lw)
            draw.arc((cx + dx - 19, cy - 4, cx + dx + 19, cy + 34), 200, 340, fill=col, width=lw)
        draw.ellipse((cx - 11, cy - 34, cx + 11, cy - 12), outline=col, width=lw)
        draw.arc((cx - 25, cy - 8, cx + 25, cy + 38), 200, 340, fill=col, width=lw)
    elif kind == "doc":
        draw.rectangle((cx - 18, cy - 28, cx + 20, cy + 28), outline=col, width=lw)
        for j in [-12, 0, 12]:
            draw.line((cx - 9, cy + j, cx + 12, cy + j), fill=col, width=lw)
    elif kind == "hand":
        draw.line((cx - 34, cy + 6, cx - 6, cy - 18), fill=col, width=lw)
        draw.line((cx + 34, cy + 6, cx + 6, cy - 18), fill=col, width=lw)
        draw.rounded_rectangle((cx - 9, cy - 16, cx + 9, cy + 14), radius=5, outline=col, width=lw)
    elif kind == "truck":
        draw.rectangle((cx - 32, cy - 12, cx + 8, cy + 14), outline=col, width=lw)
        draw.rectangle((cx + 8, cy - 4, cx + 32, cy + 14), outline=col, width=lw)
        draw.ellipse((cx - 23, cy + 10, cx - 9, cy + 24), outline=col, width=lw)
        draw.ellipse((cx + 17, cy + 10, cx + 31, cy + 24), outline=col, width=lw)
    elif kind == "timer":
        draw.ellipse((cx - 22, cy - 16, cx + 22, cy + 28), outline=col, width=lw)
        draw.line((cx, cy + 6, cx + 15, cy - 4), fill=col, width=lw)
        draw.line((cx - 10, cy - 30, cx + 10, cy - 30), fill=col, width=lw)
    elif kind == "check":
        draw.rectangle((cx - 22, cy - 24, cx + 20, cy + 24), outline=col, width=lw)
        draw.line((cx - 9, cy + 4, cx - 1, cy + 13), fill=YELLOW, width=lw + 2)
        draw.line((cx - 1, cy + 13, cx + 15, cy - 10), fill=YELLOW, width=lw + 2)
    else:
        draw.ellipse((cx - 18, cy - 18, cx + 18, cy + 18), outline=col, width=lw)


def card(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    body: str = "",
    icon: str = "cup",
    num: str | None = None,
    body_width: int = 12,
) -> None:
    x, y, w, h = box
    draw.rounded_rectangle((x, y, x + w, y + h), radius=14, fill=WHITE, outline=LINE, width=2)
    if num:
        draw.ellipse((x + 14, y + 14, x + 52, y + 52), fill=YELLOW)
        draw_text(draw, (x + 33, y + 22), num, font(18), fill=BLACK, bold=True, anchor="ma")
    draw_icon(draw, icon, x + w // 2, y + 52, scale=0.72)
    draw_text(draw, (x + w // 2, y + 105), title, font(24), fill=BLACK, bold=True, anchor="ma")
    if body:
        lines = wrap_ko(body, body_width).split("\n")[:4]
        yy = y + 145
        for line in lines:
            draw_text(draw, (x + w // 2, yy), line, font(17), fill=GRAY, anchor="ma")
            yy += 28


def small_card(draw, box, title, body="", icon="doc", num=None):
    x, y, w, h = box
    draw.rounded_rectangle((x, y, x + w, y + h), radius=12, fill=WHITE, outline=LINE, width=2)
    if num:
        draw.ellipse((x + 14, y + 14, x + 46, y + 46), fill=YELLOW)
        draw_text(draw, (x + 30, y + 20), num, font(16), fill=BLACK, bold=True, anchor="ma")
    draw_icon(draw, icon, x + 48, y + 57, scale=0.55)
    draw_text(draw, (x + 94, y + 27), title, font(22), fill=BLACK, bold=True)
    if body:
        paragraph(draw, (x + 94, y + 66), body, font(15), fill=GRAY, width=18, line_gap=4)


def note_box(draw: ImageDraw.ImageDraw, y: int, text: str) -> None:
    draw.rounded_rectangle((54, y, W - 54, y + 76), radius=12, fill="#fff6d8", outline=YELLOW, width=2)
    draw.polygon([(80, y + 54), (106, y + 18), (132, y + 54)], fill=YELLOW)
    draw_text(draw, (106, y + 29), "!", font(28), fill=WHITE, bold=True, anchor="ma")
    paragraph(draw, (156, y + 18), text, font(20), fill=BLACK, width=48, line_gap=4, bold=True)


def page01() -> Image.Image:
    im, d = new_page(1)
    y = title_block(
        d,
        "합리적인 양도양수, 꼼꼼한 분석!",
        [("컴포즈커피", BLACK), ("양도양수 상세 가이드", YELLOW)],
        116,
    )
    d.rounded_rectangle((54, y + 2, 520, y + 48), radius=24, fill=BLACK)
    draw_text(d, (77, y + 14), "블로그·웹페이지용 10페이지 상세페이지 샘플", font(22), fill=WHITE, bold=True)
    rounded_photo(im, load_photo("1_1.jpg"), (150, y + 86, 575, 268), 20)
    rounded_photo(im, load_photo("1_10.jpg"), (744, y + 42, 250, 345), 26)
    yy = y + 410
    d.text((54, yy), "왜 컴포즈커피 양도양수인가?", font=font(30), fill=BLACK)
    d.text((116, yy), "컴포즈커피", font=font(30), fill=YELLOW)
    cards = [
        ("가성비 브랜드", "합리적인 가격대와 일상 구매 수요", "coin"),
        ("높은 접근성", "상권과 생활권에 밀접한 매장 모델", "pin"),
        ("테이크아웃 친화", "빠른 주문과 회전에 유리한 구조", "cup"),
        ("메뉴 확장성", "커피·음료·디저트 조합 가능", "chart"),
    ]
    for i, (t, b, ic) in enumerate(cards):
        card(d, (54 + i * 248, yy + 62, 220, 218), t, b, ic, body_width=10)
    yy += 330
    section_title(d, "10", "페이지 구성 미리보기", yy)
    labels = [
        "브랜드 소개", "시장 포지션", "개요 및 타입", "양도양수 절차", "투자·수익 구조",
        "입지·상권 분석", "본사 지원 시스템", "메뉴·객단가", "체크포인트 사례", "상담 문의 안내",
    ]
    for i, label in enumerate(labels):
        x = 54 + (i % 5) * 196
        y0 = yy + 78 + (i // 5) * 132
        d.rounded_rectangle((x, y0, x + 174, y0 + 108), radius=12, fill=WHITE, outline=LINE, width=2)
        d.ellipse((x + 12, y0 + 12, x + 48, y0 + 48), fill=YELLOW)
        draw_text(d, (x + 30, y0 + 20), f"{i+1:02d}", font(16), fill=BLACK, bold=True, anchor="ma")
        draw_text(d, (x + 87, y0 + 62), label, font(19), fill=BLACK, bold=True, anchor="ma")
    draw_footer(d, 1)
    return im


def page02() -> Image.Image:
    im, d = new_page(2)
    y = title_block(d, "브랜드의 기본 체력을 먼저 봅니다", [("컴포즈커피", BLACK), ("브랜드 소개와", YELLOW), ("시장 포지션", YELLOW)], 112)
    rounded_photo(im, load_photo("2_9.jpg"), (604, 142, 390, 270), 18)
    paragraph(d, (54, y + 4), "컴포즈커피는 합리적인 가격대와 대중적인 메뉴 구성을 바탕으로 생활권 상권에서 반복 구매를 만들기 쉬운 커피 브랜드입니다. 양도양수 검토에서는 브랜드 인지도보다 실제 매장의 입지, 운영 구조, 비용 흐름을 함께 봐야 합니다.", font(22), fill=CHARCOAL, width=36, line_gap=9)
    yy = 600
    section_title(d, "01", "브랜드 성장 포인트", yy)
    growth = [
        ("대중적 가격대", "일상적으로 접근 가능한 커피 가격대", "coin"),
        ("생활권 접근성", "주거·오피스·역세권 상권과 연결", "pin"),
        ("빠른 회전 구조", "테이크아웃과 홀 이용 모두 고려", "timer"),
        ("브랜드 경험", "노랑·그레이 컬러로 명확한 인지", "people"),
    ]
    for i, item in enumerate(growth):
        card(d, (54 + i * 248, yy + 76, 220, 224), item[0], item[1], item[2], body_width=10)
    yy += 356
    section_title(d, "02", "양도양수 검토 시 보는 핵심 경쟁력", yy)
    comps = [
        ("접근성", "고객이 쉽게 방문하는가", "pin"),
        ("가격 경쟁력", "반복 구매 부담이 낮은가", "coin"),
        ("운영 효율", "주문·제조 동선이 안정적인가", "timer"),
        ("고객층", "직장인·학생·주거 수요가 있는가", "people"),
    ]
    for i, item in enumerate(comps):
        card(d, (54 + i * 248, yy + 76, 220, 224), item[0], item[1], item[2], num=f"{i+1:02d}", body_width=10)
    note_box(d, H - 172, "브랜드의 장점만으로 판단하지 않고, 해당 매장의 실제 상권과 비용 구조까지 함께 확인합니다.")
    draw_footer(d, 2)
    return im


def page03() -> Image.Image:
    im, d = new_page(3)
    y = title_block(d, "실속형 매장 인수 대안", [("컴포즈커피", BLACK), ("양도양수 개요 및 추천 타입", YELLOW)], 112)
    rounded_photo(im, load_photo("1_3.jpg"), (610, 150, 380, 260), 18)
    yy = 500
    section_title(d, "01", "양도양수 개요", yy)
    d.rounded_rectangle((54, yy + 78, 1026, yy + 212), radius=16, fill=WHITE, outline=LINE, width=2)
    draw_icon(d, "hand", 130, yy + 145, scale=0.82)
    paragraph(d, (205, yy + 104), "기존 매장을 인수하면 설비, 인테리어, 상권, 운영 흐름을 확인한 뒤 검토할 수 있습니다. 단, 매출자료와 계약 조건이 맞는지 반드시 검증해야 합니다.", font(22), fill=CHARCOAL, width=53, line_gap=8)
    yy += 260
    section_title(d, "02", "추천 매장 타입", yy)
    types = [
        ("테이크아웃 중심형", "유동인구가 있는 상권의 빠른 회전 매장", "cup"),
        ("소형 홀 겸용형", "10~20평 내외의 좌석 운영 가능 매장", "people"),
        ("주거상권 안정형", "생활권 반복 구매가 기대되는 매장", "pin"),
    ]
    for i, item in enumerate(types):
        card(d, (54 + i * 324, yy + 78, 300, 220), item[0], item[1], item[2], body_width=14)
    yy += 352
    section_title(d, "03", "어떤 예비 점주에게 맞을까?", yy)
    users = [
        ("첫 매장 인수", "운영 경험을 쌓고 싶은 분", "doc"),
        ("소자본 검토", "초기 비용을 비교하고 싶은 분", "coin"),
        ("동선 중시", "테이크아웃 흐름을 보는 분", "pin"),
        ("안정 추구", "장기 운영 가능성을 보는 분", "chart"),
    ]
    for i, item in enumerate(users):
        card(d, (54 + i * 248, yy + 78, 220, 204), item[0], item[1], item[2], body_width=10)
    draw_footer(d, 3)
    return im


def page04() -> Image.Image:
    im, d = new_page(4)
    y = title_block(d, "체계적인 단계로 확인합니다", [("컴포즈커피", BLACK), ("양도양수 절차", YELLOW), ("한눈에 보기", YELLOW)], 112)
    rounded_photo(im, load_photo("3_2.jpg"), (655, 140, 330, 215), 18)
    yy = 430
    section_title(d, "01", "6단계 양도양수 프로세스", yy)
    steps = [
        ("상담 및 목표 설정", "예산·희망 상권·운영 방향 정리", "people"),
        ("상권 조사", "유동인구와 경쟁 현황 검토", "pin"),
        ("매장 선정 및 계약 검토", "계약 조건과 권리관계 확인", "doc"),
        ("본사 협의 및 준비", "승계 가능 여부와 필요 서류 확인", "hand"),
        ("인테리어·장비·교육 확인", "시설 상태와 교육 일정 점검", "check"),
        ("인수 및 초기 운영 안정화", "인수 후 운영 흐름 정리", "chart"),
    ]
    for i, (t, b, ic) in enumerate(steps):
        x = 54 if i < 3 else 554
        y0 = yy + 75 + (i % 3) * 156
        small_card(d, (x, y0, 438, 128), t, b, ic, num=f"{i+1:02d}")
        if i % 3 < 2:
            d.polygon([(x + 219, y0 + 140), (x + 204, y0 + 156), (x + 234, y0 + 156)], fill=YELLOW)
    yy += 590
    section_title(d, "02", "준비 기간 체크", yy)
    d.line((110, yy + 132, 970, yy + 132), fill="#cfcfcf", width=4)
    for i, (t, _, ic) in enumerate(steps):
        cx = 110 + i * 172
        draw_icon(d, ic, cx, yy + 132, scale=0.58)
        d.ellipse((cx - 22, yy + 62, cx + 22, yy + 106), fill=YELLOW)
        draw_text(d, (cx, yy + 73), f"{i+1:02d}", font(17), fill=BLACK, bold=True, anchor="ma")
        draw_text(d, (cx, yy + 188), t.split(" ")[0], font(17), fill=BLACK, bold=True, anchor="ma")
    note_box(d, H - 174, "실제 절차와 기간은 본사 정책, 임대인 조건, 양도인 상황에 따라 달라질 수 있습니다.")
    draw_footer(d, 4)
    return im


def page05() -> Image.Image:
    im, d = new_page(5)
    y = title_block(d, "매장 승계 검토의 핵심", [("투자 비용 및", BLACK), ("수익 구조", YELLOW)], 112)
    rounded_photo(im, load_photo("3_20.jpg"), (700, 115, 285, 350), 22)
    paragraph(d, (54, y + 6), "양도금액 하나만 보고 결정하면 위험합니다. 초기 투자 항목, 고정비와 변동비, 매출 구조를 나누어 봐야 실제 인수 가능성과 운영 부담을 판단할 수 있습니다.", font(22), fill=CHARCOAL, width=37, line_gap=8)
    yy = 505
    section_title(d, "01", "초기 투자 항목", yy)
    items = [
        ("가맹 관련 비용", "승계·교육·계약 관련 비용", "doc"),
        ("인테리어", "보수·공사·집기 상태 확인", "check"),
        ("장비", "커피 머신·제빙기·POS 등", "cup"),
        ("보증금·권리금", "임대차와 권리 관계 점검", "coin"),
        ("예비 운영자금", "초기 운영비와 인건비 대비", "chart"),
    ]
    for i, item in enumerate(items):
        card(d, (54 + i * 194, yy + 76, 174, 206), item[0], item[1], item[2], body_width=8)
    yy += 330
    section_title(d, "02", "수익 구조 이해", yy)
    draw.ellipse if False else None
    # Donut chart
    cx, cy = 228, yy + 230
    d.pieslice((cx - 126, cy - 126, cx + 126, cy + 126), 0, 244, fill=YELLOW)
    d.pieslice((cx - 126, cy - 126, cx + 126, cy + 126), 244, 316, fill="#ffd766")
    d.pieslice((cx - 126, cy - 126, cx + 126, cy + 126), 316, 360, fill="#f7e6ad")
    d.ellipse((cx - 62, cy - 62, cx + 62, cy + 62), fill=WHITE)
    draw_text(d, (cx, cy - 12), "매출 구성", font(21), fill=BLACK, bold=True, anchor="ma")
    draw_text(d, (cx, cy + 18), "예시", font(20), fill=BLACK, bold=True, anchor="ma")
    legend = [("커피·음료", "핵심 매출"), ("디저트", "객단가 보조"), ("시즌 메뉴", "변동 매출")]
    for i, (a, b) in enumerate(legend):
        yy2 = yy + 125 + i * 55
        d.rounded_rectangle((410, yy2, 430, yy2 + 20), radius=4, fill=[YELLOW, "#ffd766", "#f7e6ad"][i])
        draw_text(d, (446, yy2 - 6), a, font(22), fill=BLACK, bold=True)
        draw_text(d, (446, yy2 + 24), b, font(17), fill=GRAY)
    small_card(d, (650, yy + 93, 340, 145), "고정비", "임대료·인건비·관리비처럼 매월 발생하는 비용", "coin")
    small_card(d, (650, yy + 255, 340, 145), "변동비", "재료비·수수료처럼 매출에 따라 달라지는 비용", "chart")
    note_box(d, H - 174, "이미지의 비율과 항목은 설명용 예시입니다. 실제 수익성은 매출자료와 비용자료 확인 후 판단해야 합니다.")
    draw_footer(d, 5)
    return im


def page06() -> Image.Image:
    im, d = new_page(6)
    y = title_block(d, "좋은 성과는 좋은 입지에서 시작됩니다", [("컴포즈커피", BLACK), ("입지 전략과", YELLOW), ("상권 분석", YELLOW)], 112)
    rounded_photo(im, load_photo("3_14.jpg"), (665, 135, 320, 250), 18)
    yy = 430
    section_title(d, "01", "좋은 입지의 기본 조건", yy)
    cond = [
        ("유동 인구", "출퇴근·등하교·점심 동선 확인", "people"),
        ("가시성과 접근성", "간판 노출과 진입 편의성", "pin"),
        ("타깃 고객", "직장인·학생·주거 수요 적합성", "people"),
        ("주변 시너지", "학원·오피스·편의시설과 연결", "chart"),
        ("성장 가능성", "상권 변화와 장기 수요", "chart"),
    ]
    for i, item in enumerate(cond):
        card(d, (54 + i * 194, yy + 76, 174, 220), item[0], item[1], item[2], body_width=8)
    yy += 360
    section_title(d, "02", "피해야 할 리스크", yy)
    risks = [
        ("낮은 가시성", "매장이 잘 보이지 않는 입지", "check"),
        ("과도한 임차료", "매출 대비 고정비 부담", "coin"),
        ("경쟁 과밀", "동일 고객층 경쟁 심화", "people"),
        ("동선 불편", "진입과 주문 동선이 복잡", "pin"),
    ]
    for i, item in enumerate(risks):
        small_card(d, (54 + i * 248, yy + 78, 220, 134), item[0], item[1], item[2])
    yy += 285
    section_title(d, "03", "상권 분석 포인트", yy)
    d.rounded_rectangle((54, yy + 78, 1026, yy + 260), radius=14, fill=WHITE, outline=LINE, width=2)
    for i, (t, b, ic) in enumerate([("인구 분석", "연령·직업·수요", "people"), ("상권 분석", "소비 성향·경쟁점", "chart"), ("입지 분석", "가시성·접근성", "pin")]):
        x = 92 + i * 210
        draw_icon(d, ic, x + 36, yy + 160, scale=0.7)
        draw_text(d, (x + 84, yy + 128), t, font(23), fill=BLACK, bold=True)
        draw_text(d, (x + 84, yy + 168), b, font(17), fill=GRAY)
    # Simple map rings
    mx, my = 900, yy + 168
    d.rounded_rectangle((758, yy + 98, 1002, yy + 240), radius=12, fill="#f1f7f2", outline="#cdddcf")
    for r, col in [(32, "#b7e5ff"), (56, "#d6f1c9"), (82, "#f7e6ad")]:
        d.ellipse((mx - r, my - r, mx + r, my + r), outline=col, width=10)
    d.ellipse((mx - 28, my - 28, mx + 28, my + 28), fill=YELLOW)
    draw_text(d, (mx, my - 13), "C", font(28), fill=BLACK, bold=True, anchor="ma")
    draw_footer(d, 6)
    return im


def page07() -> Image.Image:
    im, d = new_page(7)
    y = title_block(d, "인수 검토부터 운영까지", [("본사", BLACK), ("지원 시스템", YELLOW)], 112)
    rounded_photo(im, load_photo("1_20.jpg"), (610, 145, 385, 252), 18)
    paragraph(d, (54, y + 2), "프랜차이즈 매장은 브랜드 시스템을 이해해야 안정적인 운영 준비가 가능합니다. 교육, 물류, 메뉴 운영, 프로모션, 매장 관리 기준을 함께 확인합니다.", font(22), fill=CHARCOAL, width=34, line_gap=8)
    yy = 475
    section_title(d, "01", "핵심 지원 항목", yy)
    supports = [
        ("교육 지원", "운영 전 교육과 매뉴얼 확인", "people"),
        ("운영 매뉴얼", "표준화된 운영 기준 파악", "doc"),
        ("물류 시스템", "원부자재 공급과 재고 흐름", "truck"),
        ("마케팅", "프로모션과 시즌 메뉴 운영", "chart"),
    ]
    for i, item in enumerate(supports):
        card(d, (54 + i * 248, yy + 78, 220, 230), item[0], item[1], item[2], body_width=10)
    yy += 370
    section_title(d, "02", "인수 전부터 운영 후까지", yy)
    steps = ["상담", "상권 분석", "매장 점검", "교육", "오픈 준비", "운영 관리"]
    d.line((110, yy + 155, 970, yy + 155), fill=YELLOW, width=4)
    for i, step in enumerate(steps):
        cx = 110 + i * 172
        d.ellipse((cx - 48, yy + 107, cx + 48, yy + 203), fill=WHITE, outline=LINE, width=2)
        d.ellipse((cx - 22, yy + 78, cx + 22, yy + 122), fill=YELLOW)
        draw_text(d, (cx, yy + 89), f"{i+1:02d}", font(17), fill=BLACK, bold=True, anchor="ma")
        draw_text(d, (cx, yy + 228), step, font(20), fill=BLACK, bold=True, anchor="ma")
    yy += 335
    section_title(d, "03", "예비 점주가 꼭 물어봐야 할 질문", yy)
    qs = ["본사 승인 조건은?", "교육 기간은?", "물류 단가는?", "프로모션 방식은?", "운영 문제 지원은?"]
    for i, q in enumerate(qs):
        x = 54 + (i % 5) * 194
        d.rounded_rectangle((x, yy + 78, x + 174, yy + 148), radius=12, fill=WHITE, outline=LINE, width=2)
        draw_text(d, (x + 18, yy + 94), f"{i+1:02d}", font(19), fill=YELLOW, bold=True)
        draw_text(d, (x + 87, yy + 112), q, font(17), fill=BLACK, bold=True, anchor="ma")
    draw_footer(d, 7)
    return im


def page08() -> Image.Image:
    im, d = new_page(8)
    y = title_block(d, "판매 UP, 만족도 UP", [("컴포즈커피", BLACK), ("메뉴 경쟁력과", YELLOW), ("객단가 포인트", YELLOW)], 112)
    rounded_photo(im, load_photo("3_20.jpg"), (668, 116, 170, 230), 20)
    rounded_photo(im, load_photo("3_5.jpg"), (832, 150, 170, 210), 20)
    yy = 430
    section_title(d, "01", "메뉴 카테고리 구성", yy)
    menu = [
        ("커피", "아메리카노·라떼 등 기본 메뉴", "cup"),
        ("논커피", "에이드·스무디·라떼류", "cup"),
        ("시즌 메뉴", "계절별 신메뉴와 한정 메뉴", "chart"),
        ("디저트·스낵", "객단가를 보조하는 부가 메뉴", "coin"),
    ]
    for i, item in enumerate(menu):
        card(d, (54 + i * 248, yy + 76, 220, 220), item[0], item[1], item[2], body_width=10)
    yy += 350
    section_title(d, "02", "객단가를 높이는 조합", yy)
    combos = [
        ("커피 + 디저트", "함께 즐기는 구매 조합", "cup"),
        ("음료 + 스낵", "가벼운 한 끼 수요", "coin"),
        ("사이즈 업셀", "선택 옵션으로 만족도 상승", "chart"),
        ("추가 토핑", "시럽·샷·토핑 옵션", "check"),
    ]
    for i, item in enumerate(combos):
        card(d, (54 + i * 248, yy + 76, 220, 210), item[0], item[1], item[2], body_width=10)
    yy += 335
    section_title(d, "03", "메뉴 운영 체크", yy)
    d.rounded_rectangle((54, yy + 78, 1026, yy + 250), radius=14, fill=WHITE, outline=LINE, width=2)
    rows = [
        ("핵심 메뉴", "꾸준히 팔리는 기본 메뉴 중심"),
        ("성장 메뉴", "트렌드 반영과 객단가 상승"),
        ("실험 메뉴", "시즌 한정으로 반응 확인"),
    ]
    for i, (a, b) in enumerate(rows):
        x = 95 + i * 305
        draw_icon(d, ["cup", "chart", "timer"][i], x + 44, yy + 160, scale=0.72)
        draw_text(d, (x + 100, yy + 128), a, font(24), fill=BLACK, bold=True)
        paragraph(d, (x + 100, yy + 166), b, font(17), fill=GRAY, width=12, line_gap=4)
    draw_footer(d, 8)
    return im


def page09() -> Image.Image:
    im, d = new_page(9)
    y = title_block(d, "꼼꼼한 분석과 검증이 시작입니다", [("양도양수", BLACK), ("체크포인트와 사례", YELLOW)], 112)
    rounded_photo(im, load_photo("1_14.jpg"), (650, 140, 340, 245), 18)
    yy = 440
    section_title(d, "01", "기존 매장 인수 분석이 중요한 이유", yy)
    d.rounded_rectangle((54, yy + 78, 620, yy + 206), radius=14, fill=WHITE, outline=LINE, width=2)
    draw_icon(d, "chart", 126, yy + 142, scale=0.72)
    paragraph(d, (198, yy + 106), "기존 매장은 매출, 비용, 운영 데이터가 남아 있어 신규 창업보다 검토할 자료가 많습니다. 자료의 정확성과 계약 조건을 함께 확인해야 리스크를 줄일 수 있습니다.", font(20), fill=CHARCOAL, width=30, line_gap=7)
    yy += 260
    section_title(d, "02", "필수 체크포인트", yy)
    checks = [
        ("매출 검증", "POS·카드 매출 확인", "chart"),
        ("임대차 조건", "보증금·월세·계약기간", "doc"),
        ("장비 상태", "주요 장비와 AS 여부", "check"),
        ("인력 승계", "근무 조건과 인수 의사", "people"),
        ("본사 승인", "승계 심사와 교육 조건", "hand"),
    ]
    for i, item in enumerate(checks):
        card(d, (54 + i * 194, yy + 78, 174, 208), item[0], item[1], item[2], num=f"{i+1:02d}", body_width=8)
    yy += 345
    section_title(d, "03", "샘플 사례 구성", yy)
    d.rounded_rectangle((54, yy + 78, 1026, yy + 265), radius=14, fill=WHITE, outline=LINE, width=2)
    rounded_photo(im, load_photo("3_12.jpg"), (90, yy + 112, 210, 120), 12, shadow=False, border=LINE)
    sample = [("상권", "역세권·생활권 여부"), ("매출", "기간별 매출자료"), ("비용", "임대료·인건비·원가"), ("리스크", "계약·시설·인력 상태")]
    for i, (a, b) in enumerate(sample):
        x = 340 + (i % 2) * 310
        y0 = yy + 102 + (i // 2) * 76
        d.rounded_rectangle((x, y0, x + 270, y0 + 58), radius=10, fill=LIGHT, outline="#e7e7e7")
        draw_text(d, (x + 18, y0 + 12), a, font(20), fill=BLACK, bold=True)
        draw_text(d, (x + 78, y0 + 15), b, font(18), fill=GRAY)
    note_box(d, H - 174, "샘플 사례는 형식 예시입니다. 실제 매장명, 주소, 매출, 개인정보는 상담 자료 확인 후 별도로 정리합니다.")
    draw_footer(d, 9)
    return im


def page10() -> Image.Image:
    im, d = new_page(10)
    y = title_block(d, "전문가와 함께하는 매장 양도양수", [("컴포즈커피", BLACK), ("상담 및 문의 안내", YELLOW)], 112)
    rounded_photo(im, load_photo("1_1.jpg"), (640, 142, 360, 245), 18)
    paragraph(d, (54, y + 2), "체계적인 분석과 맞춤 상담으로 매장 이전과 인수 검토를 도와드립니다. 조건 분석부터 현장 확인까지 단계별로 확인하세요.", font(22), fill=CHARCOAL, width=35, line_gap=8)
    yy = 485
    section_title(d, "01", "이런 분께 추천합니다", yy)
    targets = [
        ("첫 매장 인수 준비", "신중하게 자료를 보고 싶은 분", "doc"),
        ("더 좋은 입지 고민", "상권과 동선을 비교하는 분", "pin"),
        ("소자본 안정 희망", "리스크를 줄이고 싶은 분", "coin"),
        ("파트너와 준비", "가족·동업자와 검토하는 분", "people"),
    ]
    for i, item in enumerate(targets):
        card(d, (54 + i * 248, yy + 78, 220, 218), item[0], item[1], item[2], body_width=10)
    yy += 348
    section_title(d, "02", "상담 진행 프로세스", yy)
    steps = [("문의", "기본 조건 접수"), ("니즈 파악", "예산·상권 정리"), ("매물 검토", "조건과 자료 분석"), ("맞춤 제안", "검토 결과 안내")]
    for i, (a, b) in enumerate(steps):
        x = 54 + i * 248
        card(d, (x, yy + 78, 220, 205), a, b, ["people", "doc", "pin", "hand"][i], num=f"{i+1:02d}", body_width=10)
        if i < 3:
            d.polygon([(x + 235, yy + 170), (x + 220, yy + 158), (x + 220, yy + 182)], fill=YELLOW)
    yy += 335
    d.rounded_rectangle((54, yy + 58, 520, yy + 244), radius=16, fill="#fff8dc", outline=YELLOW, width=2)
    draw_text(d, (82, yy + 82), "상담 및 문의", font(26), fill=BLACK, bold=True)
    draw_text(d, (96, yy + 126), "010-4359-7864", font(48), fill=BLACK, bold=True)
    draw_text(d, (96, yy + 178), "카카오톡 ID  siyang0616", font(27), fill=BLACK, bold=True)
    d.rounded_rectangle((560, yy + 58, 1026, yy + 244), radius=16, fill=WHITE, outline=LINE, width=2)
    draw_text(d, (588, yy + 84), "자주 묻는 질문", font(26), fill=BLACK, bold=True)
    draw_text(d, (588, yy + 126), "Q. 상담 비용이 있나요?", font(17), fill=CHARCOAL)
    draw_text(d, (588, yy + 154), "A. 우선 문의 후 안내드립니다.", font(17), fill=CHARCOAL)
    draw_text(d, (588, yy + 188), "Q. 바로 진행해야 하나요?", font(17), fill=CHARCOAL)
    draw_text(d, (588, yy + 216), "A. 자료 확인 후 결정하셔도 됩니다.", font(17), fill=CHARCOAL)
    d.rounded_rectangle((54, H - 104, 1026, H - 64), radius=10, fill=BLACK)
    draw_text(d, (540, H - 98), "컴포즈커피, 좋은 매장은 분석에서 시작됩니다.", font(28), fill=WHITE, bold=True, anchor="ma")
    draw_footer(d, 10)
    return im


DESCRIPTION = """컴포즈커피 양도양수는 단순히 매장을 사고파는 과정이 아니라, 기존 매장의 운영 흐름과 상권, 비용 구조를 종합적으로 검토해 인수 가능성을 판단하는 과정입니다. 신규 창업은 인테리어와 설비, 초기 홍보, 운영 동선 구축까지 처음부터 준비해야 하지만, 양도양수는 이미 운영 중인 매장의 매출자료와 시설 상태, 고객 흐름을 바탕으로 검토할 수 있다는 장점이 있습니다.

먼저 브랜드 자체의 시장 포지션을 이해해야 합니다. 컴포즈커피는 합리적인 가격대와 대중적인 메뉴 구성을 바탕으로 생활권, 역세권, 오피스 상권 등 다양한 입지에서 접근성이 높은 브랜드로 인식됩니다. 다만 브랜드 인지도만으로 좋은 매장을 판단할 수는 없습니다. 실제로는 유동인구, 배후수요, 경쟁점, 임대료 수준, 매장 동선, 테이크아웃 비중, 인력 운영 가능성까지 함께 분석해야 합니다.

양도양수 절차는 보통 상담과 목표 설정에서 시작해 매물 분석, 현장 확인, 조건 협의, 계약 검토, 본사 승인과 교육, 인수 후 초기 운영 안정화 순서로 진행됩니다. 이 과정에서 창업 컨설턴트는 단순히 매물을 소개하는 역할을 넘어 매출자료의 신뢰도, 임대차 조건, 권리금 적정성, 시설과 장비 상태, 원가와 고정비 구조, 상권 리스크를 함께 확인합니다. 특히 매출이 높아 보여도 임대료나 인건비 부담이 크면 실제 수익성은 달라질 수 있기 때문에 숫자의 구조를 나누어 보는 것이 중요합니다.

입지 분석도 핵심입니다. 같은 브랜드라도 매장이 위치한 상권에 따라 방문 고객층과 회전율, 객단가, 배달 의존도는 달라집니다. 출퇴근 동선에 강한 매장인지, 주거 배후수요가 있는지, 주변 경쟁 브랜드가 많은지, 간판 노출과 접근성이 좋은지 등을 현장에서 확인해야 합니다. 또한 본사 승계 조건, 교육 일정, 물류와 프로모션 지원 방식도 실제 운영에 영향을 주기 때문에 계약 전 확인이 필요합니다.

메뉴 경쟁력은 객단가와 반복 구매를 판단하는 중요한 요소입니다. 커피 중심 매출뿐 아니라 시즌 음료, 논커피 메뉴, 디저트와 스낵 조합이 얼마나 자연스럽게 판매되는지 확인하면 매장의 확장 가능성을 더 현실적으로 볼 수 있습니다. 결국 컴포즈커피 양도양수는 좋은 브랜드를 선택하는 일에서 끝나지 않습니다. 좋은 매장을 고르기 위해서는 자료 확인, 현장 확인, 조건 비교, 리스크 점검이 함께 이루어져야 합니다. 상담을 통해 본인의 예산과 운영 성향에 맞는 매장인지 차분히 검토하는 것이 안전한 인수의 출발점입니다."""


def build_index() -> None:
    html = """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>컴포즈커피 양도양수 상세 가이드</title>
  <style>
    body { margin: 0; background: #efefef; font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", sans-serif; color: #111; }
    main { max-width: 980px; margin: 0 auto; padding: 28px 16px 60px; }
    h1 { font-size: 28px; margin: 0 0 16px; }
    .toolbar { display: flex; gap: 10px; margin: 0 0 22px; flex-wrap: wrap; }
    button, a.download { border: 0; background: #111; color: white; padding: 11px 16px; border-radius: 8px; text-decoration: none; font-weight: 700; cursor: pointer; }
    .cut { margin: 0 0 28px; background: white; padding: 14px; border-radius: 10px; box-shadow: 0 8px 24px rgba(0,0,0,.08); }
    .cut h2 { font-size: 18px; margin: 0 0 10px; }
    .cut img { display: block; width: 100%; height: auto; border: 1px solid #ddd; }
    .meta { color: #666; font-size: 14px; margin-top: 8px; }
    textarea { width: 100%; min-height: 420px; box-sizing: border-box; border: 1px solid #ddd; border-radius: 10px; padding: 18px; font-size: 16px; line-height: 1.7; }
  </style>
</head>
<body>
<main>
  <h1>컴포즈커피 양도양수 상세 가이드 10장</h1>
  <div class="toolbar">
    <button onclick="downloadAll()">전체 다운로드</button>
    <a class="download" href="description-1500.txt" download>설명글 다운로드</a>
  </div>
"""
    for i in range(1, 11):
        name = f"cut-{i:02d}.png"
        html += f"""  <section class="cut">
    <h2>{i:02d}. cut-{i:02d}</h2>
    <img src="images/{name}" alt="컴포즈커피 양도양수 가이드 {i:02d}">
    <p class="meta"><a href="images/{name}" download>이 컷 다운로드</a> · QA: 텍스트 직접 렌더링 완료</p>
  </section>
"""
    html += """  <section class="cut">
    <h2>사진 밑 세부 설명 원고</h2>
    <textarea readonly>""" + DESCRIPTION.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") + """</textarea>
  </section>
</main>
<script>
function downloadAll() {
  for (let i = 1; i <= 10; i++) {
    const a = document.createElement('a');
    a.href = `images/cut-${String(i).padStart(2, '0')}.png`;
    a.download = `compose-coffee-transfer-guide-cut-${String(i).padStart(2, '0')}.png`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  }
}
</script>
</body>
</html>
"""
    (OUT / "index.html").write_text(html, encoding="utf-8")
    (OUT / "description-1500.txt").write_text(DESCRIPTION, encoding="utf-8")


def build_contact_sheet(paths: list[Path]) -> None:
    thumb_w, thumb_h = 270, 382
    sheet = Image.new("RGB", (thumb_w * 5 + 72, thumb_h * 2 + 120), "#f1f1f1")
    d = ImageDraw.Draw(sheet)
    draw_text(d, (36, 28), "컴포즈커피 양도양수 상세 가이드 10장 미리보기", font(24), fill=BLACK, bold=True)
    for i, path in enumerate(paths):
        im = Image.open(path).convert("RGB")
        im = fit_crop(im, (thumb_w, thumb_h))
        x = 36 + (i % 5) * thumb_w
        y = 78 + (i // 5) * thumb_h
        sheet.paste(im, (x, y))
        d.rectangle((x, y, x + thumb_w, y + thumb_h), outline="#d0d0d0", width=2)
    sheet.save(OUT / "contact-sheet.jpg", quality=92)


def main() -> None:
    IMG_OUT.mkdir(parents=True, exist_ok=True)
    pages = [page01, page02, page03, page04, page05, page06, page07, page08, page09, page10]
    out_paths: list[Path] = []
    for i, make in enumerate(pages, 1):
        page = make().convert("RGB")
        path = IMG_OUT / f"cut-{i:02d}.png"
        page.save(path)
        out_paths.append(path)
    build_index()
    build_contact_sheet(out_paths)
    print(OUT)


if __name__ == "__main__":
    main()
