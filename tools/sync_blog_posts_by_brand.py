from __future__ import annotations

import csv
import shutil
from pathlib import Path


WORKSPACE = Path(r"C:\Users\home\Documents\detailpages")
MANIFEST = WORKSPACE / "blog-writing-corpus" / "compiled" / "blog-corpus-manifest.csv"
READY_ROOT = WORKSPACE / "franchise-photo-library" / "_ready-for-detail-page"
OUTPUT_ROOT = WORKSPACE / "blog-writing-corpus" / "compiled" / "by-brand"


BRANDS = [
    ("megacoffee", "01_megacoffee", ["메가커피", "메가"]),
    ("subway", "02_subway", ["써브웨이", "서브웨이"]),
    ("lotteria", "03_lotteria", ["롯데리아"]),
    ("composecoffee", "04_composecoffee", ["컴포즈커피", "컴포즈"]),
    ("woozoo-coffee", "05_woozoo-coffee", ["우지커피"]),
    ("twosome-place", "06_twosome-place", ["투썸플레이스", "투썸"]),
    ("baskin-robbins", "07_baskin-robbins", ["배스킨라빈스", "베스킨라빈스"]),
    ("paris-baguette", "08_paris-baguette", ["파리바게뜨", "파리바게트"]),
    ("paikdabang", "09_paikdabang", ["빽다방"]),
]


def safe_name(name: str) -> str:
    for ch in '\\/:*?"<>|':
        name = name.replace(ch, "_")
    return " ".join(name.split()).strip()


def read_text(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "cp949"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", errors="replace")


def resolve_brand(row: dict[str, str]) -> tuple[str, str]:
    search_text = " ".join(
        [
            row.get("original_path", ""),
            row.get("relative_path", ""),
            row.get("parent_folder", ""),
            row.get("file_name", ""),
            row.get("first_nonempty_line", ""),
        ]
    )
    for slug, ready, keys in BRANDS:
        if any(key in search_text for key in keys):
            return slug, ready
    return "unknown", "_unknown"


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(MANIFEST.open("r", encoding="utf-8-sig", newline="")))

    groups: dict[str, list[dict[str, str]]] = {}
    ready_by_slug: dict[str, str] = {}
    for row in rows:
        slug, ready = resolve_brand(row)
        row["brand_slug"] = slug
        row["ready_brand_folder"] = ready
        groups.setdefault(slug, []).append(row)
        ready_by_slug[slug] = ready

    summary_rows: list[dict[str, str | int]] = []
    for slug in sorted(groups):
        items = sorted(groups[slug], key=lambda r: int(r["seq"]))
        ready_name = ready_by_slug[slug]

        brand_out = OUTPUT_ROOT / slug
        if brand_out.exists():
            shutil.rmtree(brand_out)
        brand_out.mkdir(parents=True, exist_ok=True)

        ready_blog_dir: Path | None = None
        if ready_name != "_unknown":
            ready_brand_dir = READY_ROOT / ready_name
            if ready_brand_dir.exists():
                ready_blog_dir = ready_brand_dir / "00_blog_posts"
                if ready_blog_dir.exists():
                    shutil.rmtree(ready_blog_dir)
                ready_blog_dir.mkdir(parents=True, exist_ok=True)

        compiled_lines = [
            f"# Blog posts for {slug}",
            "",
            f"- Posts: {len(items)}",
            "",
        ]
        local_manifest: list[dict[str, str | int]] = []

        for index, item in enumerate(items, 1):
            raw_copy = Path(item["raw_copy_path"])
            copy_name = f"{slug}_{index:03d}_{safe_name(item['file_name'])}"
            brand_copy = brand_out / copy_name
            shutil.copy2(raw_copy, brand_copy)

            ready_copy = ""
            if ready_blog_dir:
                ready_copy_path = ready_blog_dir / copy_name
                shutil.copy2(raw_copy, ready_copy_path)
                ready_copy = str(ready_copy_path)

            text = read_text(raw_copy).replace("\r\n", "\n").replace("\r", "\n").strip()
            compiled_lines.extend(
                [
                    "---",
                    "",
                    f"## Post {index} - {item['file_name']}",
                    "",
                    f"- Original: {item['original_path']}",
                    f"- Ready copy: {ready_copy}",
                    "",
                    "----- BEGIN POST TEXT -----",
                    text,
                    "----- END POST TEXT -----",
                    "",
                ]
            )

            local_manifest.append(
                {
                    "brand_slug": slug,
                    "seq_in_brand": index,
                    "corpus_seq": item["seq"],
                    "file_name": item["file_name"],
                    "original_path": item["original_path"],
                    "brand_copy_path": str(brand_copy),
                    "ready_copy_path": ready_copy,
                    "char_count": item["char_count"],
                }
            )

        compiled_path = brand_out / f"all-posts-{slug}.md"
        compiled_path.write_text("\n".join(compiled_lines), encoding="utf-8")
        manifest_path = brand_out / f"manifest-{slug}.csv"
        with manifest_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(local_manifest[0].keys()))
            writer.writeheader()
            writer.writerows(local_manifest)

        if ready_blog_dir:
            shutil.copy2(compiled_path, ready_blog_dir / "all-blog-posts.md")
            shutil.copy2(manifest_path, ready_blog_dir / "manifest.csv")

        summary_rows.append(
            {
                "brand_slug": slug,
                "ready_folder": ready_name,
                "posts": len(items),
                "compiled": str(compiled_path),
                "ready_blog_dir": str(ready_blog_dir or ""),
            }
        )

    summary_path = OUTPUT_ROOT / "brand-blog-summary.csv"
    with summary_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    for row in summary_rows:
        print(f"{row['brand_slug']}: {row['posts']} posts -> {row['ready_blog_dir']}")


if __name__ == "__main__":
    main()
