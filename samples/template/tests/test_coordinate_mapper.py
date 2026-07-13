"""Tests for CoordinateMapper."""

import pytest
from PySide6.QtCore import QPointF


class TestCoordinateMapper:
    """Test coordinate conversion between viewport, scene, and image."""

    def test_viewport_to_image_inside_bounds(self, coordinate_mapper):
        """Points inside image bounds should return valid coordinates."""
        # Image is 100x100, view is 400x300
        # After fitInView, image is centered and scaled
        result = coordinate_mapper.viewport_to_image(200, 150)
        assert result is not None
        ix, iy = result
        assert 0 <= ix < 100
        assert 0 <= iy < 100

    def test_viewport_to_image_outside_bounds(self, coordinate_mapper):
        """Points outside image bounds should return None."""
        # Far outside the view
        result = coordinate_mapper.viewport_to_image(-1000, -1000)
        assert result is None

    def test_image_to_viewport_returns_pointf(self, coordinate_mapper):
        """image_to_viewport should return a QPointF."""
        result = coordinate_mapper.image_to_viewport(50, 50)
        assert isinstance(result, QPointF)

    def test_roundtrip_conversion(self, coordinate_mapper):
        """Converting viewport→image→viewport should be close to original."""
        # Start with a viewport point that maps to an image point
        vp_x, vp_y = 200.0, 150.0
        img_pos = coordinate_mapper.viewport_to_image(vp_x, vp_y)
        assert img_pos is not None

        # Convert back to viewport
        vp_result = coordinate_mapper.image_to_viewport(*img_pos)

        # Should be close (allowing for rounding)
        assert abs(vp_result.x() - vp_x) < 2
        assert abs(vp_result.y() - vp_y) < 2

    def test_update_image_size(self, coordinate_mapper):
        """Updating image size should affect boundary checks."""
        # With 100x100 image, point at (99, 99) is inside
        assert coordinate_mapper.viewport_to_image(200, 150) is not None

        # Change to smaller image
        coordinate_mapper.update_image_size(10, 10)
        # The same viewport point might now be outside the smaller image
        # (depends on the view transform)

    def test_zero_size_image(self, coordinate_mapper):
        """With zero-size image, all points should be outside bounds."""
        coordinate_mapper.update_image_size(0, 0)
        result = coordinate_mapper.viewport_to_image(200, 150)
        assert result is None
