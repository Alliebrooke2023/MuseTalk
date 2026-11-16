# binks.py
"""Binks CLI — one entry point for everything.

Examples (PowerShell on Windows, bash on Linux/Mac):
    python binks.py serve                 # start the app on port 8099
    python binks.py serve --port 9000
    python binks.py discover              # find ONVIF cameras on the LAN
    python binks.py snapshot front-door   # save one JPEG from a camera
    python binks.py add --id cam1 --name "Shop" --kind rtsp \
        --url rtsp://user:pass@192.168.1.50:554/stream1
    python binks.py selftest              # verify the install with no hardware
"""
from __future__ import annotations
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from binks_sdk import CameraManager, Store, discover_onvif, serve  # noqa: E402


def cmd_serve(a):
    serve(host=a.host, port=a.port, store_path=a.data, motion=not a.no_motion)


def cmd_start(a):
    from binks_sdk.launch import start
    start(port=a.port, store_path=a.data, motion=not a.no_motion,
          window=not a.no_window)


def cmd_discover(a):
    devs = discover_onvif(timeout=a.timeout)
    print(json.dumps(devs, indent=2))
    if not devs:
        print("No ONVIF cameras answered. (On many LANs this is normal — "
              "add cameras by URL with 'python binks.py add'.)", file=sys.stderr)


def cmd_add(a):
    store = Store(a.data)
    cam = {"id": a.id, "name": a.name or a.id, "loc": a.loc,
           "kind": a.kind, "url": a.url, "user": a.user, "password": a.password}
    store.add_camera({k: v for k, v in cam.items() if v})
    print(f"Added camera '{a.id}' ({a.kind}).")


def cmd_list(a):
    store = Store(a.data)
    for c in store.cameras():
        print(f"{c['id']:<16} {c.get('kind','?'):<10} {c.get('name','')}")


def cmd_snapshot(a):
    store = Store(a.data)
    mgr = CameraManager(store.cameras())
    cam = mgr.get(a.id)
    if not cam:
        sys.exit(f"No camera '{a.id}'. Run 'python binks.py list'.")
    out = a.out or f"{a.id}.jpg"
    with open(out, "wb") as f:
        f.write(cam.snapshot())
    print(f"Saved {out}")


def cmd_selftest(a):
    from selftest import run
    sys.exit(0 if run() else 1)


def main():
    ap = argparse.ArgumentParser(prog="binks", description="Binks local camera toolkit")
    ap.add_argument("--data", default=os.path.join(HERE, "binks_data.json"))
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="run the web app + API")
    s.add_argument("--host", default="0.0.0.0")
    s.add_argument("--port", type=int, default=8099)
    s.add_argument("--no-motion", action="store_true")
    s.set_defaults(func=cmd_serve)

    st = sub.add_parser("start", help="launch as a local app (auto-opens the UI)")
    st.add_argument("--port", type=int, default=8099)
    st.add_argument("--no-motion", action="store_true")
    st.add_argument("--no-window", action="store_true",
                    help="force the browser instead of a native window")
    st.set_defaults(func=cmd_start)

    d = sub.add_parser("discover", help="find ONVIF cameras on the LAN")
    d.add_argument("--timeout", type=float, default=3.0)
    d.set_defaults(func=cmd_discover)

    ad = sub.add_parser("add", help="add a camera to the store")
    ad.add_argument("--id", required=True)
    ad.add_argument("--name", default="")
    ad.add_argument("--loc", default="")
    ad.add_argument("--kind", default="rtsp",
                    choices=["simulated", "snapshot", "mjpeg", "rtsp", "webcam"])
    ad.add_argument("--url", default="")
    ad.add_argument("--user", default="")
    ad.add_argument("--password", default="")
    ad.set_defaults(func=cmd_add)

    sub.add_parser("list", help="list stored cameras").set_defaults(func=cmd_list)

    sn = sub.add_parser("snapshot", help="save one JPEG from a camera")
    sn.add_argument("id")
    sn.add_argument("--out", default="")
    sn.set_defaults(func=cmd_snapshot)

    sub.add_parser("selftest", help="verify install, no hardware").set_defaults(func=cmd_selftest)

    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
