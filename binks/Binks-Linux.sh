#!/usr/bin/env bash
# Binks-Linux.sh - launch Binks as a local app (Linux)
cd "$(dirname "$0")"
python3 -m pip install -r requirements.txt >/dev/null 2>&1
exec python3 binks.py start
