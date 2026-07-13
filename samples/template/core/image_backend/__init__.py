"""Image backend abstraction layer.

Provides a backend-agnostic interface for image processing operations.
The default backend is OpenCV, but can be swapped via set_backend().

Usage:
    from core.image_backend import Image, get_backend

    backend = get_backend()
    img = backend.read_image("photo.jpg")
    print(img.width, img.height)
"""

from .image import Image
from .protocol import ImageBackend
from .factory import get_backend, set_backend

__all__ = ["Image", "ImageBackend", "get_backend", "set_backend"]
