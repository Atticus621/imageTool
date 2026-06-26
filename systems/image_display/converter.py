"""Image-to-Qt conversion functions.

Centralizes all cv2/numpy -> QPixmap conversion logic in one place.
UI code depends on ImageDisplaySystem, not on cv2 directly.
"""

from __future__ import annotations

import cv2
import numpy as np
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QImage, QPixmap

from systems.image_display.models import DisplayInfo


def cv2_to_qpixmap(img: np.ndarray, max_size: QSize | None = None) -> QPixmap:
    """Convert an OpenCV image (BGR or grayscale) to a QPixmap.

    Args:
        img: numpy array from cv2 (BGR color or grayscale).
        max_size: If provided, scale the pixmap to fit within this size
                  while preserving aspect ratio.

    Returns:
        QPixmap ready for display in a QLabel or similar widget.
    """
    if img is None:
        return QPixmap()

    if len(img.shape) == 2:
        h, w = img.shape
        qimg = QImage(img.data, w, h, w, QImage.Format.Format_Grayscale8)
    else:
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, ch = img_rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

    pixmap = QPixmap.fromImage(qimg)
    if max_size:
        pixmap = pixmap.scaled(
            max_size, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
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
