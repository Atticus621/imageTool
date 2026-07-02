"""Image-to-Qt conversion functions.

Centralizes all cv2/numpy -> QPixmap conversion logic in one place.
UI code depends on ImageDisplaySystem, not on cv2 directly.
"""

from __future__ import annotations

import cv2
import numpy as np
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QImage, QPixmap

from core.image_data import COLORSPACE_TO_RGB, ColorSpace, _init_color_conversions
from systems.image_display.models import DisplayInfo

# Eagerly populate cv2 constants so COLORSPACE_TO_RGB is ready at import time.
_init_color_conversions()


def cv2_to_qpixmap(
    img: np.ndarray, max_size: QSize | None = None, color_space: str = "bgr"
) -> QPixmap:
    """Convert a numpy image to a QPixmap for display.

    Args:
        img: numpy array (any color space or grayscale).
        max_size: If provided, scale the pixmap to fit within this size
                  while preserving aspect ratio.
        color_space: The color space of the input image (default "bgr").
                     Used to determine how to convert to RGB for QPixmap.

    Returns:
        QPixmap ready for display in a QLabel or similar widget.
    """
    if img is None:
        return QPixmap()

    cs = ColorSpace(color_space)

    # Grayscale path
    if len(img.shape) == 2 or cs == ColorSpace.GRAY:
        if len(img.shape) == 3 and cs == ColorSpace.GRAY:
            # 3-channel image tagged as GRAY — use first channel
            gray = img[:, :, 0] if img.shape[2] >= 1 else img
            h, w = gray.shape
            qimg = QImage(gray.data, w, h, w, QImage.Format.Format_Grayscale8)
        elif len(img.shape) == 2:
            h, w = img.shape
            qimg = QImage(img.data, w, h, w, QImage.Format.Format_Grayscale8)
        else:
            h, w = img.shape[:2]
            qimg = QImage(img.data, w, h, w, QImage.Format.Format_Grayscale8)
    elif cs == ColorSpace.RGB:
        # Already RGB — use directly
        h, w, ch = img.shape
        bytes_per_line = ch * w
        qimg = QImage(img.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
    else:
        # Convert from source color space to RGB for display
        code = COLORSPACE_TO_RGB.get(cs)
        if code is not None:
            img_rgb = cv2.cvtColor(img, code)
        else:
            # Unknown conversion — assume already displayable
            img_rgb = img
        h, w, ch = img_rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

    pixmap = QPixmap.fromImage(qimg)
    if max_size:
        pixmap = pixmap.scaled(
            max_size, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
    return pixmap


def compute_display_info(
    img: np.ndarray,
    max_width: int = 400,
    max_height: int = 280,
) -> DisplayInfo:
    """Compute DisplayInfo for an image given display constraints.

    This is the single function that determines how an image will be
    displayed. It replaces the scattered size computation previously
    in ImageSetWidget._select_image() and ImageViewerWidget.map_to_image().

    Args:
        img: The source image (numpy array).
        max_width: Maximum display width in logical pixels.
        max_height: Maximum display height in logical pixels.

    Returns:
        DisplayInfo with actual and display dimensions and computed offsets.
    """
    if len(img.shape) == 2:
        actual_h, actual_w = img.shape
    else:
        actual_h, actual_w, _ = img.shape

    # Compute display size preserving aspect ratio
    scale = min(max_width / actual_w, max_height / actual_h)
    display_w = int(actual_w * scale)
    display_h = int(actual_h * scale)

    return DisplayInfo(
        actual_w=actual_w,
        actual_h=actual_h,
        display_w=display_w,
        display_h=display_h,
    )
