"""ImageInfoSystem — provides pixel-level image information.

Registered as a subsystem of ImageDisplaySystem.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from core.image_data import CHANNEL_NAMES, ColorSpace
from core.logger import logger
from systems.base import ISystem
from systems.image_display.info.models import PixelInfo

if TYPE_CHECKING:
    from core.interfaces import IImageDisplayProvider


class ImageInfoSystem(ISystem):
    """System for querying pixel-level information from displayed images.

    Depends on IImageDisplayProvider for display state access.
    """

    def __init__(self, image_display: "IImageDisplayProvider"):
        self._image_display = image_display

    # ------------------------------------------------------------------
    # ISystem
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "ImageInfo"

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> None:
        pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_pixel_info(
        self,
        img: np.ndarray,
        x: int,
        y: int,
        color_space: str = "bgr",
    ) -> PixelInfo | None:
        """Get pixel information at the given image coordinates.

        Args:
            img: The numpy image array.
            x: X coordinate (column) in image pixels.
            y: Y coordinate (row) in image pixels.
            color_space: The color space of the image.

        Returns:
            PixelInfo if coordinates are valid, None otherwise.
        """
        if img is None:
            return None

        h, w = img.shape[:2]
        if not (0 <= x < w and 0 <= y < h):
            return None

        try:
            cs = ColorSpace(color_space)
        except ValueError:
            cs = ColorSpace.BGR

        # Extract channel values
        channel_names = CHANNEL_NAMES.get(cs, ("Ch0", "Ch1", "Ch2"))
        if cs == ColorSpace.GRAY or len(img.shape) == 2:
            val = img[y, x]
            if hasattr(val, "item"):
                val = val.item()
            channel_values = {channel_names[0]: int(val)}
        else:
            pixel = img[y, x]
            channel_values = {}
            for i, name in enumerate(channel_names):
                if i < len(pixel):
                    v = pixel[i]
                    if hasattr(v, "item"):
                        v = v.item()
                    # HSV hue is 0-179 in OpenCV, scale to 0-360 for display
                    if cs == ColorSpace.HSV and i == 0:
                        v = int(v * 2)
                    channel_values[name] = int(v) if isinstance(v, (int, float)) else int(v)

        return PixelInfo(
            x=x,
            y=y,
            channel_values=channel_values,
            color_space=color_space,
            image_width=w,
            image_height=h,
        )
