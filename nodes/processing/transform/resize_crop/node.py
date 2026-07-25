"""Resize, crop, and rotate node."""

from __future__ import annotations

import cv2
import numpy as np

from core.image_data import ImageData
from core.logger import logger
from core.node_base.node import NodeBase, NodeState


class ResizeCropNode(NodeBase):
    """Resizes, crops, or rotates images."""

    NODE_ID = "processing/transform/resize_crop"
    NODE_NAME = "缩放裁剪"
    NODE_DESCRIPTION = "图像缩放、裁剪、旋转"
    NODE_INPUTS = [
        {"name": "images", "type": "image", "label": "图像输入"},
    ]
    NODE_OUTPUTS = [
        {"name": "images", "type": "image", "label": "图像输出"},
    ]

    def execute(self) -> bool:
        mode = self.params.get("mode", "resize")
        width = int(self.params.get("target_width", 640))
        height = int(self.params.get("target_height", 480))
        keep_ratio = self.params.get("keep_ratio", True)
        crop_x = int(self.params.get("crop_x", 0))
        crop_y = int(self.params.get("crop_y", 0))
        angle = float(self.params.get("angle", 0.0))

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

            if mode == "resize":
                processed = self._resize(img, width, height, keep_ratio)
            elif mode == "crop":
                processed = self._crop(img, crop_x, crop_y, width, height)
            else:  # rotate
                processed = self._rotate(img, angle)

            results.append(ImageData(array=processed, color_space=color_space))

        self._set_output_images("images", results)
        logger.info(f"[{self.meta.name}] {mode} on {len(results)} image(s)")
        self.set_state(NodeState.SUCCESS)
        return True

    def _resize(self, img, width, height, keep_ratio):
        if keep_ratio:
            h, w = img.shape[:2]
            scale = min(width / w, height / h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        return cv2.resize(img, (width, height), interpolation=cv2.INTER_LINEAR)

    def _crop(self, img, x, y, w, h):
        h_img, w_img = img.shape[:2]
        x1 = max(0, min(x, w_img))
        y1 = max(0, min(y, h_img))
        x2 = min(x1 + w, w_img)
        y2 = min(y1 + h, h_img)
        return img[y1:y2, x1:x2].copy()

    def _rotate(self, img, angle):
        h, w = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(img, M, (w, h), borderValue=(0, 0, 0))
