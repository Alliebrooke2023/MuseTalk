"""Synthetic eye-blink generation for single-photo-driven inference.

MuseTalk only regenerates the lower-face/mouth region and always copies the
eyes straight from the source frame(s) (see `musetalk/utils/blending.py`).
That's fine when the source is a video, since the video already contains
natural eye motion. When the source is a single still photo there is only
one frame, so without this module the eyes stay frozen open for the entire
output. This module detects the eye landmarks on the source photo, builds a
natural, randomly-timed blink cadence for the requested number of output
frames, and warps the eyelid region closed frame-by-frame to match it.
"""

import numpy as np
import cv2
from mmpose.apis import inference_topdown
from mmpose.structures import merge_data_samples

from musetalk.utils.preprocessing import model as _landmark_model

# ibug/dlib-style 68-point facial landmark indices for each eye.
RIGHT_EYE_IDX = list(range(36, 42))
LEFT_EYE_IDX = list(range(42, 48))


def get_face_landmarks(frame):
    """Return the 68 ibug-style facial landmarks for a single BGR frame, or None if no face is found."""
    results = inference_topdown(_landmark_model, frame)
    results = merge_data_samples(results)
    keypoints = results.pred_instances.keypoints
    if keypoints is None or len(keypoints) == 0:
        return None
    return keypoints[0][23:91].astype(np.float32)


def generate_blink_schedule(
    num_frames,
    fps,
    min_interval_sec=2.0,
    max_interval_sec=5.0,
    blink_duration_sec=0.15,
    seed=None,
):
    """Per-frame eyelid closure ratio (0=open, 1=fully closed).

    Blinks occur at randomized intervals within [min_interval_sec, max_interval_sec],
    each shaped as a smooth close-then-open ease over blink_duration_sec.
    """
    fps = max(float(fps), 1.0)
    closure = np.zeros(num_frames, dtype=np.float32)
    duration_frames = max(2, int(round(blink_duration_sec * fps)))
    rng = np.random.default_rng(seed)

    t = int(rng.uniform(0.5, max_interval_sec) * fps)
    while t < num_frames:
        for i in range(duration_frames):
            idx = t + i
            if idx >= num_frames:
                break
            phase = i / (duration_frames - 1)
            closure[idx] = np.sin(phase * np.pi)
        t += duration_frames + int(round(rng.uniform(min_interval_sec, max_interval_sec) * fps))
    return closure


def _feathered_ellipse_mask(w, h):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    ry, rx = max(cy, 1.0), max(cx, 1.0)
    dist = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
    mask = np.clip(1.5 - 1.5 * dist, 0.0, 1.0)
    return mask[..., None]


def _close_eye_region(frame, eye_pts, closure_ratio, vertical_margin=0.9, horizontal_margin=0.35):
    """Vertically squeeze the eye ROI toward its center to simulate the eyelid closing."""
    if closure_ratio <= 1e-3:
        return frame
    h_img, w_img = frame.shape[:2]
    x0, y0 = eye_pts.min(axis=0)
    x1, y1 = eye_pts.max(axis=0)
    ew, eh = x1 - x0, y1 - y0
    if ew <= 0 or eh <= 0:
        return frame

    x0 = int(max(0, x0 - ew * horizontal_margin))
    x1 = int(min(w_img, x1 + ew * horizontal_margin))
    y0 = int(max(0, y0 - eh * vertical_margin))
    y1 = int(min(h_img, y1 + eh * vertical_margin))
    if x1 - x0 < 2 or y1 - y0 < 2:
        return frame

    roi = frame[y0:y1, x0:x1]
    h, w = roi.shape[:2]
    new_h = max(1, int(round(h * (1 - closure_ratio * 0.92))))
    squeezed = cv2.resize(roi, (w, new_h), interpolation=cv2.INTER_LINEAR)

    top_pad = (h - new_h) // 2
    bottom_pad = h - new_h - top_pad
    canvas = np.empty_like(roi)
    if top_pad > 0:
        canvas[:top_pad] = squeezed[0:1]
    canvas[top_pad:top_pad + new_h] = squeezed
    if bottom_pad > 0:
        canvas[top_pad + new_h:] = squeezed[-1:]

    mask = _feathered_ellipse_mask(w, h) * closure_ratio
    blended = (canvas.astype(np.float32) * mask + roi.astype(np.float32) * (1 - mask)).astype(np.uint8)

    out = frame.copy()
    out[y0:y1, x0:x1] = blended
    return out


def apply_blink(frame, landmarks, closure_ratio):
    """Return a copy of frame with both eyes warped toward closed by closure_ratio (0..1)."""
    if landmarks is None or closure_ratio <= 1e-3:
        return frame
    out = _close_eye_region(frame, landmarks[RIGHT_EYE_IDX], closure_ratio)
    out = _close_eye_region(out, landmarks[LEFT_EYE_IDX], closure_ratio)
    return out
