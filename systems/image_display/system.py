"""ImageDisplaySystem — owns image-to-display conversion and coordinate mapping.

UI layer depends on this system instead of importing cv2/numpy directly.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QSize
from PySide6.QtGui import QPixmap

from core.events import EventEmitter
from systems.base import ISystem
from systems.image_display.converter import compute_display_info, cv2_to_qpixmap
from systems.image_display.models import DisplayInfo


class ImageDisplaySystem(ISystem):
    """System that owns all image-to-Qt-display conversion logic.

    UI widgets use this system to:
    - Convert numpy arrays to QPixmap (without importing cv2)
    - Compute DisplayInfo for coordinate mapping (single source of truth)
    - Track which image is currently displayed
    """

    def __init__(self):
        self.on_display_changed = EventEmitter()
        self.on_image_selected = EventEmitter()
        self._current_display_info: DisplayInfo | None = None

    # ------------------------------------------------------------------
    # ISystem
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "ImageDisplay"

    def initialize(self) -> bool:
        return True

    def shutdown(self) -> None:
        self._current_display_info = None

    # ------------------------------------------------------------------
    # Public API — used by UI widgets
    # ------------------------------------------------------------------

    def convert_to_qpixmap(
        self, img: np.ndarray, max_size: QSize | None = None
    ) -> QPixmap:
        """Convert an OpenCV/numpy image to QPixmap for display.

        This is the ONLY place cv2 color conversion happens.
        UI widgets should never import cv2 directly.
        """
        return cv2_to_qpixmap(img, max_size)

    def compute_display_info(
        self,
        img: np.ndarray,
        max_width: int = 400,
        max_height: int = 280,
    ) -> DisplayInfo:
        """Compute the DisplayInfo for an image given display constraints.

        Returns the canonical DisplayInfo that all coordinate mapping
        should use. Stored as _current_display_info for ruler queries.
        """
        info = compute_display_info(img, max_width, max_height)
        self._current_display_info = info
        return info

    def get_current_display_info(self) -> DisplayInfo | None:
        """Return the most recently computed DisplayInfo.

        Used by RulerSystem to map screen coordinates to image pixels.
        """
        return self._current_display_info

    def map_to_image(
        self, display_x: float, display_y: float
    ) -> tuple[int, int] | None:
        """Map a display-pixmap coordinate to image pixel coordinates.

        Uses the current DisplayInfo. Returns None if no image is displayed
        or the coordinate is out of bounds.
        """
        if self._current_display_info is None:
            return None
        return self._current_display_info.map_to_image(display_x, display_y)
