# voxbridge/hub/cli.py
import argparse
import subprocess
import sys

from .registry import ROOT, load_models, load_yaml, plan_pipeline


def main(argv=None):
    ap = argparse.ArgumentParser(prog="hub")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sw = sub.add_parser("swarm")
    sw.add_argument("stack")
    run = sub.add_parser("run")
    run.add_argument("pipeline")
    run.add_argument("--set", action="append", default=[], metavar="KEY=VAL")
    run.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    if a.cmd == "swarm":
        import json
        from .swarm import plan_stack
        print(json.dumps(plan_stack(a.stack), indent=2))
        return 0

    models = load_models()
    if a.cmd == "list":
        for m in models.values():
            print(f"{m['name']:<16} {m['kind']}")
        return 0

    path = ROOT / "configs" / "pipelines" / f"{a.pipeline}.yaml"
    inputs = dict(kv.split("=", 1) for kv in a.set)
    for name, cmd in plan_pipeline(load_yaml(path), models, inputs):
        print(f"[{name}] {' '.join(cmd)}")
        if not a.dry_run:
            subprocess.run(cmd, check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
