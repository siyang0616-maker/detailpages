from __future__ import annotations

import argparse
import csv
from dataclasses import fields
from pathlib import Path

from .asset_ingest import ingest_assets, make_review_sheet
from .asset_qa import qa_output
from .asset_registry import AssetRecord, DEFAULT_ASSET_INDEX, bool_from_csv, read_jsonl, write_jsonl
from .privacy_masker import mask_assets
from .visual_transformer import render_project


def _cmd_ingest(args: argparse.Namespace) -> None:
    records = ingest_assets(Path(args.input), Path(args.output), source_type=args.source_type, source_url=args.source_url)
    print(f"ingested {len(records)} new assets")
    print(args.output)


def _cmd_review(args: argparse.Namespace) -> None:
    output = make_review_sheet(Path(args.asset_index), Path(args.output) if args.output else None)
    print(output)


def _cmd_mask(args: argparse.Namespace) -> None:
    records = mask_assets(Path(args.asset_index))
    print(f"processed {len(records)} assets")


def _infer_asset_index(review_sheet: Path) -> Path:
    if review_sheet.name == "review-sheet.csv":
        candidate = review_sheet.parent / "manifests" / "asset-index.jsonl"
        if candidate.exists():
            return candidate
    return DEFAULT_ASSET_INDEX


def _cmd_approve(args: argparse.Namespace) -> None:
    review_sheet = Path(args.review_sheet)
    asset_index = Path(args.asset_index) if args.asset_index else _infer_asset_index(review_sheet)
    records = {record.asset_id: record for record in read_jsonl(asset_index)}
    known_fields = {field.name for field in fields(AssetRecord)}
    with review_sheet.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            asset_id = row.get("asset_id", "")
            if asset_id not in records:
                continue
            record = records[asset_id]
            for key, value in row.items():
                if key not in known_fields or value is None:
                    continue
                if key in {"commercial_use_allowed", "derivative_allowed", "needs_masking", "approved_for_generation"}:
                    setattr(record, key, bool_from_csv(value))
                elif key == "masking_targets":
                    record.masking_targets = [item.strip() for item in value.split(",") if item.strip()]
                elif key in {"width", "height"}:
                    if str(value).strip():
                        setattr(record, key, int(value))
                else:
                    setattr(record, key, value)
    write_jsonl(asset_index, records.values())
    print(f"updated {len(records)} records")
    print(asset_index)


def _cmd_render_preview(args: argparse.Namespace) -> None:
    out = render_project(Path(args.manifest), full=False)
    print(out)


def _cmd_render_full(args: argparse.Namespace) -> None:
    out = render_project(Path(args.manifest), full=True)
    print(out)


def _cmd_qa(args: argparse.Namespace) -> None:
    report = qa_output(Path(args.output))
    print("PASS" if report["passed"] else "FAIL")
    print(Path(args.output) / "qa-report.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m detailpages.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ingest-assets")
    p.add_argument("--input", required=True)
    p.add_argument("--output", default=str(DEFAULT_ASSET_INDEX))
    p.add_argument("--source-type", default="unknown")
    p.add_argument("--source-url", default="")
    p.set_defaults(func=_cmd_ingest)

    p = sub.add_parser("make-review-sheet")
    p.add_argument("--asset-index", default=str(DEFAULT_ASSET_INDEX))
    p.add_argument("--output")
    p.set_defaults(func=_cmd_review)

    p = sub.add_parser("mask-assets")
    p.add_argument("--asset-index", default=str(DEFAULT_ASSET_INDEX))
    p.set_defaults(func=_cmd_mask)

    p = sub.add_parser("approve-assets")
    p.add_argument("--review-sheet", required=True)
    p.add_argument("--asset-index")
    p.set_defaults(func=_cmd_approve)

    p = sub.add_parser("render-preview")
    p.add_argument("--manifest", required=True)
    p.set_defaults(func=_cmd_render_preview)

    p = sub.add_parser("render-full")
    p.add_argument("--manifest", required=True)
    p.set_defaults(func=_cmd_render_full)

    p = sub.add_parser("qa")
    p.add_argument("--output", required=True)
    p.set_defaults(func=_cmd_qa)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
