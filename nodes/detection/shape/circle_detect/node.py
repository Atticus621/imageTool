"""Circle detection node — detects circles using Hough transform."""

import cv2
import numpy as np

from core.image_data import convert_to_gray
from core.roi import ROIManager
from nodes.detection.detection_base import DetectionBase


class CircleDetectionNode(DetectionBase):
    NODE_ID = "detection/shape/circle_detect"
    NODE_NAME = "圆形检测"
    NODE_DESCRIPTION = "使用霍夫圆变换检测图像中的圆形"

    def _get_detection_params(self) -> dict:
        return {
            "dp": self.params.get("dp", 1.2),
            "min_dist": self.params.get("min_dist", 50),
            "param1": self.params.get("param1", 100),
            "param2": self.params.get("param2", 30),
            "min_radius": self.params.get("min_radius", 10),
            "max_radius": self.params.get("max_radius", 200),
        }

    def _detect(
        self, img: np.ndarray, color_space: str, **params
    ) -> tuple[np.ndarray | None, list]:
        output = img.copy()
        gray = convert_to_gray(img, color_space)
        gray = cv2.GaussianBlur(gray, (9, 9), 2)

        circles = cv2.HoughCircles(
            gray, cv2.HOUGH_GRADIENT,
            params["dp"], params["min_dist"],
            param1=params["param1"], param2=params["param2"],
            minRadius=params["min_radius"], maxRadius=params["max_radius"],
        )

        rois = []
        roi_mgr = ROIManager.instance()
        h, w = img.shape[:2]

        if circles is not None:
            circles = np.uint16(np.around(circles))
            for c in circles[0, :]:
                center = (c[0], c[1])
                radius = c[2]
                cv2.circle(output, center, radius, (0, 255, 0), 2)
                cv2.drawMarker(output, center, (0, 0, 255),
                               cv2.MARKER_CROSS, 20, 2)
                rois.append(roi_mgr.create(
                    roi_type="circle",
                    data=(int(c[0]), int(c[1]), int(c[2])),
                    image_size=(w, h),
                    source_node=self.meta.name,
                ))
            text = f"Detected: {len(circles[0])} circles"
            color = (0, 255, 0)
        else:
            text = "Not detected"
            color = (0, 0, 255)

        cv2.putText(output, text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        return output, rois
