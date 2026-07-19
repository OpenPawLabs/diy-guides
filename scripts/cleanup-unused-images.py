#!/usr/bin/env python3
"""Report (and optionally delete) files under images/ that no guide references."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from guide_images import (  # noqa: E402
    RASTER_EXTENSIONS,
    collect_image_refs,
    find_images_dirs,
    format_bytes,
    repair_mdx_image_prefixes,
    repo_root_from,
)

UNUSED_RATIO_ABORT = 0.5

# Build-time derivatives from diy-guide-images — treat as used when the canonical exists.
VARIANT_NAME_RE = re.compile(r"^.+\.w\d+\.avif$", re.IGNORECASE)


def is_derived_asset(path: Path, referenced: set[Path]) -> bool:
    # images/thumbnails/* — keep when a matching (or any) canonical lives in images/
    if path.parent.name == "thumbnails":
        images_dir = path.parent.parent
        if path.name == "variants.json":
            return any(ref.parent.resolve() == images_dir.resolve() for ref in referenced)
        if not VARIANT_NAME_RE.match(path.name):
            return False
        stem = path.name.rsplit(".w", 1)[0]
        for ref in referenced:
            if ref.parent.resolve() == images_dir.resolve() and ref.stem == stem:
                return True
        return False

    # Legacy flat layout (pre-thumbnails/) — keep if the canonical is referenced
    if path.name == "variants.json":
        return True
    if not VARIANT_NAME_RE.match(path.name):
        return False
    stem = path.name.rsplit(".w", 1)[0]
    parent = path.parent
    for ref in referenced:
        if ref.parent.resolve() == parent.resolve() and ref.stem == stem:
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="List or delete files under images/ that are not referenced by any guide.mdx."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (default: parent of scripts/)",
    )
    parser.add_argument(
        "--rasters-only",
        action="store_true",
        help="Only consider raster images (png/jpg/jpeg/webp) as unused candidates",
    )
    parser.add_argument(
        "--include-non-rasters",
        action="store_true",
        help="Allow --delete to remove non-raster unused files (e.g. .step)",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete unused files (default is report-only)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow --delete even when unused ratio is unusually high",
    )
    args = parser.parse_args()

    root = (args.root or repo_root_from(__file__)).resolve()

    repaired_files, repaired_refs = repair_mdx_image_prefixes(root, dry_run=False)
    if repaired_files:
        print(
            f"Repaired ./ prefix on {repaired_refs} image ref(s) "
            f"across {repaired_files} guide(s)."
        )
        print()

    refs = collect_image_refs(root)
    referenced = {ref.source_path.resolve() for ref in refs}
    existing_referenced = sum(1 for path in referenced if path.exists())

    candidates: list[Path] = []
    unused: list[Path] = []
    for images_dir in find_images_dirs(root):
        for path in sorted(images_dir.iterdir()):
            if not path.is_file():
                continue
            if path.name.startswith("."):
                continue
            if args.rasters_only and path.suffix.lower() not in RASTER_EXTENSIONS:
                continue
            candidates.append(path)
            if path.resolve() not in referenced and not is_derived_asset(path, referenced):
                unused.append(path)

    print(f"Root: {root}")
    print(f"Referenced image paths: {len(referenced)} ({existing_referenced} exist on disk)")
    print(f"Candidate files: {len(candidates)}")
    print(f"Unused files: {len(unused)}")
    if args.delete:
        print("Mode: delete")
    else:
        print("Mode: report only (pass --delete to remove)")
    print()

    if args.delete:
        if existing_referenced == 0 and candidates:
            print(
                "error: refusing to delete — no referenced image files exist on disk. "
                "Guides may not be scanning correctly; fix refs before using --delete.",
                file=sys.stderr,
            )
            return 2
        if candidates and len(unused) / len(candidates) >= UNUSED_RATIO_ABORT and not args.force:
            pct = (len(unused) / len(candidates)) * 100
            print(
                f"error: refusing to delete — {len(unused)}/{len(candidates)} "
                f"({pct:.0f}%) of images look unused (>= {UNUSED_RATIO_ABORT:.0%}). "
                "Re-check guide refs, or pass --force if this is intentional.",
                file=sys.stderr,
            )
            return 2

    total = 0
    deleted = 0
    skipped_non_raster = 0

    for path in unused:
        size = path.stat().st_size
        total += size
        is_raster = path.suffix.lower() in RASTER_EXTENSIONS
        try:
            rel = path.relative_to(root)
        except ValueError:
            rel = path

        if args.delete:
            if not is_raster and not args.include_non_rasters:
                print(f"  SKIP non-raster (use --include-non-rasters): {rel}")
                skipped_non_raster += 1
                continue
            path.unlink()
            print(f"  DELETE {rel} ({format_bytes(size)})")
            deleted += 1
        else:
            kind = "raster" if is_raster else "other"
            print(f"  UNUSED [{kind}] {rel} ({format_bytes(size)})")

    print()
    print(f"Reclaimable: {format_bytes(total)} across {len(unused)} file(s)")
    if args.delete:
        print(f"Deleted:     {deleted}")
        if skipped_non_raster:
            print(f"Skipped:     {skipped_non_raster} non-raster(s)")
    else:
        print("No files deleted. Re-run with --delete after reviewing the list.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
