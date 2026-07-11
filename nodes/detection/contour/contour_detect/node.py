"""Contour detection node — finds contours with area/vertex filtering."""

from __future__ import annotations

import cv2
import numpy as np

from core.image_data import ImageData, convert_to_gray
from core.logger import logger
from core.node_base.node import NodeBase, NodeState
from core.roi import ROIManager


class ContourDetectNode(NodeBase):
    """Detects contours in images with configurable filtering."""

    NODE_ID = "detection/contour/contour_detect"
    NODE_NAME = "轮廓检测"
    NODE_CATEGORY = "检测"
    NODE_DESCRIPTION = "检测图像中的轮廓，支持面积和顶点数过滤"
    NODE_INPUTS = [
        {"name": "images", "type": "image", "label": "图像输入"},
    ]
    NODE_OUTPUTS = [
        {"name": "images", "type": "image", "label": "标注图像"},
        {"name": "rois", "type": "roi", "label": "检测区域"},
    ]
    NODE_OPTIONAL_PORTS = [
        {"name": "roi", "label": "ROI 输入", "port_type": "roi", "direction": "input", "default": False, "group": "input"},
    ]
    NODE_PARAMS = [
        {"name": "min_area", "type": "int_slider", "label": "最小面积", "default": 500, "min": 10, "max": 10000, "step": 10, "pinned": True},
        {"name": "max_area", "type": "int_slider", "label": "最大面积", "default": 100000, "min": 1000, "max": 1000000, "step": 100},
        {"name": "epsilon_factor", "type": "float_slider", "label": "近似精度", "default": 0.02, "min": 0.001, "max": 0.1, "step": 0.001},
        {"name": "retrieval_mode", "type": "combo", "label": "检索模式", "default": "tree",
         "options": [
             {"value": "external", "label": "_EXTERNAL (仅外部)"},
             {"value": "list", "label": "_LIST (所有轮廓)"},
             {"value": "tree", "label": "_TREE (层级树)"},
         ]},
    ]

    _RETR_MAP = {
        "external": cv2.RETR_EXTERNAL,
        "list": cv2.RETR_LIST,
        "tree": cv2.RETR_TREE,
    }

    def execute(self) -> bool:
        min_area = int(self.params.get("min_area", 500))
        max_area = int(self.params.get("max_area", 100000))
        epsilon_factor = float(self.params.get("epsilon_factor", 0.02))
        retrieval_mode = self.params.get("retrieval_mode", "tree")

        items = self._get_input_images_raw("images")
        if not items:
            logger.warning(f"[{self.meta.name}] No input images")
            self.set_state(NodeState.ERROR)
            return False

        output_annotated = self.params.get("_opt_annotated", False)
        retr = self._RETR_MAP.get(retrieval_mode, cv2.RETR_TREE)
        roi_mgr = ROIManager.instance()

        results = []
        all_rois = []

        for item in items:
            if isinstance(item, ImageData):
                img = item.array
                color_space = item.color_space
            else:
                img = item
                color_space = "bgr"

            annotated, rois = self._detect(img, color_space, min_area, max_area, epsilon_factor, retr, roi_mgr)
            if annotated is not None:
                results.append(ImageData(array=annotated, color_space=color_space))
            all_rois.extend(rois)

        if results:
            self._set_output_images("images", results)
        self._set_output_rois("rois", all_rois)

        # Output optional statistics
        count = len(all_rois)
        if self._opt_enabled("count"):
            self._set_output_port("count", count)
        if self._opt_enabled("stats"):
            if count > 0:
                stats_text = f"检测到 {count} 个轮廓"
            else:
                stats_text = "未检测到轮廓"
            self._set_output_port("stats", stats_text)

        logger.info(f"[{self.meta.name}] Found {count} contours from {len(items)} image(s)")
        self.set_state(NodeState.SUCCESS)
        return True

    def _detect(self, img, color_space, min_area, max_area, epsilon_factor, retr, roi_mgr):
        output = img.copy()
        gray = convert_to_gray(img, color_space)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)

        contours, _ = cv2.findContours(edges, retr, cv2.CHAIN_APPROX_SIMPLE)

        rois = []
        h, w = img.shape[:2]

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area or area > max_area:
                continue

            epsilon = epsilon_factor * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)

            # Draw contour
            cv2.drawContours(output, [approx], 0, (0, 255, 0), 2)

            # Create polygon ROI using ROIManager
            vertices = approx.reshape(-1, 2).tolist()
            rois.append(roi_mgr.create(
                roi_type="polygon",
                data=vertices,
                image_size=(w, h),
                source_node=self.meta.name,
            ))

        count = len(rois)
        text = f"Detected: {count} contours" if count > 0 else "Not detected"
        color = (0, 255, 0) if count > 0 else (0, 0, 255)
        cv2.putText(output, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        return output, rois
