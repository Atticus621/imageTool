"""Cv2Backend — OpenCV-based image processing backend.

Implements the ImageBackend protocol using OpenCV (cv2) and numpy.
This is the default backend for the imageTools project.
"""

from __future__ import annotations

import numpy as np
from typing import Any

from .protocol import ImageBackend
from .image import Image


class Cv2Backend(ImageBackend):
    """OpenCV implementation of the ImageBackend protocol.

    All methods delegate to cv2 functions. The raw data type is np.ndarray.
    """

    # ── I/O ──────────────────────────────────────────────────────────

    def read_image(self, path: str) -> Image | None:
        import cv2
        try:
            data = np.fromfile(path, dtype=np.uint8)
            img = cv2.imdecode(data, cv2.IMREAD_COLOR)
            if img is None:
                return None
            return Image(data=img, backend=self, color_space="bgr")
        except Exception:
            return None

    def write_image(self, path: str, image: Image) -> bool:
        import cv2
        try:
            ext = path.rsplit(".", 1)[-1] if "." in path else "png"
            ok, encoded = cv2.imencode(f".{ext}", image.to_backend_data())
            if ok:
                encoded.tofile(path)
                return True
            return False
        except Exception:
            return False

    # ── Geometry ─────────────────────────────────────────────────────

    def resize(self, image: Image, width: int, height: int) -> Image:
        import cv2
        data = image.to_backend_data()
        resized = cv2.resize(data, (width, height))
        return Image(data=resized, backend=self, color_space=image.color_space)

    def crop(self, image: Image, x: int, y: int, w: int, h: int) -> Image:
        data = image.to_backend_data()
        cropped = data[y : y + h, x : x + w]
        return Image(data=cropped, backend=self, color_space=image.color_space)

    # ── Color space ──────────────────────────────────────────────────

    def convert_color_space(self, image: Image, src_space: str, dst_space: str) -> Image:
        import cv2
        from core.image_data import COLORSPACE_TO_RGB, _TO_GRAY, _TO_BGR

        if src_space == dst_space:
            return image.copy()

        data = image.to_backend_data()
        src = src_space.lower()
        dst = dst_space.lower()

        # Direct conversion via lookup tables
        if dst == "gray":
            code = _TO_GRAY.get(src)
            if code is not None:
                result = cv2.cvtColor(data, code)
                return Image(data=result, backend=self, color_space="gray")

        if src == "gray" and dst in ("bgr", "rgb"):
            # Grayscale → BGR
            code = _TO_BGR.get("gray")
            if code is not None:
                result = cv2.cvtColor(data, code)
                return Image(data=result, backend=self, color_space="bgr")

        # General: try direct cv2.COLOR_{src}2{dst}
        param_to_cv2 = {
            "bgr": "BGR", "rgb": "RGB", "hsv": "HSV", "hls": "HLS",
            "lab": "LAB", "luv": "LUV", "gray": "GRAY", "xyz": "XYZ",
            "ycr_cb": "YCrCb",
        }
        src_cv2 = param_to_cv2.get(src, src.upper())
        dst_cv2 = param_to_cv2.get(dst, dst.upper())
        code_name = f"COLOR_{src_cv2}2{dst_cv2}"
        code = getattr(cv2, code_name, None)
        if code is not None:
            result = cv2.cvtColor(data, code)
            return Image(data=result, backend=self, color_space=dst)

        # Fallback: two-step via BGR
        code1 = _TO_BGR.get(src)
        code2_name = f"COLOR_BGR2{dst_cv2}"
        code2 = getattr(cv2, code2_name, None)
        if code1 is not None and code2 is not None:
            bgr = cv2.cvtColor(data, code1)
            result = cv2.cvtColor(bgr, code2)
            return Image(data=result, backend=self, color_space=dst)

        # Unknown conversion — return copy
        return image.copy()

    def to_grayscale(self, image: Image) -> Image:
        import cv2
        data = image.to_backend_data()
        if len(data.shape) == 2:
            return image.copy()
        gray = cv2.cvtColor(data, cv2.COLOR_BGR2GRAY)
        return Image(data=gray, backend=self, color_space="gray")

    # ── Mask operations ──────────────────────────────────────────────

    def create_mask(self, image: Image, width: int, height: int, fill: int = 0) -> Image:
        mask = np.full((height, width), fill, dtype=bool)
        return Image(data=mask, backend=self, color_space="mask")

    def apply_mask(self, image: Image, mask: Image, fill: int = 0) -> Image:
        data = image.to_backend_data()
        mask_data = mask.to_backend_data()
        result = data.copy()
        if data.ndim == 3 and mask_data.ndim == 2:
            mask_3ch = np.stack([mask_data] * data.shape[2], axis=-1)
        else:
            mask_3ch = mask_data
        result[~mask_3ch] = fill
        return Image(data=result, backend=self, color_space=image.color_space)

    def combine_masks(self, masks: list[Image], mode: str = "union") -> Image:
        if not masks:
            raise ValueError("No masks to combine")

        mask_arrays = [m.to_backend_data() for m in masks]
        result = mask_arrays[0]

        if mode == "union":
            for m in mask_arrays[1:]:
                result = result | m
        elif mode == "intersection":
            for m in mask_arrays[1:]:
                result = result & m
        elif mode == "difference":
            for m in mask_arrays[1:]:
                result = result & ~m
        else:
            raise ValueError(f"Unsupported combine mode: {mode}")

        return Image(data=result, backend=self, color_space="mask")

    # ── Properties ───────────────────────────────────────────────────

    def get_width(self, data: Any) -> int:
        return data.shape[1] if len(data.shape) >= 2 else 0

    def get_height(self, data: Any) -> int:
        return data.shape[0] if len(data.shape) >= 1 else 0

    def get_channels(self, data: Any) -> int:
        return data.shape[2] if len(data.shape) >= 3 else 1

    def get_shape(self, data: Any) -> tuple[int, ...]:
        return data.shape
