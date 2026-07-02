"""ImageData — value object encapsulating a numpy image array and color space.

UI code depends on this instead of raw np.ndarray so that image
metadata (width, height, channels, color space) is available without
numpy imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np


class ColorSpace(str, Enum):
    """Supported image color spaces."""

    BGR = "bgr"
    RGB = "rgb"
    HSV = "hsv"
    HLS = "hls"
    LAB = "lab"
    LUV = "luv"
    GRAY = "gray"
    XYZ = "xyz"
    YCrCb = "ycr_cb"


# Human-readable channel names for each color space.
CHANNEL_NAMES: dict[ColorSpace, tuple[str, ...]] = {
    ColorSpace.BGR: ("B", "G", "R"),
    ColorSpace.RGB: ("R", "G", "B"),
    ColorSpace.HSV: ("H", "S", "V"),
    ColorSpace.HLS: ("H", "L", "S"),
    ColorSpace.LAB: ("L", "A", "B"),
    ColorSpace.LUV: ("L", "U", "V"),
    ColorSpace.GRAY: ("Gray",),
    ColorSpace.XYZ: ("X", "Y", "Z"),
    ColorSpace.YCrCb: ("Y", "Cr", "Cb"),
}

# Value ranges for each channel in each color space (OpenCV conventions).
# Used by color filter nodes to validate and clamp channel ranges.
CHANNEL_RANGES: dict[ColorSpace, list[tuple[int, int]]] = {
    ColorSpace.BGR:   [(0, 255), (0, 255), (0, 255)],
    ColorSpace.RGB:   [(0, 255), (0, 255), (0, 255)],
    ColorSpace.HSV:   [(0, 179), (0, 255), (0, 255)],
    ColorSpace.HLS:   [(0, 179), (0, 255), (0, 255)],
    ColorSpace.LAB:   [(0, 100), (0, 255), (0, 255)],
    ColorSpace.LUV:   [(0, 100), (0, 255), (0, 255)],
    ColorSpace.XYZ:   [(0, 255), (0, 255), (0, 255)],
    ColorSpace.YCrCb: [(0, 255), (0, 255), (0, 255)],
    ColorSpace.GRAY:  [(0, 255)],
}

# Mapping from each color space to the cv2.COLOR_*2RGB conversion code.
# Used by the display converter to produce correct RGB for QPixmap.
COLORSPACE_TO_RGB: dict[ColorSpace, int | None] = {}

# Mapping from color space name to the cv2.COLOR_*2GRAY conversion code.
# Used by nodes that need to convert images to grayscale for processing.
_TO_GRAY: dict[str, int] = {}

# Mapping from color space name to the cv2.COLOR_*2BGR conversion code.
# Used as a fallback when no direct →GRAY conversion exists.
_TO_BGR: dict[str, int] = {}


def _init_color_conversions():
    """Populate color conversion lookup tables with cv2 constants (lazy import)."""
    try:
        import cv2
    except ImportError:
        return

    # →RGB
    _map = {
        ColorSpace.BGR: cv2.COLOR_BGR2RGB,
        ColorSpace.RGB: None,           # already RGB, no conversion needed
        ColorSpace.HSV: cv2.COLOR_HSV2RGB,
        ColorSpace.HLS: cv2.COLOR_HLS2RGB,
        ColorSpace.LAB: cv2.COLOR_LAB2RGB,
        ColorSpace.LUV: cv2.COLOR_LUV2RGB,
        ColorSpace.GRAY: None,          # grayscale path in converter
        ColorSpace.XYZ: cv2.COLOR_XYZ2RGB,
        ColorSpace.YCrCb: cv2.COLOR_YCrCb2RGB,
    }
    COLORSPACE_TO_RGB.update(_map)

    # →GRAY (direct)
    for _src in ["BGR", "RGB", "HSV", "HLS", "LAB", "LUV", "XYZ", "YCrCb"]:
        _code = getattr(cv2, f"COLOR_{_src}2GRAY", None)
        if _code is not None:
            _TO_GRAY[_src.lower()] = _code

    # →BGR (for fallback two-step conversion)
    for _src in ["HSV", "HLS", "LAB", "LUV", "XYZ", "YCrCb", "RGB", "GRAY"]:
        _code = getattr(cv2, f"COLOR_{_src}2BGR", None)
        if _code is not None:
            _TO_BGR[_src.lower()] = _code


def convert_to_gray(img: np.ndarray, src_color_space: str) -> np.ndarray:
    """Convert an image from *src_color_space* to grayscale.

    Uses direct ``cv2.COLOR_{src}2GRAY`` when available; otherwise
    falls back to a two-step ``{src} → BGR → GRAY`` conversion.
    If the source is already ``"gray"`` the image is returned as-is.
    """
    import cv2 as _cv2

    src = src_color_space.lower()
    if src == "gray":
        return img.copy() if img.ndim == 3 else img

    # Direct conversion
    code = _TO_GRAY.get(src)
    if code is not None:
        return _cv2.cvtColor(img, code)

    # Fallback: {src} → BGR → GRAY
    to_bgr = _TO_BGR.get(src)
    if to_bgr is not None:
        bgr = _cv2.cvtColor(img, to_bgr)
        return _cv2.cvtColor(bgr, _cv2.COLOR_BGR2GRAY)

    # Last resort: assume it's already BGR-compatible
    return _cv2.cvtColor(img, _cv2.COLOR_BGR2GRAY)


@dataclass(frozen=True)
class ImageData:
    """Immutable wrapper around a numpy image array with color space metadata.

    Provides width/height/channels without callers needing numpy.
    The underlying array is shared (not copied) for zero overhead.

    Attributes:
        array: The numpy image array.
        color_space: The color space of the image data (default "bgr").
    """

    array: np.ndarray = field(repr=False)
    color_space: str = "bgr"

    @property
    def width(self) -> int:
        return self.array.shape[1]

    @property
    def height(self) -> int:
        return self.array.shape[0]

    @property
    def channels(self) -> int:
        s = self.array.shape
        return s[2] if len(s) >= 3 else 1

    @property
    def is_grayscale(self) -> bool:
        return self.channels == 1 or self.color_space == ColorSpace.GRAY.value

    @property
    def shape(self) -> tuple[int, ...]:
        return self.array.shape
