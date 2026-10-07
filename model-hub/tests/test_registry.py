# model-hub/tests/test_registry.py
import pytest

from hub.registry import (ROOT, build_command, load_models, load_yaml,
                          plan_pipeline, validate_model)


def test_loads_all_models():
    assert {"musetalk_v1", "musetalk_v15", "tts_example"} <= set(load_models())


def test_build_command_uses_defaults_and_overrides():
    m = load_models()["musetalk_v15"]
    cmd = build_command(m, {"result_dir": "out"})
    assert cmd[cmd.index("--result_dir") + 1] == "out"
    assert "v15" in cmd


def test_missing_value_raises():
    with pytest.raises(KeyError):
        build_command(load_models()["tts_example"], {})


def test_bad_kind_rejected():
    with pytest.raises(ValueError):
        validate_model({"name": "x", "kind": "nope", "command": "y"})


def test_pipeline_chains_outputs():
    p = load_yaml(ROOT / "configs" / "pipelines" / "talking_avatar.yaml")
    plan = plan_pipeline(p, load_models(), {"text": "hi"})
    assert [n for n, _ in plan] == ["speak", "lipsync"]
    assert "results/hub/speech.wav" in plan[0][1]
    assert "results/hub/video" in plan[1][1]
