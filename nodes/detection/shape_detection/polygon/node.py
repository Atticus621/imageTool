"""Polygon detection node — detects polygons using contour approximation."""

import cv2
import numpy as np

from core.image_data import convert_to_gray
from core.roi import ROIManager
from nodes.detection.detection_base import DetectionBase


class PolygonDetectionNode(DetectionBase):
    NODE_ID = "detection/shape_detection/polygon"
    NODE_NAME = "多边形检测"
    NODE_CATEGORY = "检测"
    NODE_SUBCATEGORY = "形状检测"
    NODE_DESCRIPTION = "使用轮廓近似检测图像中的多边形"

    def _get_detection_params(self) -> dict:
        return {
            "epsilon_factor": self.params.get("epsilon_factor", 0.02),
            "min_area": self.params.get("min_area", 500),
        }

    def _detect(
        self, img: np.ndarray, color_space: str, **params
    ) -> tuple[np.ndarray | None, list]:
        output = img.copy()
        gray = convert_to_gray(img, color_space)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)

        contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        rois = []
        roi_mgr = ROIManager.instance()
        h, w = img.shape[:2]
        count = 0

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < params["min_area"]:
                continue

            epsilon = params["epsilon_factor"] * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)

            if len(approx) >= 3:
                cv2.drawContours(output, [approx], 0, (0, 255, 0), 2)
                count += 1
                vertices = approx.reshape(-1, 2).tolist()
                rois.append(roi_mgr.create(
                    roi_type="polygon",
                    data=vertices,
                    image_size=(w, h),
                    source_node=self.meta.name,
                ))

        if count > 0:
            text = f"Detected: {count} polygons"
            color = (0, 255, 0)
        else:
            text = "Not detected"
            color = (0, 0, 255)

        cv2.putText(output, text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        return output, rois
