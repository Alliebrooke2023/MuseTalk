# voxbridge/tests/test_registry.py
import pytest

from hub.registry import (ROOT, build_command, load_models, load_yaml,
                          plan_pipeline, validate_model)


def test_loads_all_models():
    assert {"musetalk_v1", "musetalk_v15", "tts_example", "stt_whisper"} <= set(load_models())


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
    assert [n for n, _ in plan] == ["speak", "config", "lipsync"]
    assert "results/hub/speech.mp3" in plan[1][1]
    assert "results/hub/musetalk.yaml" in plan[2][1]


def test_transcribe_pipeline():
    p = load_yaml(ROOT / "configs" / "pipelines" / "transcribe.yaml")
    (name, cmd), = plan_pipeline(p, load_models(), {"audio_in": "a.wav"})
    assert name == "transcribe" and cmd[:2] == ["whisper", "a.wav"]


def test_swarm_plan_one_bot_per_agent():
    from hub.swarm import plan_stack
    plan = plan_stack("chief_of_staff")
    assert len(plan) == 4
    assert all("stack:chief_of_staff_stack" in p["tags"] for p in plan)
    assert "Team: chief_of_staff, inbox" in plan[0]["prompt"]


def test_sts_avatar_chains_all_steps():
    p = load_yaml(ROOT / "configs" / "pipelines" / "sts_avatar.yaml")
    plan = dict(plan_pipeline(p, load_models(), {"audio_in": "in/q.wav"}))
    assert list(plan) == ["transcribe", "think", "speak", "config", "lipsync"]
    assert "results/hub/q.txt" in plan["think"]
    assert "results/hub/reply.txt" in plan["speak"]
    assert "results/hub/reply.mp3" in plan["config"]


def test_voice_convert():
    p = load_yaml(ROOT / "configs" / "pipelines" / "voice_convert.yaml")
    (_, cmd), = plan_pipeline(p, load_models(), {"audio_in": "a.wav", "voice_ref": "me.wav"})
    assert cmd[cmd.index("--target") + 1] == "me.wav"


def test_musetalk_cfg_writes_yaml(tmp_path):
    from hub.musetalk_cfg import main
    out = tmp_path / "m.yaml"
    main(["--video", "v.mp4", "--audio", "a.mp3", "--out", str(out)])
    assert load_yaml(out) == {"task_0": {"video_path": "v.mp4", "audio_path": "a.mp3"}}
