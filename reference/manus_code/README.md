# Exact Chart Generation Code

This package contains the exact Python scripts used to create the four delivered January–August charts, the three original source images, the font used for labels, pinned dependencies, and known-good output files.

## What was used

Two rendering methods were used because the requested outputs had different requirements.

1. **Pillow image extension** was used for the first three charts. It preserves every existing source-image pixel, appends July and August to the right, calibrates values to the source chart’s y-axis, and draws only the new grid, lines, markers, labels, and month names.
2. **Matplotlib with NumPy** was used for the final competitor-only Top 100 chart. That chart had to remove New Holland and Vermeer and rebuild the vertical scale at 2K intervals, so the entire chart was rendered from structured values.

Pinned versions:

- Python 3.11
- Pillow 12.3.0
- Matplotlib 3.11.1
- NumPy 2.5.1

## Package contents

```text
chart_generator_code/
├── exact_scripts/
│   ├── 01_extend_top3_volume.py
│   ├── 02_extend_monthly_traffic.py
│   ├── 03_extend_top100_keywords.py
│   └── 04_rebuild_top100_competitors_2k_scale.py
├── portable_scripts/
│   ├── 01_extend_top3_volume.py
│   ├── 02_extend_monthly_traffic.py
│   ├── 03_extend_top100_keywords.py
│   └── 04_rebuild_top100_competitors_2k_scale.py
├── source_images/
├── example_outputs/
├── generated/
├── fonts/
├── requirements.txt
├── run_all.sh
└── SHA256SUMS
```

The files in `exact_scripts/` are verbatim copies of the scripts used in the sandbox. They retain the original absolute sandbox paths.

The files in `portable_scripts/` preserve the same values, coordinates, colors, rendering settings, and label placement. Only asset/output paths were changed to package-relative paths. The Matplotlib portable script also explicitly selects its headless renderer and registers the bundled font.

## Install and run

Run these commands from the package directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
./run_all.sh
```

If `run_all.sh` is not executable after downloading or unzipping, run:

```bash
chmod +x run_all.sh
./run_all.sh
```

The generated images will appear in `generated/`.

You can also run one chart at a time:

```bash
python3 portable_scripts/01_extend_top3_volume.py
python3 portable_scripts/02_extend_monthly_traffic.py
python3 portable_scripts/03_extend_top100_keywords.py
python3 portable_scripts/04_rebuild_top100_competitors_2k_scale.py
```

## Script 1: Volume of Top 3

File: `portable_scripts/01_extend_top3_volume.py`

Source image: `source_images/top3_volume_source.webp`

Output: `generated/seo_volume_top3_jan_aug_2026.png`

Edit the July and August values in the `series` list. Each entry has this structure:

```python
('Competitor name', june_anchor_y, july_value, august_value, rgba_color)
```

The `june_anchor_y` is a pixel coordinate recovered from the source screenshot. Do not change it unless the source image changes. Labels are positioned by the `draw_centered(...)` calls because the dense clusters require manual placement.

## Script 2: Monthly traffic

File: `portable_scripts/02_extend_monthly_traffic.py`

Source image: `source_images/monthly_traffic_source.webp`

Output: `generated/monthly_traffic_jan_aug_2026.png`

Edit the July and August values in the `series` list. This script adds a new 22K band above the original chart because Fecon’s August value exceeds the original 20K maximum. The original chart remains an untouched pixel block shifted downward by 100 pixels.

If future values exceed 22K, the `TOP`, canvas height, new grid line, and y-axis label logic will need to be generalized. For the reusable app described in the PRD, this should become automatic scale calculation rather than a hard-coded adjustment.

## Script 3: Full Top 100 keywords

File: `portable_scripts/03_extend_top100_keywords.py`

Source image: `source_images/top100_keywords_source.webp`

Output: `generated/top_100_keywords_jan_aug_2026.png`

Edit July and August in the `series` list. Values are converted to y-coordinates using:

```python
y = axis_intercept - axis_slope * value
```

The slope and intercept were calibrated from labeled points in the source chart. They are specific to that source image and y-axis.

## Script 4: Top 100 competitors with a 2K scale

File: `portable_scripts/04_rebuild_top100_competitors_2k_scale.py`

Output: `generated/top_100_keywords_competitors_original_style_jan_aug_2026.png`

This is the Matplotlib chart. The complete January–August data is stored in the `series` dictionary:

```python
'Virnig': {
    'v': [5710, 5758, 5263, 5085, 4834, 3954, 3765, 3642],
    'c': '#EF6CC1'
}
```

The month labels are stored in `months`. Every series must contain the same number of values as the month list.

The requested axis appears here:

```python
ax.set_ylim(0, 6400)
ax.set_yticks([0, 2000, 4000, 6000])
ax.set_yticklabels(['0K', '2K', '4K', '6K'])
```

Competitor callout locations are stored in `callouts`. Point-label offsets are stored in `main_offsets` and `small_offsets`. Those positions are intentionally explicit because automatic placement would not reproduce the approved image exactly.

## Why some positions are hard-coded

The original inputs were screenshots rather than their underlying chart configuration. To preserve those screenshots exactly, the extension scripts use calibrated pixel positions and source-specific anchors. The numeric y-coordinate is calculated, but labels in crowded regions are manually staggered.

This is correct for exact reproduction of these specific files. A reusable application should instead store values and styling in a JSON chart specification, calculate axes dynamically, detect label collisions, and allow users to drag or override labels. The accompanying PRD specifies that generalized architecture.

## Reproducibility

`example_outputs/` contains the known-good files made by the exact scripts. `SHA256SUMS` records hashes for package assets and outputs. On the pinned environment, the portable scripts are tested against those examples.

Exact raster output depends on the same dependency versions, font file, source images, and rendering environment. The bundled Liberation Sans font removes the largest source of cross-machine variation.

## Asset note

The source `.webp` files are the images supplied for this work. They are included so the Pillow scripts can reproduce the delivered extensions. The bundled font remains subject to its included license and copyright notice.
