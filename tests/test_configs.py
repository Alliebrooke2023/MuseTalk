"""Sanity checks on the YAML configs under ``configs/``.

These guard against typos and structural drift in the config files that drive
every inference / training entrypoint, without needing any model weights.
"""

import glob
import os

import pytest
import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_GLOB = os.path.join(REPO_ROOT, "configs", "**", "*.yaml")

ALL_CONFIGS = sorted(glob.glob(CONFIG_GLOB, recursive=True))


def test_configs_exist():
    assert ALL_CONFIGS, "no YAML configs found under configs/"


@pytest.mark.parametrize("path", ALL_CONFIGS, ids=lambda p: os.path.relpath(p, REPO_ROOT))
def test_config_parses(path):
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert data is not None, f"{path} parsed to empty/None"
    assert isinstance(data, dict), f"{path} top level is not a mapping"


def _load(rel_path):
    with open(os.path.join(REPO_ROOT, rel_path), "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_inference_test_config_tasks_have_required_keys():
    data = _load("configs/inference/test.yaml")
    assert data, "test.yaml is empty"
    for task_name, task in data.items():
        assert "video_path" in task, f"{task_name} missing video_path"
        assert "audio_path" in task, f"{task_name} missing audio_path"
        if "bbox_shift" in task:
            assert isinstance(task["bbox_shift"], int)


def test_realtime_config_avatars_have_required_keys():
    data = _load("configs/inference/realtime.yaml")
    assert data, "realtime.yaml is empty"
    for avatar_name, avatar in data.items():
        assert "video_path" in avatar, f"{avatar_name} missing video_path"
        assert "audio_clips" in avatar, f"{avatar_name} missing audio_clips"
        assert isinstance(avatar["audio_clips"], dict) and avatar["audio_clips"], \
            f"{avatar_name} audio_clips must be a non-empty mapping"
        assert isinstance(avatar.get("preparation", False), bool)
