"""Shared helpers for finding guide image references."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

RASTER_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".webp"})
CONVERTIBLE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg"})

# Matches "./images/<file>" or "images/<file>" inside quotes in MDX/JSX.
IMAGE_REF_RE = re.compile(r"""['"]((?:\./)?images/[^'"]+)['"]""")

# Quoted "images/..." / 'images/...' missing the "./" prefix (Windows Path bug residue).
MISSING_DOT_SLASH_RE = re.compile(r"""(['"])images/""")


@dataclass(frozen=True)
class ImageRef:
    """A raster/path reference from a guide.mdx file."""

    guide_path: Path
    ref: str  # normalized, e.g. "./images/foo.png"
    raw_ref: str  # exact text from MDX (may omit "./")
    source_path: Path  # resolved absolute path

    @property
    def extension(self) -> str:
        return Path(self.ref).suffix.lower()


def repo_root_from(script_file: str | Path) -> Path:
    return Path(script_file).resolve().parent.parent


def find_guide_mdx(root: Path) -> list[Path]:
    return sorted(root.rglob("guide.mdx"))


def find_images_dirs(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("images") if p.is_dir())


def normalize_image_ref(ref: str) -> str:
    """Normalize to ./images/... form."""
    if ref.startswith("./images/"):
        return ref
    if ref.startswith("images/"):
        return f"./{ref}"
    return ref


def collect_image_refs(
    root: Path,
    *,
    extensions: frozenset[str] | None = None,
) -> list[ImageRef]:
    """Collect images/ refs from all guide.mdx files under root."""
    refs: list[ImageRef] = []
    for guide in find_guide_mdx(root):
        text = guide.read_text(encoding="utf-8")
        for match in IMAGE_REF_RE.finditer(text):
            raw = match.group(1)
            ref = normalize_image_ref(raw)
            ext = Path(ref).suffix.lower()
            if extensions is not None and ext not in extensions:
                continue
            source = (guide.parent / ref).resolve()
            refs.append(
                ImageRef(
                    guide_path=guide,
                    ref=ref,
                    raw_ref=raw,
                    source_path=source,
                )
            )
    return refs


def repair_mdx_image_prefixes(root: Path, *, dry_run: bool = False) -> tuple[int, int]:
    """Rewrite quoted images/... to ./images/... in guide.mdx files.

    Returns (files_changed, replacements).
    """
    files_changed = 0
    replacements = 0
    for guide in find_guide_mdx(root):
        text = guide.read_text(encoding="utf-8")
        updated, n = MISSING_DOT_SLASH_RE.subn(r"\1./images/", text)
        if n == 0:
            continue
        replacements += n
        files_changed += 1
        if not dry_run:
            guide.write_text(updated, encoding="utf-8", newline="\n")
    return files_changed, replacements


def format_bytes(n: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    size = float(n)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{n} B"
