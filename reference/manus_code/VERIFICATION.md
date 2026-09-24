# Verification Results

All four portable scripts were executed successfully with the pinned dependency versions on September 24, 2026.

Each generated PNG was compared byte-for-byte with its approved example output using `cmp`.

| Portable script | Result |
| --- | --- |
| `01_extend_top3_volume.py` | Byte-identical |
| `02_extend_monthly_traffic.py` | Byte-identical |
| `03_extend_top100_keywords.py` | Byte-identical |
| `04_rebuild_top100_competitors_2k_scale.py` | Byte-identical |

This verifies that the package-relative path changes and explicit bundled-font registration do not change the rendered files in the tested environment.
