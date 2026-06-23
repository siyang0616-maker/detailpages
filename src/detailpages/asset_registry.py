from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
ALLOWED_RIGHTS = {"owned", "licensed", "client_approved", "public_license_allowed"}
RIGHTS_STATUSES = ALLOWED_RIGHTS | {"review_required", "disallowed"}
RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "disallowed": 3}
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LIBRARY_ROOT = PROJECT_ROOT / "data" / "asset_library"
DEFAULT_ASSET_INDEX = DEFAULT_LIBRARY_ROOT / "manifests" / "asset-index.jsonl"


@dataclass
class AssetRecord:
    asset_id: str
    original_file: str
    source_type: str = "unknown"
    source_url: str = ""
    brand_detected: str = ""
    category: str = "unknown"
    visual_role: str = "reference_only"
    rights_status: str = "review_required"
    commercial_use_allowed: bool = False
    derivative_allowed: bool = False
    needs_masking: bool = False
    masking_targets: list[str] = field(default_factory=list)
    risk_level: str = "medium"
    approved_for_generation: bool = False
    notes: str = ""
    file_sha256: str = ""
    width: int | None = None
    height: int | None = None
    transformed_files: list[dict[str, Any]] = field(default_factory=list)
    masking_performed: list[dict[str, Any]] = field(default_factory=list)
    qa_status: str = "not_checked"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AssetRecord":
        fields = cls.__dataclass_fields__.keys()
        clean = {k: data[k] for k in fields if k in data}
        return cls(**clean)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["approved_for_generation"] = bool(data["approved_for_generation"])
        data["commercial_use_allowed"] = bool(data["commercial_use_allowed"])
        data["derivative_allowed"] = bool(data["derivative_allowed"])
        data["needs_masking"] = bool(data["needs_masking"])
        return data


def ensure_library_dirs(library_root: Path = DEFAULT_LIBRARY_ROOT) -> None:
    for relative in [
        "raw",
        "reviewed",
        "reviewed/thumbnails",
        "reviewed/contact-sheets",
        "reviewed/masked",
        "approved",
        "rejected",
        "transformed",
        "manifests",
    ]:
        (library_root / relative).mkdir(parents=True, exist_ok=True)


def asset_index_library_root(asset_index: Path) -> Path:
    if asset_index.name == "asset-index.jsonl" and asset_index.parent.name == "manifests":
        return asset_index.parent.parent
    return DEFAULT_LIBRARY_ROOT


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_image(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS


def read_jsonl(path: Path) -> list[AssetRecord]:
    if not path.exists():
        return []
    records: list[AssetRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(AssetRecord.from_dict(json.loads(line)))
    return records


def write_jsonl(path: Path, records: Iterable[AssetRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")


def next_asset_id(existing: Iterable[AssetRecord]) -> str:
    max_id = 0
    for record in existing:
        try:
            max_id = max(max_id, int(record.asset_id.split("_")[-1]))
        except (ValueError, IndexError):
            continue
    return f"asset_{max_id + 1:06d}"


def risk_allows(record: AssetRecord, max_level: str = "medium") -> bool:
    return RISK_ORDER.get(record.risk_level, 99) <= RISK_ORDER.get(max_level, 1)


def can_use_for_generation(record: AssetRecord, max_risk: str = "medium") -> bool:
    if not record.approved_for_generation:
        return False
    if record.rights_status not in ALLOWED_RIGHTS:
        return False
    if not record.commercial_use_allowed or not record.derivative_allowed:
        return False
    if not risk_allows(record, max_risk):
        return False
    if record.needs_masking and not record.masking_performed:
        return False
    return True


def resolve_asset_path(record: AssetRecord, library_root: Path = DEFAULT_LIBRARY_ROOT) -> Path:
    path = Path(record.original_file)
    if path.is_absolute():
        return path
    return library_root / path


def resolve_preferred_asset_path(record: AssetRecord, library_root: Path = DEFAULT_LIBRARY_ROOT) -> Path:
    if record.masking_performed:
        latest = record.masking_performed[-1].get("output_file")
        if latest:
            path = Path(str(latest))
            return path if path.is_absolute() else library_root / path
    return resolve_asset_path(record, library_root)


def bool_from_csv(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "승인", "allowed", "approve", "approved"}
