"""ImageBackend protocol — abstract interface for image processing operations.

Defines the contract that image processing backends must implement.
The default backend is OpenCV, but other backends (PIL, etc.) can be swapped in.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .image import Image


class ImageBackend(ABC):
    """Abstract image processing backend interface.

    All image operations go through this interface so that the core
    infrastructure and systems layer can remain decoupled from concrete
    libraries like OpenCV.
    """

    # ── I/O ──────────────────────────────────────────────────────────

    @abstractmethod
    def read_image(self, path: str) -> Image | None:
        """Read an image from file path.

        Returns:
            Image object, or None on failure.
        """
        ...

    @abstractmethod
    def write_image(self, path: str, image: Image) -> bool:
        """Write an image to file path.

        Returns:
            True on success, False on failure.
        """
        ...

    # ── Geometry ─────────────────────────────────────────────────────

    @abstractmethod
    def resize(self, image: Image, width: int, height: int) -> Image:
        """Resize image to given dimensions."""
        ...

    @abstractmethod
    def crop(self, image: Image, x: int, y: int, w: int, h: int) -> Image:
        """Crop image to bounding box (x, y, width, height)."""
        ...

    # ── Color space ──────────────────────────────────────────────────

    @abstractmethod
    def convert_color_space(self, image: Image, src_space: str, dst_space: str) -> Image:
        """Convert image between color spaces."""
        ...

    @abstractmethod
    def to_grayscale(self, image: Image) -> Image:
        """Convert image to grayscale."""
        ...

    # ── Mask operations ──────────────────────────────────────────────

    @abstractmethod
    def create_mask(self, image: Image, width: int, height: int, fill: int = 0) -> Image:
        """Create a new mask image filled with a value."""
        ...

    @abstractmethod
    def apply_mask(self, image: Image, mask: Image, fill: int = 0) -> Image:
        """Apply a binary mask to an image, filling outside regions."""
        ...

    @abstractmethod
    def combine_masks(self, masks: list[Image], mode: str = "union") -> Image:
        """Combine multiple binary masks.

        Args:
            masks: List of binary mask images.
            mode: "union", "intersection", or "difference".
        """
        ...

    # ── Properties ───────────────────────────────────────────────────

    @abstractmethod
    def get_width(self, data: Any) -> int:
        """Get image width from backend-specific data."""
        ...

    @abstractmethod
    def get_height(self, data: Any) -> int:
        """Get image height from backend-specific data."""
        ...

    @abstractmethod
    def get_channels(self, data: Any) -> int:
        """Get image channel count from backend-specific data."""
        ...

    @abstractmethod
    def get_shape(self, data: Any) -> tuple[int, ...]:
        """Get image shape tuple from backend-specific data."""
        ...
