# binks_sdk/motion.py
"""Frame-difference motion detector (Pillow + numpy, CPU only).

Feed it JPEG frames; it returns a motion score 0..1 by comparing each frame
to the previous one on a downscaled grayscale image. Above `threshold` it
reports an event. No ML model, no cloud — pure local pixel math.
"""
from __future__ import annotations
import io
import time


class MotionDetector:
    def __init__(self, threshold: float = 0.04, cooldown: float = 4.0, size: int = 64):
        self.threshold = threshold
        self.cooldown = cooldown
        self.size = size
        self._prev = None
        self._last_event = 0.0

    def _gray(self, jpeg: bytes):
        from PIL import Image
        import numpy as np
        im = Image.open(io.BytesIO(jpeg)).convert("L").resize((self.size, self.size))
        return np.asarray(im, dtype="float32") / 255.0

    def score(self, jpeg: bytes) -> float:
        import numpy as np
        cur = self._gray(jpeg)
        if self._prev is None:
            self._prev = cur
            return 0.0
        diff = float(np.mean(np.abs(cur - self._prev)))
        self._prev = cur
        return diff

    def check(self, jpeg: bytes) -> dict | None:
        """Return an event dict if motion crossed the threshold, else None."""
        s = self.score(jpeg)
        now = time.time()
        if s >= self.threshold and (now - self._last_event) >= self.cooldown:
            self._last_event = now
            return {"score": round(s, 4), "ts": now,
                    "level": "high" if s >= self.threshold * 2 else "normal"}
        return None
