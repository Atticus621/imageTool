"""Centroid localization node — finds object centers via contour moments."""

from __future__ import annotations

import cv2
import numpy as np

from core.image_data import ImageData, convert_to_gray
from core.logger import logger
from core.node_base.node import NodeBase, NodeState
from core.roi import ROIManager


class CentroidNode(NodeBase):
    """Locates object centroids using contour moments."""

    NODE_ID = "detection/location/centroid"
    NODE_NAME = "质心定位"
    NODE_DESCRIPTION = "通过轮廓矩计算物体质心位置"
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
        {"name": "min_area", "type": "int_slider", "label": "最小面积", "default": 500, "min": 10, "max": 10000, "step": 10},
        {"name": "draw_cross", "type": "checkbox", "label": "绘制十字标记", "default": True},
        {"name": "draw_label", "type": "checkbox", "label": "绘制坐标文字", "default": True},
    ]

    def execute(self) -> bool:
        min_area = int(self.params.get("min_area", 500))
        draw_cross = self.params.get("draw_cross", True)
        draw_label = self.params.get("draw_label", True)

        items = self._get_input_images_raw("images")
        if not items:
            logger.warning(f"[{self.meta.name}] No input images")
            self.set_state(NodeState.ERROR)
            return False

        output_annotated = self.params.get("_opt_annotated", False)
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

            annotated, rois = self._detect(img, color_space, min_area, draw_cross, draw_label, roi_mgr)
            if annotated is not None:
                results.append(ImageData(array=annotated, color_space=color_space))
            all_rois.extend(rois)

        if results:
            self._set_output_images("images", results)
        self._set_output_rois("rois", all_rois)

        logger.info(f"[{self.meta.name}] Found {len(all_rois)} centroids from {len(items)} image(s)")
        self.set_state(NodeState.SUCCESS)
        return True

    def _detect(self, img, color_space, min_area, draw_cross, draw_label, roi_mgr):
        output = img.copy()
        gray = convert_to_gray(img, color_space)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        rois = []
        h, w = img.shape[:2]

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area:
                continue

            M = cv2.moments(contour)
            if M["m00"] == 0:
                continue

            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])

            # Create circle ROI at centroid using ROIManager
            radius = int(np.sqrt(area / np.pi))
            rois.append(roi_mgr.create(
                roi_type="circle",
                data=(cx, cy, radius),
                image_size=(w, h),
                source_node=self.meta.name,
            ))

            # Draw on output
            if draw_cross:
                cv2.drawMarker(output, (cx, cy), (0, 0, 255),
                               cv2.MARKER_CROSS, 20, 2)
            if draw_label:
                cv2.putText(output, f"({cx},{cy})", (cx + 10, cy - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        count = len(rois)
        text = f"Found: {count} centroids" if count > 0 else "Not detected"
        color = (0, 255, 0) if count > 0 else (0, 0, 255)
        cv2.putText(output, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        return output, rois
