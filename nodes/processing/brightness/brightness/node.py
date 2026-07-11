"""Brightness and contrast adjustment node."""

from __future__ import annotations

import cv2
import numpy as np

from core.image_data import ImageData
from core.logger import logger
from core.node_base.node import NodeBase, NodeState


class BrightnessNode(NodeBase):
    """Adjusts image brightness, contrast, and optional CLAHE equalization."""

    NODE_ID = "processing/brightness/brightness"
    NODE_NAME = "亮度对比度"
    NODE_CATEGORY = "图像处理"
    NODE_SUBCATEGORY = "预处理"
    NODE_DESCRIPTION = "调整图像亮度、对比度，支持CLAHE自适应均衡化"
    NODE_INPUTS = [
        {"name": "images", "type": "image", "label": "图像输入"},
    ]
    NODE_OUTPUTS = [
        {"name": "images", "type": "image", "label": "图像输出"},
    ]

    def execute(self) -> bool:
        brightness = int(self.params.get("brightness", 0))
        contrast = float(self.params.get("contrast", 1.0))
        clahe_enabled = self.params.get("clahe", False)
        clahe_clip = int(self.params.get("clahe_clip", 2))

        items = self._get_input_images_raw("images")
        if not items:
            logger.warning(f"[{self.meta.name}] No input images")
            self.set_state(NodeState.ERROR)
            return False

        results = []
        for item in items:
            if isinstance(item, ImageData):
                img = item.array
                color_space = item.color_space
            else:
                img = item
                color_space = "bgr"

            processed = self._adjust(img, brightness, contrast, clahe_enabled, clahe_clip)
            results.append(ImageData(array=processed, color_space=color_space))

        self._set_output_images("images", results)
        logger.info(f"[{self.meta.name}] brightness={brightness}, contrast={contrast:.1f} on {len(results)} image(s)")
        self.set_state(NodeState.SUCCESS)
        return True

    def _adjust(self, img, brightness, contrast, clahe_enabled, clahe_clip):
        # Apply contrast and brightness: output = img * alpha + beta
        result = cv2.convertScaleAbs(img, alpha=contrast, beta=brightness)

        if clahe_enabled:
            if len(result.shape) == 3:
                # Apply CLAHE to L channel in LAB space
                lab = cv2.cvtColor(result, cv2.COLOR_BGR2LAB)
                clahe = cv2.createCLAHE(clipLimit=float(clahe_clip), tileGridSize=(8, 8))
                lab[:, :, 0] = clahe.apply(lab[:, :, 0])
                result = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            else:
                clahe = cv2.createCLAHE(clipLimit=float(clahe_clip), tileGridSize=(8, 8))
                result = clahe.apply(result)

        return result
