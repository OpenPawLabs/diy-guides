# diy-guides

Contains all of our DIY guides written for OpenPawLabs! Help fix/contribute today!

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
```

Suggested workflow: convert referenced images, review the cleanup report, then delete unused files.
