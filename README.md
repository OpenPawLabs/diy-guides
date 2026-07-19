# diy-guides

Contains all of our DIY guides written for OpenPawLabs! Help fix/contribute today!

## Project manifests

Each project folder (for example `bb-lsm6dsv/`) includes a `project.json` that is the source of truth for:

- Project title and description
- **Ordered** list of guides shown on the docs site (cards, prev/next, progress)
- Per-guide card descriptions, plus `optional` / `shared` flags
- Optional route `slug` overrides (used for shared `common/` guides)

Guide display fields (`title`, `difficulty`, `timeEstimate`, `heroImage`, steps) still come from each guide’s `guide.mdx` header — do not duplicate titles in the manifest.

### Conventions

| Field | Meaning |
|-------|---------|
| `overview` | Project-relative path of the guide whose hero backs the project card |
| `guides[].path` | Project-relative for local guides (`0-overview`), or repo-root-relative for shared guides (`common/…`) |
| `guides[].slug` | Defaults to the final path segment; set only when the URL should differ |
| Array order | Site order |

When you add, remove, or reorder guides, edit `project.json` in the same change. Folders not listed in the manifest stay invisible on the site (useful for WIP drafts). The docs site validates that every listed path has a `guide.mdx`.

## Image scripts

Guides reference local rasters under each guide’s `images/` folder. Two scripts help keep those assets small and tidy.

### Setup

```bash
pip install -r scripts/requirements.txt
```

### Convert referenced images to WebP

Converts every PNG/JPG referenced by a `guide.mdx` to WebP (default quality `92`, full resolution, alpha preserved), rewrites the MDX paths, and deletes the converted originals.

```bash
# Preview without writing
python scripts/convert-images-to-webp.py --dry-run

# Convert (lossy WebP, quality 92)
python scripts/convert-images-to-webp.py

# Optional: custom quality or lossless encode
python scripts/convert-images-to-webp.py --quality 95
python scripts/convert-images-to-webp.py --lossless
```

### Clean up unused images

Reports files under any `images/` directory that no `guide.mdx` references. Deletion is opt-in.

```bash
# List unused files and reclaimable size
python scripts/cleanup-unused-images.py

# Only consider raster images in the report
python scripts/cleanup-unused-images.py --rasters-only

# Delete unused rasters (non-rasters need an extra flag)
python scripts/cleanup-unused-images.py --delete
python scripts/cleanup-unused-images.py --delete --include-non-rasters

# --delete aborts if nothing looks referenced, or if ≥50% of images
# look unused (pass --force only after reviewing that report)
python scripts/cleanup-unused-images.py --delete --force
```

Suggested workflow: convert referenced images, review the cleanup report, then delete unused files.

### Responsive size variants (build hosts, not this repo)

Do **not** commit thumbnail derivatives here. The docs site (and other publishers) run
[`diy-guide-images`](https://github.com/OpenPawLabs/diy-guides-ui-react) from
`@openpawlabs/diy-guides-ui` after syncing this tree, writing AVIF width variants
under `images/thumbnails/` (plus `variants.json`). Authors only commit canonical
sources under each guide’s `images/` folder. Delete `images/thumbnails/` locally
to force a regenerate.

To preview locally:

```bash
pnpm --dir ../diy-guides-ui-react exec diy-guide-images ./bb-lsm6dsv/0-overview
```
