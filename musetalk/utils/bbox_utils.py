"""Pure geometry helpers for face bounding-box computation.

These functions contain the arithmetic that decides the crop bbox used by
``get_landmark_and_bbox`` in ``preprocessing.py``. They are kept free of heavy
dependencies (no torch / mmpose / face_detection and no model initialization at
import time) so the logic can be unit-tested without a GPU or model weights.

The behaviour here is a literal transcription of the inline logic that used to
live in ``preprocessing.py``; keep the two in sync when either changes.
"""


def compute_upper_bound(half_face_y, max_face_y, min_upper_bound=0):
    """Return the (clamped) top y-coordinate of the crop box.

    Mirrors the landmark logic::

        half_face_dist = max_face_y - half_face_y
        upper_bound = max(min_upper_bound, half_face_y - half_face_dist)

    The clamp against ``min_upper_bound`` (default 0) prevents the crop box from
    extending above the top of the frame, which previously produced a negative
    coordinate and a broken crop (see the "ensure upper bond does not go below
    zero" fix).

    Args:
        half_face_y: y of the mid-face landmark (landmark 29, possibly shifted
            by ``bbox_shift``).
        max_face_y: largest y across the face landmarks (the chin).
        min_upper_bound: floor for the returned coordinate; defaults to 0.

    Returns:
        The upper (top) y-coordinate, never below ``min_upper_bound``.
    """
    half_face_dist = max_face_y - half_face_y
    return max(min_upper_bound, half_face_y - half_face_dist)


def is_valid_landmark_bbox(bbox):
    """Whether a landmark-derived bbox ``(x1, y1, x2, y2)`` is usable.

    Mirrors the check in ``get_landmark_and_bbox``: a bbox is rejected (and the
    detector bbox reused instead) when it has non-positive width or height, or a
    negative left edge::

        if y2 - y1 <= 0 or x2 - x1 <= 0 or x1 < 0:  # not suitable

    Returns:
        True when the bbox has positive area and a non-negative left edge.
    """
    x1, y1, x2, y2 = bbox
    return (y2 - y1) > 0 and (x2 - x1) > 0 and x1 >= 0
