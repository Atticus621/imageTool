"""Binarize node — threshold, adaptive threshold, Otsu."""

from __future__ import annotations

import cv2
import numpy as np

from core.image_data import ImageData, ColorSpace, convert_to_gray
from core.logger import logger
from core.node_base.node import NodeBase, NodeState


class BinarizeNode(NodeBase):
    """Converts images to binary (black/white) using various thresholding methods."""

    NODE_ID = "processing/preprocess/binarize"
    NODE_NAME = "二值化"
    NODE_CATEGORY = "图像预处理"
    NODE_DESCRIPTION = "图像二值化：固定阈值、自适应阈值、Otsu自动阈值"
    NODE_INPUTS = [
        {"name": "images", "type": "image", "label": "图像输入"},
    ]
    NODE_OUTPUTS = [
        {"name": "images", "type": "image", "label": "二值图像"},
        {"name": "mask", "type": "image", "label": "掩码输出"},
    ]

    def execute(self) -> bool:
        method = self.params.get("method", "otsu")
        threshold_value = int(self.params.get("threshold_value", 128))
        block_size = int(self.params.get("block_size", 11))
        c_value = int(self.params.get("c_value", 2))

        items = self._get_input_images_raw("images")
        if not items:
            logger.warning(f"[{self.meta.name}] No input images")
            self.set_state(NodeState.ERROR)
            return False

        # Ensure block_size is odd
        if block_size % 2 == 0:
            block_size += 1

        results = []
        masks = []
        for item in items:
            if isinstance(item, ImageData):
                img = item.array
                color_space = item.color_space
            else:
                img = item
                color_space = "bgr"

            gray = convert_to_gray(img, color_space)
            binary, mask = self._apply_binarize(gray, method, threshold_value, block_size, c_value)

            results.append(ImageData(array=binary, color_space=ColorSpace.GRAY.value))
            masks.append(ImageData(array=mask, color_space=ColorSpace.GRAY.value))

        self._set_output_images("images", results)
        self._set_output_images("mask", masks)
        logger.info(f"[{self.meta.name}] {method} on {len(results)} image(s)")
        self.set_state(NodeState.SUCCESS)
        return True

    def _apply_binarize(self, gray, method, threshold_value, block_size, c_value):
        if method == "adaptive_mean":
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                cv2.THRESH_BINARY, block_size, c_value
            )
        elif method == "adaptive_gaussian":
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, block_size, c_value
            )
        elif method == "otsu":
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        else:  # fixed
            _, binary = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)

        return binary, binary
