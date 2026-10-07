# voxbridge/hub/musetalk_cfg.py
"""Write a one-task MuseTalk inference YAML for a given video + audio."""
import argparse
from pathlib import Path

import yaml


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    cfg = {"task_0": {"video_path": a.video, "audio_path": a.audio}}
    Path(a.out).write_text(yaml.safe_dump(cfg), encoding="utf-8")


if __name__ == "__main__":
    main()
