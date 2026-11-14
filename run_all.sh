#!/usr/bin/env bash
# Полный запуск с чистого окружения: ./run_all.sh [флаги run_all.py]
set -euo pipefail
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt
python run_all.py "$@"
