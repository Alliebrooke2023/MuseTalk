# voxbridge/hub/registry.py
import re
import shlex
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
KINDS = {"lipsync", "tts", "stt", "llm", "other"}
PLACEHOLDER = re.compile(r"\{(\w+)\}")


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_models(models_dir=None):
    """Load every configs/models/*.yaml into {name: config}."""
    models_dir = Path(models_dir or ROOT / "configs" / "models")
    models = {}
    for p in sorted(models_dir.glob("*.yaml")):
        cfg = load_yaml(p)
        validate_model(cfg, p.name)
        models[cfg["name"]] = cfg
    return models


def validate_model(cfg, label="model"):
    for key in ("name", "kind", "command"):
        if key not in cfg:
            raise ValueError(f"{label}: missing '{key}'")
    if cfg["kind"] not in KINDS:
        raise ValueError(f"{label}: kind must be one of {sorted(KINDS)}")


def render(template, values):
    """Fill {placeholders}; raise on any that are missing."""
    missing = [k for k in PLACEHOLDER.findall(template) if k not in values]
    if missing:
        raise KeyError(f"missing values: {missing}")
    return PLACEHOLDER.sub(lambda m: str(values[m.group(1)]), template)


def build_command(model, values):
    """Merge model defaults with overrides and return an argv list."""
    merged = {**model.get("defaults", {}), **values}
    return shlex.split(render(model["command"], merged))


def plan_pipeline(pipeline, models, inputs):
    """Return [(step_name, argv)] with outputs of earlier steps feeding later ones."""
    values = dict(pipeline.get("inputs", {}), **inputs)
    plan = []
    for step in pipeline["steps"]:
        model = models[step["model"]]
        step_vals = {k: render(str(v), values) for k, v in step.get("args", {}).items()}
        plan.append((step["name"], build_command(model, {**values, **step_vals})))
        for out_key, out_tpl in step.get("outputs", {}).items():
            values[out_key] = render(str(out_tpl), values)
    return plan
