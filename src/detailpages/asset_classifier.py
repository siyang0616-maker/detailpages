from __future__ import annotations

from pathlib import Path

from .asset_registry import ALLOWED_RIGHTS


BRAND_KEYWORDS = {
    "megacoffee": "메가커피",
    "mega": "메가커피",
    "메가": "메가커피",
    "composecoffee": "컴포즈커피",
    "compose": "컴포즈커피",
    "컴포즈": "컴포즈커피",
    "subway": "써브웨이",
    "써브": "써브웨이",
    "lotteria": "롯데리아",
    "롯데리아": "롯데리아",
    "twosome": "투썸플레이스",
    "투썸": "투썸플레이스",
    "paikdabang": "빽다방",
    "빽다방": "빽다방",
    "paris": "파리바게뜨",
    "파리": "파리바게뜨",
    "baskin": "배스킨라빈스",
    "배스킨": "배스킨라빈스",
}

CATEGORY_KEYWORDS = {
    "exterior": "exterior",
    "signage": "exterior",
    "외관": "exterior",
    "간판": "exterior",
    "01-exterior-signage": "exterior",
    "interior": "interior",
    "seating": "interior",
    "내부": "interior",
    "좌석": "interior",
    "02-interior-seating": "interior",
    "counter": "counter",
    "kiosk": "counter",
    "order": "counter",
    "카운터": "counter",
    "키오스크": "counter",
    "03-counter-kiosk-order": "counter",
    "equipment": "equipment",
    "kitchen": "equipment",
    "장비": "equipment",
    "04-kitchen-equipment": "equipment",
    "menu": "menu",
    "drink": "menu",
    "food": "menu",
    "promotion": "menu",
    "메뉴": "menu",
    "음료": "menu",
    "05-food-drink-menu": "menu",
    "06-menu-promotion": "menu",
    "street": "street",
    "trade": "street",
    "상권": "street",
    "거리": "street",
    "07-street-trade-area": "street",
    "people": "people",
    "person": "people",
    "face": "people",
    "인물": "people",
    "document": "document",
    "pos": "document",
    "문서": "document",
    "review": "unknown",
    "uncategorized": "unknown",
    "99_review_needed": "unknown",
    "09-caution-unusable": "people",
}

VISUAL_ROLE_BY_CATEGORY = {
    "exterior": "hero",
    "interior": "evidence",
    "counter": "evidence",
    "street": "background",
    "menu": "mood",
    "equipment": "evidence",
    "product": "mood",
    "people": "reference_only",
    "document": "reference_only",
    "unknown": "reference_only",
}


def detect_brand(path: Path) -> str:
    haystack = str(path).lower()
    for keyword, brand in BRAND_KEYWORDS.items():
        if keyword.lower() in haystack:
            return brand
    return ""


def classify_category(path: Path) -> str:
    haystack = str(path).lower().replace("_", "-")
    for keyword, category in CATEGORY_KEYWORDS.items():
        if keyword.lower() in haystack:
            return category
    return "unknown"


def masking_targets_for(category: str, path: Path) -> list[str]:
    haystack = str(path).lower()
    targets: list[str] = []
    if category == "people" or any(k in haystack for k in ["person", "face", "인물", "caution-unusable"]):
        targets.append("face")
    if category in {"counter", "document"} or "pos" in haystack:
        targets.extend(["phone_number", "staff_name_tag", "private_document"])
    if category in {"exterior", "street"}:
        targets.extend(["license_plate", "phone_number", "store_branch_name"])
    if category == "menu":
        targets.append("third_party_poster_or_campaign")
    return sorted(set(targets))


def risk_for(category: str, path: Path, targets: list[str]) -> str:
    haystack = str(path).lower()
    if "watermark" in haystack:
        return "disallowed"
    if "caution-unusable" in haystack or category in {"people", "document"}:
        return "high"
    if targets or category in {"counter", "street", "menu"}:
        return "medium"
    if category in {"exterior", "interior", "equipment"}:
        return "low"
    return "medium"


def rights_for_source(source_type: str) -> tuple[str, bool, bool]:
    if source_type in {"user_owned", "self_shot"}:
        return "owned", True, True
    if source_type == "client_provided":
        return "client_approved", True, True
    if source_type in {"stock", "public_license"}:
        return "review_required", False, False
    return "review_required", False, False


def classify_path(path: Path, source_type: str = "unknown") -> dict[str, object]:
    category = classify_category(path)
    targets = masking_targets_for(category, path)
    risk_level = risk_for(category, path, targets)
    rights_status, commercial_use_allowed, derivative_allowed = rights_for_source(source_type)
    if risk_level == "disallowed":
        rights_status = "disallowed"
        commercial_use_allowed = False
        derivative_allowed = False
    return {
        "brand_detected": detect_brand(path),
        "category": category,
        "visual_role": VISUAL_ROLE_BY_CATEGORY.get(category, "reference_only"),
        "rights_status": rights_status if rights_status in ALLOWED_RIGHTS else rights_status,
        "commercial_use_allowed": commercial_use_allowed,
        "derivative_allowed": derivative_allowed,
        "needs_masking": bool(targets),
        "masking_targets": targets,
        "risk_level": risk_level,
    }
