"""Regression tests for the face bbox geometry in ``musetalk.utils.bbox_utils``.

This logic is buried inside ``preprocessing.get_landmark_and_bbox``, which cannot
be imported without a GPU and model weights (it initializes mmpose / face
detection at import time). The pure functions tested here are the extracted
source of truth that the preprocessing code calls.
"""

from musetalk.utils.bbox_utils import compute_upper_bound, is_valid_landmark_bbox


class TestComputeUpperBound:
    def test_normal_case_returns_symmetric_top(self):
        # half-face at y=100, chin at y=180 -> dist 80 -> top = 100 - 80 = 20
        assert compute_upper_bound(half_face_y=100, max_face_y=180) == 20

    def test_clamped_to_zero_when_would_go_negative(self):
        # This is the regression: half_face close to the top of a tall face makes
        # (half_face_y - half_face_dist) negative; it must clamp to 0, not go below.
        # half=30, chin=200 -> dist=170 -> raw = 30 - 170 = -140 -> clamped 0
        assert compute_upper_bound(half_face_y=30, max_face_y=200) == 0

    def test_never_returns_below_zero_for_a_range_of_inputs(self):
        for half_face_y in range(0, 300, 7):
            for max_face_y in range(half_face_y, half_face_y + 400, 11):
                assert compute_upper_bound(half_face_y, max_face_y) >= 0

    def test_exact_zero_boundary(self):
        # half=50, chin=100 -> dist=50 -> raw = 0 -> stays 0
        assert compute_upper_bound(50, 100) == 0

    def test_custom_min_upper_bound_is_respected(self):
        assert compute_upper_bound(30, 200, min_upper_bound=10) == 10
        assert compute_upper_bound(100, 180, min_upper_bound=10) == 20


class TestIsValidLandmarkBbox:
    def test_valid_bbox(self):
        assert is_valid_landmark_bbox((10, 20, 110, 220)) is True

    def test_zero_height_is_invalid(self):
        assert is_valid_landmark_bbox((10, 50, 110, 50)) is False

    def test_zero_width_is_invalid(self):
        assert is_valid_landmark_bbox((10, 20, 10, 220)) is False

    def test_negative_area_is_invalid(self):
        assert is_valid_landmark_bbox((10, 220, 110, 20)) is False

    def test_negative_left_edge_is_invalid(self):
        # positive area but x1 < 0 -> rejected (would index out of frame)
        assert is_valid_landmark_bbox((-5, 20, 110, 220)) is False

    def test_left_edge_at_zero_is_valid(self):
        assert is_valid_landmark_bbox((0, 20, 110, 220)) is True
