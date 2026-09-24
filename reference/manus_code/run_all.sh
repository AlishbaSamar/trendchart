#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
mkdir -p generated

python3 portable_scripts/01_extend_top3_volume.py
python3 portable_scripts/02_extend_monthly_traffic.py
python3 portable_scripts/03_extend_top100_keywords.py
python3 portable_scripts/04_rebuild_top100_competitors_2k_scale.py

echo "Generated files are in: $ROOT/generated"
