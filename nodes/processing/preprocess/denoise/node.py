"""Denoise node — Gaussian blur, median filter, bilateral filter."""

from __future__ import annotations

import cv2
import numpy as np

from core.image_data import ImageData, ColorSpace
from core.logger import logger
from core.node_base.node import NodeBase, NodeState


class DenoiseNode(NodeBase):
    """Reduces image noise using various filtering methods."""

    NODE_ID = "processing/preprocess/denoise"
    NODE_NAME = "降噪"
    NODE_DESCRIPTION = "图像降噪：高斯模糊、中值滤波、双边滤波"
    NODE_INPUTS = [
        {"name": "images", "type": "image", "label": "图像输入"},
    ]
    NODE_OUTPUTS = [
        {"name": "images", "type": "image", "label": "图像输出"},
    ]

    def execute(self) -> bool:
        method = self.params.get("method", "gaussian")
        kernel_size = int(self.params.get("kernel_size", 5))
        sigma_color = int(self.params.get("sigma_color", 75))
        sigma_space = int(self.params.get("sigma_space", 75))

        items = self._get_input_images_raw("images")
        if not items:
            logger.warning(f"[{self.meta.name}] No input images")
            self.set_state(NodeState.ERROR)
            return False

        # Ensure kernel_size is odd
        if kernel_size % 2 == 0:
            kernel_size += 1

        results = []
        for item in items:
            if isinstance(item, ImageData):
                img = item.array
                color_space = item.color_space
            else:
                img = item
                color_space = "bgr"

            processed = self._apply_denoise(img, method, kernel_size, sigma_color, sigma_space)
            results.append(ImageData(array=processed, color_space=color_space))

        self._set_output_images("images", results)
        logger.info(f"[{self.meta.name}] {method} (k={kernel_size}) on {len(results)} image(s)")
        self.set_state(NodeState.SUCCESS)
        return True

    def _apply_denoise(self, img, method, kernel_size, sigma_color, sigma_space):
        if method == "median":
            return cv2.medianBlur(img, kernel_size)
        elif method == "bilateral":
            return cv2.bilateralFilter(img, kernel_size, sigma_color, sigma_space)
        else:  # gaussian
            return cv2.GaussianBlur(img, (kernel_size, kernel_size), 0)
