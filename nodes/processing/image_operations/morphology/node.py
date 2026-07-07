"""Morphology operations node — erosion, dilation, opening, closing, and more."""

from __future__ import annotations

import cv2
import numpy as np

from core.image_data import ImageData, ColorSpace, convert_to_gray
from core.logger import logger
from core.node_base.node import NodeBase, NodeState


class MorphologyNode(NodeBase):
    """Performs morphological operations on images.

    Supports 7 standard morphological operations with configurable
    kernel shape, size, and iteration count. Handles both grayscale
    and multi-channel images.
    """

    # ── Node metadata (no meta.json needed) ─────────────────────────
    NODE_ID = "processing/image_operations/morphology"
    NODE_NAME = "形态学操作"
    NODE_CATEGORY = "图像运算"
    NODE_DESCRIPTION = "对图像进行形态学操作：腐蚀、膨胀、开运算、闭运算、形态学梯度、顶帽、黑帽"
    NODE_INPUTS = [
        {"name": "images", "type": "image", "label": "图像输入"},
    ]
    NODE_OUTPUTS = [
        {"name": "images", "type": "image", "label": "图像输出"},
    ]
    NODE_OPTIONAL_PORTS = [
        {"name": "roi", "label": "ROI 输入", "port_type": "roi", "direction": "input", "default": False, "group": "input"},
    ]
    NODE_PARAMS = [
        {
            "name": "operation", "type": "combo", "label": "操作类型", "default": "open",
            "options": [
                {"value": "erode",     "label": "腐蚀 (Erosion)"},
                {"value": "dilate",    "label": "膨胀 (Dilation)"},
                {"value": "open",      "label": "开运算 (Opening)"},
                {"value": "close",     "label": "闭运算 (Closing)"},
                {"value": "gradient",  "label": "形态学梯度 (Gradient)"},
                {"value": "top_hat",   "label": "顶帽 (Top Hat)"},
                {"value": "black_hat", "label": "黑帽 (Black Hat)"},
            ],
        },
        {
            "name": "kernel_shape", "type": "combo", "label": "结构元素形状",
            "default": "rect",
            "options": [
                {"value": "rect",   "label": "矩形 (Rect)"},
                {"value": "ellipse", "label": "椭圆 (Ellipse)"},
                {"value": "cross",  "label": "十字形 (Cross)"},
            ],
        },
        {
            "name": "kernel_size", "type": "int_slider", "label": "核大小",
            "default": 3, "min": 3, "max": 31, "step": 2,
        },
        {
            "name": "iterations", "type": "int_slider", "label": "迭代次数",
            "default": 1, "min": 1, "max": 10, "step": 1,
        },
        {
            "name": "color_mode", "type": "combo", "label": "彩色处理方式",
            "default": "per_channel",
            "options": [
                {"value": "per_channel", "label": "逐通道处理 (保留颜色)"},
                {"value": "grayscale",  "label": "先转灰度再处理"},
            ],
        },
    ]

    # Map kernel shape names → cv2.MORPH_* constants
    _KERNEL_SHAPES = {
        "rect":    cv2.MORPH_RECT,
        "ellipse": cv2.MORPH_ELLIPSE,
        "cross":   cv2.MORPH_CROSS,
    }

    # Map operation names → cv2.MORPH_* constants (for morphologyEx)
    _MORPH_OPS = {
        "open":      cv2.MORPH_OPEN,
        "close":     cv2.MORPH_CLOSE,
        "gradient":  cv2.MORPH_GRADIENT,
        "top_hat":   cv2.MORPH_TOPHAT,
        "black_hat": cv2.MORPH_BLACKHAT,
    }

    def execute(self) -> bool:
        operation = self.params.get("operation", "open")
        kernel_shape = self.params.get("kernel_shape", "rect")
        kernel_size = int(self.params.get("kernel_size", 3))
        iterations = int(self.params.get("iterations", 1))
        color_mode = self.params.get("color_mode", "per_channel")

        # Get input images
        items = self._get_input_images_raw("images")
        if not items:
            logger.warning(f"[{self.meta.name}] No input images")
            self.set_state(NodeState.ERROR)
            return False

        # Build structuring element
        shape = self._KERNEL_SHAPES.get(kernel_shape, cv2.MORPH_RECT)
        kernel = cv2.getStructuringElement(shape, (kernel_size, kernel_size))

        rois = self._get_input_rois("roi")
        roi_mgr = None
        if rois:
            from core.roi import ROIManager
            roi_mgr = ROIManager.instance()

        results: list[ImageData] = []

        for item in items:
            if isinstance(item, ImageData):
                img = item.array
                color_space = item.color_space
            elif isinstance(item, np.ndarray):
                img = item
                color_space = ColorSpace.BGR.value  # assume BGR for raw arrays
            else:
                logger.warning(f"[{self.meta.name}] Unexpected input type: {type(item)}")
                continue

            processed = self._apply_morphology(img, operation, kernel, iterations, color_mode, color_space)

            # Apply ROI constraint if connected
            if roi_mgr and rois:
                processed = roi_mgr.apply_constraint(img, processed, rois)

            # When converting to grayscale, the output color space becomes GRAY
            out_space = ColorSpace.GRAY.value if color_mode == "grayscale" and not _is_grayscale(img) else color_space
            results.append(ImageData(array=processed, color_space=out_space))

        if not results:
            logger.error(f"[{self.meta.name}] No valid images processed")
            self.set_state(NodeState.ERROR)
            return False

        self._set_output_images("images", results)

        logger.info(
            f"[{self.meta.name}] {operation} (kernel={kernel_size}x{kernel_size}, "
            f"shape={kernel_shape}, iter={iterations}) on {len(results)} image(s)"
        )
        self.set_state(NodeState.SUCCESS)
        return True

    # ── Internal helpers ─────────────────────────────────────────────

    def _apply_morphology(
        self,
        img: np.ndarray,
        operation: str,
        kernel: np.ndarray,
        iterations: int,
        color_mode: str = "per_channel",
        color_space: str = "bgr",
    ) -> np.ndarray:
        """Apply the morphological operation to a single image.

        Args:
            img: Input image array.
            operation: Morphology operation name.
            kernel: Structuring element.
            iterations: Number of iterations.
            color_mode: ``"per_channel"`` to process each channel independently,
                        ``"grayscale"`` to convert to gray first.
            color_space: Source color space (e.g. ``"bgr"``, ``"lab"``, ``"hsv"``).
                         Used for correct grayscale conversion.
        """
        if _is_grayscale(img) or color_mode == "grayscale":
            gray = img if _is_grayscale(img) else convert_to_gray(img, color_space)
            return self._apply_op(gray, operation, kernel, iterations)

        # Per-channel mode: process each channel independently
        channels = cv2.split(img)
        processed = [
            self._apply_op(ch, operation, kernel, iterations)
            for ch in channels
        ]
        return cv2.merge(processed)

    @staticmethod
    def _apply_op(
        img: np.ndarray,
        operation: str,
        kernel: np.ndarray,
        iterations: int,
    ) -> np.ndarray:
        """Apply a single morphological operation to a 2D array."""
        if operation == "erode":
            return cv2.erode(img, kernel, iterations=iterations)
        elif operation == "dilate":
            return cv2.dilate(img, kernel, iterations=iterations)
        else:
            morph_type = MorphologyNode._MORPH_OPS.get(operation)
            if morph_type is None:
                raise ValueError(f"Unknown morphology operation: {operation}")
            return cv2.morphologyEx(img, morph_type, kernel, iterations=iterations)


def _is_grayscale(img: np.ndarray) -> bool:
    """Return True if the image is 2D or single-channel."""
    return img.ndim == 2 or (img.ndim == 3 and img.shape[2] == 1)
