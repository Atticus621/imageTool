"""ImageDisplaySystem — owns image-to-display conversion and coordinate mapping.

UI layer depends on this system instead of importing cv2/numpy directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from PySide6.QtCore import QSize
from PySide6.QtGui import QPixmap

from core.events import EventEmitter
from core.interfaces import IImageDisplayProvider
from core.system.auto_register import register_system
from systems.base import ISystem
from systems.image_display.converter import compute_display_info, cv2_to_qpixmap
from systems.image_display.models import DisplayInfo
from systems.image_display.info.system import ImageInfoSystem
from systems.image_display.ruler.system import RulerSystem

if TYPE_CHECKING:
    from systems.registry import SystemRegistry


@register_system(
    name="ImageDisplay",
    depends_on=[],
    auto_wire=False,  # 不需要绑定 graph
)
class ImageDisplaySystem(ISystem, IImageDisplayProvider):
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

    def register_subsystems(self, registry: SystemRegistry) -> None:
        """Register subsystems."""
        self._ruler = RulerSystem(self)
        registry.register(self._ruler, parent=self.name)

        self._info = ImageInfoSystem(self)
        registry.register(self._info, parent=self.name)

    # ------------------------------------------------------------------
    # Public API — used by UI widgets
    # ------------------------------------------------------------------

    def convert_to_qpixmap(
        self, img: np.ndarray, max_size: QSize | None = None,
        color_space: str = "bgr",
    ) -> QPixmap:
        """Convert an OpenCV/numpy image to QPixmap for display.

        This is the ONLY place cv2 color conversion happens.
        UI widgets should never import cv2 directly.

        Args:
            img: numpy array image.
            max_size: Optional max size for scaling.
            color_space: The color space of the input image (default "bgr").
        """
        return cv2_to_qpixmap(img, max_size, color_space=color_space)

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

    # ------------------------------------------------------------------
    # Subsystem access
    # ------------------------------------------------------------------

    @property
    def ruler(self) -> RulerSystem:
        """The ruler subsystem. Available after register_subsystems() is called."""
        if not hasattr(self, '_ruler'):
            raise RuntimeError(
                "RulerSystem not yet registered. "
                "register_subsystems() must be called first."
            )
        return self._ruler

    @property
    def info(self) -> ImageInfoSystem:
        """The image info subsystem. Available after register_subsystems() is called."""
        if not hasattr(self, '_info'):
            raise RuntimeError(
                "ImageInfoSystem not yet registered. "
                "register_subsystems() must be called first."
            )
        return self._info
