# voxbridge/hub/swarm.py
"""Turn agent specs + a stack into per-bot spawn requests (one container each)."""
from .registry import ROOT, load_yaml


def load_agent(name):
    cfg = load_yaml(ROOT / "configs" / "agents" / f"{name}.yaml")
    for key in ("name", "role", "prompt"):
        if key not in cfg:
            raise ValueError(f"agent {name}: missing '{key}'")
    return cfg


def plan_stack(stack_name):
    """Return one spawn request per agent. Each runs in its own container."""
    stack = load_yaml(ROOT / "configs" / "stacks" / f"{stack_name}.yaml")
    team = ", ".join(stack["agents"])
    plan = []
    for name in stack["agents"]:
        a = load_agent(name)
        plan.append({
            "title": f"{stack['name']}: {a['name']}",
            "tags": [f"stack:{stack['name']}", *a.get("tags", [])],
            "prompt": (f"{a['prompt']}\n\nOutcome: {stack['outcome']}\n"
                       f"Role: {a['role']}\nTeam: {team}"),
        })
    return plan
