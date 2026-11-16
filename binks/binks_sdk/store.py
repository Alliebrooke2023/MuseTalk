# binks_sdk/store.py
"""Local JSON store for camera config + motion events. No database needed."""
from __future__ import annotations
import json
import os
import threading
import time

_DEFAULT = {
    "cameras": [
        {"id": "front-door", "name": "Front Door", "loc": "Porch", "kind": "simulated"},
        {"id": "backyard", "name": "Backyard", "loc": "Patio", "kind": "simulated"},
        {"id": "garage", "name": "Garage", "loc": "Driveway", "kind": "simulated"},
        {"id": "living-room", "name": "Living Room", "loc": "Indoor", "kind": "simulated"},
    ],
    "events": [],
}


class Store:
    def __init__(self, path: str):
        self.path = os.path.abspath(path)
        self._lock = threading.Lock()
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    d = json.load(f)
                d.setdefault("cameras", [])
                d.setdefault("events", [])
                return d
            except (OSError, ValueError):
                pass
        return json.loads(json.dumps(_DEFAULT))

    def save(self):
        with self._lock:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            os.replace(tmp, self.path)

    # cameras
    def cameras(self):
        return self.data["cameras"]

    def add_camera(self, cam: dict):
        cam.setdefault("id", cam.get("name", "cam").lower().replace(" ", "-"))
        self.data["cameras"] = [c for c in self.data["cameras"] if c["id"] != cam["id"]]
        self.data["cameras"].append(cam)
        self.save()
        return cam

    def remove_camera(self, cam_id: str):
        self.data["cameras"] = [c for c in self.data["cameras"] if c["id"] != cam_id]
        self.save()

    # events
    def add_event(self, cam_id: str, msg: str, extra: dict | None = None):
        ev = {"cam": cam_id, "msg": msg, "ts": time.time()}
        if extra:
            ev.update(extra)
        self.data["events"].insert(0, ev)
        self.data["events"] = self.data["events"][:200]
        self.save()
        return ev

    def events(self):
        return self.data["events"]
