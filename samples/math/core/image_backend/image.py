"""Image wrapper — backend-agnostic image container.

Wraps backend-specific data (e.g. numpy ndarray from OpenCV) with
metadata and convenience properties. The wrapper is thin — it stores
the raw data and a reference to the backend, delegating actual
operations to the backend.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .protocol import ImageBackend


@dataclass
class Image:
    """Backend-agnostic image container.

    Attributes:
        data: Backend-specific image data (e.g. np.ndarray for OpenCV).
        backend: The backend that created/will process this image.
        color_space: Color space identifier (e.g. "bgr", "rgb", "gray").
    """

    data: Any = field(repr=False)
    backend: Any = field(repr=False, default=None)  # ImageBackend instance
    color_space: str = "bgr"

    # ── Convenience properties ───────────────────────────────────────

    @property
    def width(self) -> int:
        """Image width in pixels."""
        if self.backend is not None:
            return self.backend.get_width(self.data)
        # Fallback: try shape access (works for numpy arrays)
        return self.data.shape[1] if len(self.data.shape) >= 2 else 0

    @property
    def height(self) -> int:
        """Image height in pixels."""
        if self.backend is not None:
            return self.backend.get_height(self.data)
        return self.data.shape[0] if len(self.data.shape) >= 1 else 0

    @property
    def channels(self) -> int:
        """Number of color channels."""
        if self.backend is not None:
            return self.backend.get_channels(self.data)
        return self.data.shape[2] if len(self.data.shape) >= 3 else 1

    @property
    def shape(self) -> tuple[int, ...]:
        """Image shape tuple (height, width[, channels])."""
        if self.backend is not None:
            return self.backend.get_shape(self.data)
        return self.data.shape

    @property
    def is_grayscale(self) -> bool:
        """True if image is single-channel or tagged as grayscale."""
        return self.channels == 1 or self.color_space == "gray"

    # ── Data access ──────────────────────────────────────────────────

    def to_backend_data(self) -> Any:
        """Return the raw backend-specific data.

        Used by nodes that need direct access to the underlying library
        (e.g. OpenCV functions on numpy arrays).
        """
        return self.data

    # ── Copy ─────────────────────────────────────────────────────────

    def copy(self) -> Image:
        """Create a shallow copy of this image (data is shared, not copied)."""
        return Image(
            data=self.data,
            backend=self.backend,
            color_space=self.color_space,
        )
