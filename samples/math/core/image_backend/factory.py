"""Image backend factory — provides access to the active image processing backend.

Default backend is OpenCV (Cv2Backend). Can be swapped via configuration
or by calling set_backend().
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .protocol import ImageBackend

_backend: ImageBackend | None = None


def get_backend() -> ImageBackend:
    """Get the active image processing backend.

    Returns:
        The current ImageBackend instance (default: Cv2Backend).
    """
    global _backend
    if _backend is None:
        from .cv2_backend import Cv2Backend
        _backend = Cv2Backend()
    return _backend


def set_backend(backend: ImageBackend) -> None:
    """Set a custom image processing backend.

    Args:
        backend: The backend instance to use.
    """
    global _backend
    _backend = backend
