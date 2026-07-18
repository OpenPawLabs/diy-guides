"""Shared helpers for finding guide image references."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

RASTER_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".webp"})
CONVERTIBLE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg"})

# Matches "./images/<file>" inside single or double quotes in MDX/JSX.
IMAGE_REF_RE = re.compile(r"""['"](\./images/[^'"]+)['"]""")


@dataclass(frozen=True)
class ImageRef:
    """A raster/path reference from a guide.mdx file."""

    guide_path: Path
    ref: str  # e.g. "./images/foo.png"
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


def collect_image_refs(
    root: Path,
    *,
    extensions: frozenset[str] | None = None,
) -> list[ImageRef]:
    """Collect ./images/... refs from all guide.mdx files under root."""
    refs: list[ImageRef] = []
    for guide in find_guide_mdx(root):
        text = guide.read_text(encoding="utf-8")
        for match in IMAGE_REF_RE.finditer(text):
            ref = match.group(1)
            ext = Path(ref).suffix.lower()
            if extensions is not None and ext not in extensions:
                continue
            source = (guide.parent / ref).resolve()
            refs.append(ImageRef(guide_path=guide, ref=ref, source_path=source))
    return refs


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
