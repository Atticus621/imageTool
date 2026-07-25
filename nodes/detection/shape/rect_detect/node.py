"""Rectangle detection node — detects rectangles via minAreaRect or approxPolyDP."""

from __future__ import annotations

import cv2
import numpy as np

from core.image_data import ImageData, convert_to_gray
from core.logger import logger
from core.node_base.node import NodeBase, NodeState
from core.roi import ROIManager


class RectDetectNode(NodeBase):
    """Detects rectangles and quadrilaterals in images."""

    NODE_ID = "detection/shape/rect_detect"
    NODE_NAME = "矩形检测"
    NODE_DESCRIPTION = "检测图像中的矩形和四边形"
    NODE_INPUTS = [
        {"name": "images", "type": "image", "label": "图像输入"},
    ]
    NODE_OUTPUTS = [
        {"name": "images", "type": "image", "label": "标注图像"},
        {"name": "rois", "type": "roi", "label": "检测区域"},
    ]
    NODE_OPTIONAL_PORTS = [
        {"name": "roi", "label": "ROI 输入", "port_type": "roi", "direction": "input", "default": False, "group": "input"},
        {"name": "count", "label": "检测数量", "port_type": "number", "direction": "output", "default": False, "group": "output"},
        {"name": "stats", "label": "统计信息", "port_type": "string", "direction": "output", "default": False, "group": "output"},
    ]
    NODE_PARAMS = [
        {"name": "min_area", "type": "int_slider", "label": "最小面积", "default": 500, "min": 10, "max": 10000, "step": 10},
        {"name": "epsilon_factor", "type": "float_slider", "label": "近似精度", "default": 0.02, "min": 0.001, "max": 0.1, "step": 0.001},
        {"name": "detect_mode", "type": "combo", "label": "检测模式", "default": "rect",
         "options": [
             {"value": "rect", "label": "最小外接矩形"},
             {"value": "quad", "label": "四边形近似"},
         ]},
    ]

    def execute(self) -> bool:
        min_area = int(self.params.get("min_area", 500))
        epsilon_factor = float(self.params.get("epsilon_factor", 0.02))
        detect_mode = self.params.get("detect_mode", "rect")

        items = self._get_input_images_raw("images")
        if not items:
            logger.warning(f"[{self.meta.name}] No input images")
            self.set_state(NodeState.ERROR)
            return False

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

            annotated, rois = self._detect(img, color_space, min_area, epsilon_factor, detect_mode, roi_mgr)
            if annotated is not None:
                results.append(ImageData(array=annotated, color_space=color_space))
            all_rois.extend(rois)

        if results:
            self._set_output_images("images", results)
        self._set_output_rois("rois", all_rois)

        logger.info(f"[{self.meta.name}] Found {len(all_rois)} rectangles from {len(items)} image(s)")
        self.set_state(NodeState.SUCCESS)
        return True

    def _detect(self, img, color_space, min_area, epsilon_factor, detect_mode, roi_mgr):
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

            if detect_mode == "rect":
                # MinAreaRect approach
                rect = cv2.minAreaRect(contour)
                box = cv2.boxPoints(rect)
                box = np.intp(box)
                cv2.drawContours(output, [box], 0, (0, 255, 0), 2)
                vertices = box.tolist()
            else:
                # ApproxPolyDP approach (must have 4 vertices)
                epsilon = epsilon_factor * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                if len(approx) != 4:
                    continue
                cv2.drawContours(output, [approx], 0, (0, 255, 0), 2)
                vertices = approx.reshape(-1, 2).tolist()

            rois.append(roi_mgr.create(
                roi_type="polygon",
                data=vertices,
                image_size=(w, h),
                source_node=self.meta.name,
            ))

        count = len(rois)
        text = f"Detected: {count} rectangles" if count > 0 else "Not detected"
        color = (0, 255, 0) if count > 0 else (0, 0, 255)
        cv2.putText(output, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        return output, rois
