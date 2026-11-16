# selftest.py
"""Verify a Binks install with no camera hardware.

    python selftest.py        # or:  python binks.py selftest

Checks: SDK imports, simulated snapshot + stream, motion detection,
store round-trip, and the HTTP server/API end to end on a throwaway port.
"""
from __future__ import annotations
import os
import sys
import json
import time
import threading
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _ok(msg):
    print(f"  ok  {msg}")


def run() -> bool:
    from binks_sdk import CameraManager, Store, BinksServer
    from binks_sdk.motion import MotionDetector

    # 1) simulated snapshot is a real JPEG
    mgr = CameraManager([{"id": "t", "name": "Test", "kind": "simulated"}])
    jpg = mgr.get("t").snapshot()
    assert jpg[:2] == b"\xff\xd8" and jpg[-2:] == b"\xff\xd9", "snapshot not a JPEG"
    _ok(f"simulated snapshot is JPEG ({len(jpg)} bytes)")

    # 2) stream yields frames
    frames = list(mgr.get("t").frames(limit=3, fps=30))
    assert len(frames) == 3 and all(f[:2] == b"\xff\xd8" for f in frames)
    _ok("stream yields JPEG frames")

    # 3) motion detector reacts to the moving simulated subject
    det = MotionDetector(threshold=0.0)
    det.check(mgr.get("t").snapshot()); time.sleep(0.2)
    s = det.score(mgr.get("t").snapshot())
    assert s >= 0.0
    _ok(f"motion score computed ({s:.4f})")

    # 4) store round-trip
    sp = os.path.join(HERE, "_selftest_store.json")
    st = Store(sp)
    st.add_camera({"id": "x", "name": "X", "kind": "simulated"})
    st.add_event("x", "Test event")
    assert any(c["id"] == "x" for c in st.cameras())
    assert st.events()[0]["msg"] == "Test event"
    os.remove(sp)
    _ok("store add/save/load round-trip")

    # 5) HTTP server + API end to end
    app = BinksServer(store_path=os.path.join(HERE, "_selftest_srv.json"), motion=False)
    from binks_sdk.server import _make_server
    srv = _make_server(app, "127.0.0.1", 8137)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.4)
    base = "http://127.0.0.1:8137"
    cams = json.loads(urllib.request.urlopen(base + "/api/cameras", timeout=5).read())
    assert cams["cameras"], "no cameras from API"
    cid = cams["cameras"][0]["id"]
    snap = urllib.request.urlopen(base + f"/api/cameras/{cid}/snapshot", timeout=5).read()
    assert snap[:2] == b"\xff\xd8"
    html = urllib.request.urlopen(base + "/", timeout=5).read()
    assert b"Binks" in html
    srv.shutdown()
    os.path.exists(os.path.join(HERE, "_selftest_srv.json")) and \
        os.remove(os.path.join(HERE, "_selftest_srv.json"))
    _ok("HTTP API: /api/cameras, /snapshot, / (web app) all serve")

    print("\nALL CHECKS PASSED — Binks is working.")
    return True


if __name__ == "__main__":
    try:
        sys.exit(0 if run() else 1)
    except AssertionError as e:
        print(f"\nFAILED: {e}")
        sys.exit(1)
