#!/usr/bin/env bash
# Binks.command - double-click to launch Binks as a local app (macOS)
cd "$(dirname "$0")"
python3 -m pip install -r requirements.txt >/dev/null 2>&1
python3 binks.py start
