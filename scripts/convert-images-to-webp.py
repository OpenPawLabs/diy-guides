#!/usr/bin/env python3
"""Convert guide-referenced PNG/JPG images to WebP and update MDX paths."""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from guide_images import (  # noqa: E402
    CONVERTIBLE_EXTENSIONS,
    collect_image_refs,
    format_bytes,
    repo_root_from,
)


def prepare_for_webp(image: Image.Image) -> Image.Image:
    """Normalize mode so WebP keeps alpha when present; never resize."""
    if image.mode in ("RGBA", "LA"):
        return image.convert("RGBA")
    if image.mode == "P":
        if "transparency" in image.info:
            return image.convert("RGBA")
        return image.convert("RGB")
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


def convert_to_webp(
    source: Path,
    dest: Path,
    *,
    quality: int,
    lossless: bool,
) -> None:
    with Image.open(source) as image:
        prepared = prepare_for_webp(image)
        save_kwargs: dict = {"method": 6}
        if lossless:
            save_kwargs["lossless"] = True
        else:
            save_kwargs["quality"] = quality
        prepared.save(dest, "WEBP", **save_kwargs)


def webp_ref(ref: str) -> str:
    return str(Path(ref).with_suffix(".webp")).replace("\\", "/")


def rewrite_guide(guide_path: Path, replacements: dict[str, str], *, dry_run: bool) -> int:
    """Replace old ./images refs with .webp. Returns number of substitutions."""
    text = guide_path.read_text(encoding="utf-8")
    updated = text
    count = 0
    # Longer paths first so foo.png does not partially match foo-1.png families incorrectly.
    for old, new in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        occurrences = updated.count(old)
        if occurrences:
            updated = updated.replace(old, new)
            count += occurrences
    if count and not dry_run and updated != text:
        guide_path.write_text(updated, encoding="utf-8", newline="\n")
    return count


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert guide-referenced PNG/JPG images to WebP and update MDX refs."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (default: parent of scripts/)",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=92,
        help="Lossy WebP quality 0-100 (default: 92)",
    )
    parser.add_argument(
        "--lossless",
        action="store_true",
        help="Encode lossless WebP instead of quality-based lossy",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned work without writing or deleting files",
    )
    args = parser.parse_args()

    if not 0 <= args.quality <= 100:
        print("error: --quality must be between 0 and 100", file=sys.stderr)
        return 2

    root = (args.root or repo_root_from(__file__)).resolve()
    refs = collect_image_refs(root, extensions=CONVERTIBLE_EXTENSIONS)

    by_source: dict[Path, list] = defaultdict(list)
    for ref in refs:
        by_source[ref.source_path].append(ref)

    if not by_source:
        print("No convertible image references found.")
        return 0

    mode = "lossless" if args.lossless else f"quality={args.quality}"
    print(f"Root: {root}")
    print(f"Mode: {mode}{' (dry-run)' if args.dry_run else ''}")
    print()

    converted = 0
    skipped_missing = 0
    skipped_webp = 0
    failed = 0
    bytes_before = 0
    bytes_after = 0
    # guide_path -> {old_ref: new_ref} for successful converts only
    guide_replacements: dict[Path, dict[str, str]] = defaultdict(dict)
    sources_to_delete: list[Path] = []

    for source, source_refs in sorted(by_source.items(), key=lambda item: str(item[0])):
        sample_ref = source_refs[0].ref
        new_ref = webp_ref(sample_ref)
        dest = source.with_suffix(".webp")
        try:
            rel = source.relative_to(root)
        except ValueError:
            rel = source

        if not source.exists():
            print(f"  SKIP missing: {sample_ref} (from {source_refs[0].guide_path.relative_to(root)})")
            skipped_missing += 1
            continue

        if source.suffix.lower() == ".webp":
            skipped_webp += 1
            continue

        before = source.stat().st_size

        try:
            if args.dry_run:
                after = before  # unknown; report planned only
                print(f"  CONVERT {rel} -> {dest.name} ({format_bytes(before)})")
            else:
                convert_to_webp(
                    source,
                    dest,
                    quality=args.quality,
                    lossless=args.lossless,
                )
                after = dest.stat().st_size
                print(
                    f"  CONVERT {rel} -> {dest.name} "
                    f"({format_bytes(before)} -> {format_bytes(after)})"
                )
                bytes_before += before
                bytes_after += after
                sources_to_delete.append(source)

            for ref in source_refs:
                guide_replacements[ref.guide_path][ref.ref] = new_ref
            converted += 1
        except Exception as exc:  # noqa: BLE001 - report and continue batch
            print(f"  FAIL {rel}: {exc}", file=sys.stderr)
            failed += 1

    print()
    rewrite_count = 0
    for guide_path, replacements in sorted(guide_replacements.items(), key=lambda item: str(item[0])):
        n = rewrite_guide(guide_path, replacements, dry_run=args.dry_run)
        if n:
            action = "WOULD REWRITE" if args.dry_run else "REWRITE"
            print(f"  {action} {guide_path.relative_to(root)} ({n} ref(s))")
            rewrite_count += n

    if not args.dry_run:
        print()
        for source in sources_to_delete:
            source.unlink()
            print(f"  DELETE {source.relative_to(root)}")

    print()
    print(f"Converted: {converted}")
    print(f"Missing:   {skipped_missing}")
    if failed:
        print(f"Failed:    {failed}")
    print(f"MDX refs:  {rewrite_count}")
    if not args.dry_run and bytes_before:
        saved = bytes_before - bytes_after
        pct = (saved / bytes_before) * 100
        print(
            f"Size:      {format_bytes(bytes_before)} -> {format_bytes(bytes_after)} "
            f"({format_bytes(saved)} saved, {pct:.1f}%)"
        )
    elif args.dry_run:
        print("Dry-run complete; no files were modified.")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
