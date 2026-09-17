"""Tests for the pure crop-box geometry in ``musetalk.utils.blending.get_crop_box``.

``blending`` imports PIL/numpy/cv2 but does no model initialization at import
time, so ``get_crop_box`` can be exercised directly.
"""

from musetalk.utils.blending import get_crop_box


class TestGetCropBox:
    def test_square_box_expand_one(self):
        # box 0..100 in both axes, center (50,50), half-size 50 * 1 = 50
        crop_box, s = get_crop_box([0, 0, 100, 100], expand=1.0)
        assert crop_box == [0, 0, 100, 100]
        assert s == 50

    def test_expand_grows_symmetrically(self):
        crop_box, s = get_crop_box([0, 0, 100, 100], expand=1.5)
        # max(w,h)//2 * 1.5 = 50 * 1.5 = 75
        assert s == 75
        assert crop_box == [50 - 75, 50 - 75, 50 + 75, 50 + 75]

    def test_uses_longer_side_for_square_crop(self):
        # wide box: w=200, h=100 -> uses w -> s = 200//2 = 100
        crop_box, s = get_crop_box([0, 0, 200, 100], expand=1.0)
        assert s == 100
        # center is (100, 50); crop is square around it
        assert crop_box == [0, -50, 200, 150]
        assert (crop_box[2] - crop_box[0]) == (crop_box[3] - crop_box[1])

    def test_crop_box_is_always_square(self):
        for box in ([0, 0, 40, 90], [10, 10, 210, 60], [5, 5, 25, 25]):
            for expand in (1.0, 1.2, 1.5, 2.0):
                crop_box, _ = get_crop_box(box, expand)
                w = crop_box[2] - crop_box[0]
                h = crop_box[3] - crop_box[1]
                assert w == h
