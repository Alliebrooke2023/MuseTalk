#!/usr/bin/env bash
# run.sh — start Binks on Linux/macOS
cd "$(dirname "$0")"
python3 -m pip install -r requirements.txt >/dev/null 2>&1 || true
exec python3 binks.py serve --port "${1:-8099}"
