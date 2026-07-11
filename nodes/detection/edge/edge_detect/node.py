"""Edge detection node — Canny, Sobel, Laplacian."""

from __future__ import annotations

import cv2
import numpy as np

from core.image_data import ImageData, ColorSpace, convert_to_gray
from core.logger import logger
from core.node_base.node import NodeBase, NodeState


class EdgeDetectNode(NodeBase):
    """Detects edges using Canny, Sobel, or Laplacian methods."""

    NODE_ID = "detection/edge/edge_detect"
    NODE_NAME = "边缘检测"
    NODE_CATEGORY = "检测"
    NODE_DESCRIPTION = "图像边缘检测：Canny、Sobel、Laplacian"
    NODE_INPUTS = [
        {"name": "images", "type": "image", "label": "图像输入"},
    ]
    NODE_OUTPUTS = [
        {"name": "images", "type": "image", "label": "边缘图像"},
    ]

    def execute(self) -> bool:
        method = self.params.get("method", "canny")
        threshold1 = int(self.params.get("threshold1", 50))
        threshold2 = int(self.params.get("threshold2", 150))
        ksize = int(self.params.get("ksize", 3))

        items = self._get_input_images_raw("images")
        if not items:
            logger.warning(f"[{self.meta.name}] No input images")
            self.set_state(NodeState.ERROR)
            return False

        # Ensure ksize is odd
        if ksize % 2 == 0:
            ksize += 1

        results = []
        for item in items:
            if isinstance(item, ImageData):
                img = item.array
                color_space = item.color_space
            else:
                img = item
                color_space = "bgr"

            gray = convert_to_gray(img, color_space)
            edges = self._detect_edges(gray, method, threshold1, threshold2, ksize)
            results.append(ImageData(array=edges, color_space=ColorSpace.GRAY.value))

        self._set_output_images("images", results)
        logger.info(f"[{self.meta.name}] {method} (t1={threshold1}, t2={threshold2}, k={ksize}) on {len(results)} image(s)")
        self.set_state(NodeState.SUCCESS)
        return True

    def _detect_edges(self, gray, method, threshold1, threshold2, ksize):
        if method == "sobel":
            sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=ksize)
            sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=ksize)
            magnitude = cv2.magnitude(sobel_x, sobel_y)
            return cv2.convertScaleAbs(magnitude)
        elif method == "laplacian":
            laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=ksize)
            return cv2.convertScaleAbs(laplacian)
        else:  # canny
            return cv2.Canny(gray, threshold1, threshold2)
