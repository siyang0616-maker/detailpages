from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .asset_registry import AssetRecord, can_use_for_generation, read_jsonl


def search_assets(asset_index: Path, query: dict[str, Any]) -> list[AssetRecord]:
    records = read_jsonl(asset_index)
    brand = query.get("brand") or query.get("brand_detected")
    categories = set(query.get("categories") or [])
    rights = set(query.get("rights_status") or [])
    approved = query.get("approved_for_generation")
    max_risk = query.get("risk_level_max", "medium")

    result: list[AssetRecord] = []
    for record in records:
        if brand and record.brand_detected != brand:
            continue
        if categories and record.category not in categories:
            continue
        if rights and record.rights_status not in rights:
            continue
        if approved is not None and bool(record.approved_for_generation) != bool(approved):
            continue
        if not can_use_for_generation(record, max_risk=max_risk):
            continue
        result.append(record)
    return sorted(result, key=lambda r: (r.category, r.risk_level, r.asset_id))


def pick_by_category(records: list[AssetRecord], categories: list[str]) -> dict[str, AssetRecord]:
    buckets: dict[str, list[AssetRecord]] = defaultdict(list)
    for record in records:
        buckets[record.category].append(record)
    picked: dict[str, AssetRecord] = {}
    used: set[str] = set()
    for category in categories:
        candidates = [r for r in buckets.get(category, []) if r.asset_id not in used]
        if candidates:
            picked[category] = candidates[0]
            used.add(candidates[0].asset_id)
    return picked

