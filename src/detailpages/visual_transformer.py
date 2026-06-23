from __future__ import annotations

import json
import math
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

from .asset_registry import AssetRecord, DEFAULT_ASSET_INDEX, asset_index_library_root, resolve_preferred_asset_path
from .asset_search import pick_by_category, search_assets


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "outputs"
FONT_CANDIDATES = [
    Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
    Path("/System/Library/Fonts/Supplemental/AppleGothic.ttf"),
    Path("/Library/Fonts/AppleGothic.ttf"),
    Path(r"C:\Windows\Fonts\malgun.ttf"),
]


PRESETS: dict[str, dict[str, Any]] = {
    "clean_real_estate_report": {"brand_overlay": 0.16, "brightness": 1.04, "contrast": 1.05, "saturation": 0.98},
    "naver_blog_cover": {"brand_overlay": 0.20, "brightness": 1.05, "contrast": 1.06, "saturation": 1.05},
    "franchise_briefing": {"brand_overlay": 0.18, "brightness": 1.03, "contrast": 1.08, "saturation": 1.02},
    "warm_consulting": {"brand_overlay": 0.14, "brightness": 1.06, "contrast": 1.03, "saturation": 1.04},
    "bright_brand_mood": {"brand_overlay": 0.24, "brightness": 1.08, "contrast": 1.08, "saturation": 1.10},
    "realistic_store_review": {"brand_overlay": 0.12, "brightness": 1.03, "contrast": 1.05, "saturation": 1.02},
    "premium_transfer_report": {"brand_overlay": 0.10, "brightness": 1.02, "contrast": 1.10, "saturation": 1.0},
}


@dataclass(frozen=True)
class RenderedAsset:
    asset: AssetRecord
    source_file: str
    transformed_file: str
    masking_performed: list[dict[str, Any]]
    risk_level: str
    rights_status: str
    layout: str
    passed_qa: bool = True


def _font(size: int) -> ImageFont.FreeTypeFont:
    for candidate in FONT_CANDIDATES:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def _text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, size: int, fill: str, bold: bool = False, anchor: str | None = None) -> None:
    x, y = xy
    offsets = [(0, 0), (1, 0), (0, 1)] if bold else [(0, 0)]
    for ox, oy in offsets:
        draw.text((x + ox, y + oy), text, font=_font(size), fill=fill, anchor=anchor)


def _wrap(text: str, width: int) -> list[str]:
    import textwrap

    lines: list[str] = []
    for paragraph in text.split("\n"):
        lines.extend(textwrap.wrap(paragraph, width=width, break_long_words=False) or [""])
    return lines


def _draw_wrapped(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, size: int, fill: str, width: int, line_gap: int = 8, bold: bool = False) -> int:
    x, y = xy
    fnt = _font(size)
    for line in _wrap(text, width):
        for ox, oy in ([(0, 0), (1, 0), (0, 1)] if bold else [(0, 0)]):
            draw.text((x + ox, y + oy), line, font=fnt, fill=fill)
        box = draw.textbbox((x, y), line, font=fnt)
        y += (box[3] - box[1]) + line_gap
    return y


def _cover(path: Path, size: tuple[int, int]) -> Image.Image:
    with Image.open(path) as raw:
        image = ImageOps.exif_transpose(raw).convert("RGB")
    ratio = max(size[0] / image.width, size[1] / image.height)
    resized = image.resize((math.ceil(image.width * ratio), math.ceil(image.height * ratio)), Image.Resampling.LANCZOS)
    left = (resized.width - size[0]) // 2
    top = (resized.height - size[1]) // 2
    return resized.crop((left, top, left + size[0], top + size[1]))


def transform_photo(source: Path, out: Path, size: tuple[int, int], preset: str, brand_color: tuple[int, int, int] = (245, 180, 0)) -> Path:
    params = PRESETS.get(preset, PRESETS["realistic_store_review"])
    image = _cover(source, size)
    image = ImageEnhance.Brightness(image).enhance(params["brightness"])
    image = ImageEnhance.Contrast(image).enhance(params["contrast"])
    image = ImageEnhance.Color(image).enhance(params["saturation"])
    overlay = Image.new("RGBA", size, (*brand_color, int(255 * params["brand_overlay"])))
    image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out, quality=92)
    return out


def _card_base(size: tuple[int, int] = (1080, 1080)) -> Image.Image:
    return Image.new("RGB", size, "#fbfbfb")


def _topbar(draw: ImageDraw.ImageDraw, manifest: dict[str, Any], page: int, total: int) -> None:
    _text(draw, (54, 42), manifest.get("brand", "브랜드"), 31, "#111111", bold=True)
    draw.line((220, 58, 950, 58), fill="#f3b400", width=3)
    _text(draw, (1010, 35), f"{page:02d}", 28, "#111111", bold=True)
    _text(draw, (54, 1030), f"{page:02d} | VISUAL ASSET FACTORY", 17, "#888888")
    _text(draw, (680, 1030), "상담/분석용 · 본사 공식 자료 아님", 16, "#999999")


def _photo_card(
    photo: Path,
    out: Path,
    manifest: dict[str, Any],
    title: str,
    subtitle: str,
    bullets: list[str],
    page: int,
    total: int,
    preset: str,
) -> Path:
    img = _card_base()
    transformed = transform_photo(photo, out.parent / "transformed" / f"{out.stem}-photo.jpg", (920, 470), preset)
    photo_img = Image.open(transformed).convert("RGB")
    img.paste(photo_img, (80, 170))
    draw = ImageDraw.Draw(img)
    _topbar(draw, manifest, page, total)
    _text(draw, (80, 104), subtitle, 25, "#222222", bold=True)
    _draw_wrapped(draw, (80, 675), title, 56, "#111111", 18, bold=True)
    y = 815
    for bullet in bullets[:4]:
        draw.rounded_rectangle((80, y, 1000, y + 54), radius=12, fill="#ffffff", outline="#dddddd", width=2)
        draw.ellipse((102, y + 15, 126, y + 39), fill="#f3b400")
        _text(draw, (146, y + 14), bullet, 22, "#222222", bold=True)
        y += 68
    img.save(out, quality=93)
    return out


def _summary_card(out: Path, manifest: dict[str, Any], page: int, total: int) -> Path:
    img = _card_base()
    draw = ImageDraw.Draw(img)
    _topbar(draw, manifest, page, total)
    _text(draw, (72, 126), f"{manifest.get('region', '')} {manifest.get('brand', '')}", 60, "#111111", bold=True)
    _text(draw, (72, 200), "조건 요약", 62, "#f0ae00", bold=True)
    items = [
        ("월매출", manifest.get("monthly_sales", "확인 필요")),
        ("창업비용", manifest.get("startup_cost", "확인 필요")),
        ("브랜드", manifest.get("brand", "확인 필요")),
        ("분석 기준", "승인된 사진 자산"),
    ]
    y = 330
    for label, value in items:
        draw.rounded_rectangle((72, y, 1008, y + 105), radius=16, fill="#ffffff", outline="#dddddd", width=2)
        _text(draw, (112, y + 31), label, 27, "#777777", bold=True)
        _text(draw, (330, y + 28), str(value), 32, "#111111", bold=True)
        y += 126
    draw.rounded_rectangle((72, 880, 1008, 960), radius=14, fill="#fff5d6", outline="#f3b400", width=2)
    _text(draw, (112, 904), "review_required/disallowed 자산은 자동 출력에서 제외됩니다.", 24, "#111111", bold=True)
    img.save(out, quality=93)
    return out


def _cta_card(out: Path, manifest: dict[str, Any], page: int, total: int) -> Path:
    img = _card_base()
    draw = ImageDraw.Draw(img)
    _topbar(draw, manifest, page, total)
    _text(draw, (74, 132), f"{manifest.get('brand', '')} 양도양수", 58, "#111111", bold=True)
    _text(draw, (74, 208), "좋은 매장은 분석에서 시작됩니다", 48, "#f0ae00", bold=True)
    bullets = ["사진 자산 검토", "권리·위험 상태 확인", "상권과 비용 구조 분석", "자료 기반 상담 안내"]
    y = 340
    for idx, bullet in enumerate(bullets, 1):
        draw.rounded_rectangle((74, y, 1006, y + 94), radius=18, fill="#ffffff", outline="#dddddd", width=2)
        draw.ellipse((104, y + 27, 144, y + 67), fill="#f3b400")
        _text(draw, (115, y + 35), str(idx), 18, "#111111", bold=True)
        _text(draw, (174, y + 30), bullet, 30, "#111111", bold=True)
        y += 115
    consultant = manifest.get("consultant", {})
    draw.rounded_rectangle((74, 825, 1006, 942), radius=18, fill="#111111")
    _text(draw, (110, 850), consultant.get("phone", "상담 문의"), 45, "#ffffff", bold=True)
    if consultant.get("show_name", False) and consultant.get("name"):
        _text(draw, (110, 908), f"{consultant.get('name')} {consultant.get('title', '')}", 24, "#f3b400", bold=True)
    else:
        _text(draw, (110, 908), manifest.get("cta_text", "자료 확인 후 안내드립니다."), 24, "#f3b400", bold=True)
    img.save(out, quality=93)
    return out


def _contact_sheet(image_paths: list[Path], out: Path) -> Path:
    thumbs = []
    for path in image_paths:
        with Image.open(path) as image:
            thumbs.append(ImageOps.fit(image.convert("RGB"), (240, 240)))
    cols = min(4, max(1, len(thumbs)))
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 260 + 40, rows * 290 + 60), "#f4f4f4")
    draw = ImageDraw.Draw(sheet)
    _text(draw, (24, 18), "render contact sheet", 22, "#111111", bold=True)
    for idx, thumb in enumerate(thumbs):
        x = 24 + (idx % cols) * 260
        y = 60 + (idx // cols) * 290
        sheet.paste(thumb, (x, y))
        _text(draw, (x, y + 248), image_paths[idx].name, 16, "#444444")
    sheet.save(out, quality=90)
    return out


def _asset_index_from_manifest(manifest_path: Path, manifest: dict[str, Any]) -> Path:
    configured = manifest.get("asset_index")
    if configured:
        path = Path(configured)
        return path if path.is_absolute() else (manifest_path.parent / path).resolve()
    return DEFAULT_ASSET_INDEX


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def render_project(manifest_path: Path, full: bool = False) -> Path:
    manifest = load_manifest(manifest_path)
    slug = manifest["project_slug"]
    asset_index = _asset_index_from_manifest(manifest_path, manifest)
    library_root = asset_index_library_root(asset_index)
    output_root = Path(manifest.get("output_root", DEFAULT_OUTPUT_ROOT))
    if not output_root.is_absolute():
        output_root = (PROJECT_ROOT / output_root).resolve()
    out_dir = output_root / slug / ("latest" if full else "preview")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    query = dict(manifest.get("asset_query", {}))
    query.setdefault("brand", manifest.get("brand"))
    query.setdefault("approved_for_generation", True)
    records = search_assets(asset_index, query)
    if not records:
        raise SystemExit("No approved, allowed assets matched the manifest query. Approve assets before rendering.")
    picked = pick_by_category(records, ["exterior", "interior", "counter", "street", "menu"])
    if "exterior" not in picked:
        raise SystemExit("Rendering needs at least one approved exterior asset for the cover.")

    preset = manifest.get("visual_preset", "realistic_store_review")
    total = int(manifest.get("output", {}).get("card_count", 10)) if full else 4
    generated: list[Path] = []
    usage: list[RenderedAsset] = []

    def add_usage(record: AssetRecord, path: Path, layout: str) -> None:
        usage.append(
            RenderedAsset(
                asset=record,
                source_file=record.original_file,
                transformed_file=str(path),
                masking_performed=record.masking_performed,
                risk_level=record.risk_level,
                rights_status=record.rights_status,
                layout=layout,
            )
        )

    exterior = picked["exterior"]
    exterior_path = resolve_preferred_asset_path(exterior, library_root)
    generated.append(_photo_card(exterior_path, out_dir / "cut-01.jpg", manifest, f"{manifest.get('brand')} 양도양수\n검토 전 확인할 조건", "실사진 기반 커버", ["외관", "간판", "접근성", "출입 동선"], 1, total, preset))
    add_usage(exterior, generated[-1], "photo_variant_1")
    generated.append(_summary_card(out_dir / "cut-02.jpg", manifest, 2, total))

    evidence = picked.get("interior") or picked.get("counter") or exterior
    evidence_path = resolve_preferred_asset_path(evidence, library_root)
    generated.append(_photo_card(evidence_path, out_dir / "cut-03.jpg", manifest, "사진으로 확인하는\n운영 증거", "photo-first evidence", ["매장 컨디션", "운영 동선", "설비 상태", "현장 확인"], 3, total, preset))
    add_usage(evidence, generated[-1], "photo_variant_2")
    generated.append(_cta_card(out_dir / "cut-04.jpg", manifest, 4, total))

    if full:
        categories = ["counter", "street", "menu", "interior", "exterior", "counter", "street", "menu"]
        titles = [
            "운영 동선과 카운터 흐름",
            "입지와 주변 상권",
            "메뉴 경쟁력과 객단가",
            "좌석과 내부 컨디션",
            "외관 노출과 접근성",
            "장비·POS·주문 흐름",
            "유입 동선과 배후수요",
            "계약 전 체크포인트",
        ]
        for idx in range(5, total + 1):
            cat = categories[(idx - 5) % len(categories)]
            record = picked.get(cat) or exterior
            path = resolve_preferred_asset_path(record, library_root)
            generated.append(
                _photo_card(
                    path,
                    out_dir / f"cut-{idx:02d}.jpg",
                    manifest,
                    titles[(idx - 5) % len(titles)],
                    "approved asset evidence",
                    ["자료 확인", "현장 확인", "리스크 점검", "상담 후 판단"],
                    idx,
                    total,
                    preset,
                )
            )
            add_usage(record, generated[-1], f"photo_variant_{((idx - 1) % 5) + 1}")

    _contact_sheet(generated, out_dir / "contact-sheet.jpg")
    (out_dir / "blog-caption-copy.md").write_text(_blog_caption(manifest, full=full), encoding="utf-8")
    (out_dir / "naver-upload-draft.md").write_text(_naver_draft(manifest, generated), encoding="utf-8")
    usage_report = {
        "project_slug": slug,
        "asset_index": str(asset_index),
        "items": [
            {
                "asset_id": item.asset.asset_id,
                "source_file": item.source_file,
                "transformed_file": item.transformed_file,
                "masking_performed": item.masking_performed,
                "risk_level": item.risk_level,
                "rights_status": item.rights_status,
                "masking_targets": item.asset.masking_targets,
                "layout": item.layout,
                "passed_qa": item.passed_qa,
            }
            for item in usage
        ],
    }
    (out_dir / "asset-usage-report.json").write_text(json.dumps(usage_report, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_dir


def _blog_caption(manifest: dict[str, Any], full: bool = False) -> str:
    return f"""# {manifest.get('brand')} 양도양수 블로그 설명 초안

{manifest.get('region', '')} {manifest.get('brand', '')} 양도양수 검토는 단순히 예쁜 이미지나 매출 숫자만으로 판단하지 않습니다. 실제 사진 자산을 통해 외관, 내부, 카운터, 상권, 메뉴 구성을 확인하고, 승인된 자료만 사용해 상담용 콘텐츠를 구성합니다.

월매출은 `{manifest.get('monthly_sales', '확인 필요')}`, 창업비용은 `{manifest.get('startup_cost', '확인 필요')}`로 입력되어 있지만, 해당 수치는 반드시 원자료와 비용 구조를 함께 봐야 합니다. 권리금, 보증금, 임대료, 인건비, 재료비, 본사 승계 조건까지 확인해야 실제 인수 판단이 가능합니다.

이 콘텐츠는 본사 공식 자료가 아니라 상담/분석용 초안입니다. review_required 또는 disallowed 상태의 사진은 최종 출력에서 제외됩니다.
"""


def _naver_draft(manifest: dict[str, Any], generated: list[Path]) -> str:
    lines = [f"# {manifest.get('brand')} 양도양수 이미지 업로드 초안", ""]
    for path in generated:
        lines.append(f"![{path.stem}]({path.name})")
        lines.append("")
    lines.append("상담/분석용 초안이며 본사 공식 자료가 아닙니다.")
    return "\n".join(lines)
