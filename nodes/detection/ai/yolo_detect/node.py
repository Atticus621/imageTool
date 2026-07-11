"""YOLO detection node — uses ultralytics YOLOv8+ for object detection."""

import numpy as np

from core.logger import logger
from core.roi import ROIManager
from nodes.detection.detection_base import DetectionBase


class YoloDetectNode(DetectionBase):
    """YOLO 目标检测节点。"""

    NODE_ID = "detection/ai/yolo_detect"
    NODE_NAME = "YOLO检测"
    NODE_CATEGORY = "检测"
    NODE_DESCRIPTION = "使用 ultralytics YOLOv8+ 模型进行目标检测"

    def _get_detection_params(self) -> dict:
        model_path_param = self.params.get("model_path", [])
        if isinstance(model_path_param, list):
            model_path = model_path_param[0] if model_path_param else ""
        else:
            model_path = str(model_path_param).strip()

        return {
            "model_path": model_path,
            "conf_threshold": self.params.get("conf_threshold", 0.25),
            "iou_threshold": self.params.get("iou_threshold", 0.45),
        }

    def _detect(
        self, img: np.ndarray, color_space: str, **params
    ) -> tuple[np.ndarray | None, list]:
        model_path = params["model_path"]
        if not model_path:
            logger.error(f"[{self.meta.name}] 未指定模型文件路径")
            return None, []

        try:
            from ultralytics import YOLO
            model = YOLO(model_path)
        except Exception as e:
            logger.error(f"[{self.meta.name}] 加载模型失败: {e}")
            return None, []

        det_results = model(
            img,
            conf=params["conf_threshold"],
            iou=params["iou_threshold"],
            verbose=False,
        )

        annotated = det_results[0].plot()

        rois = []
        roi_mgr = ROIManager.instance()
        h, w = img.shape[:2]

        for box in det_results[0].boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            rois.append(roi_mgr.create(
                roi_type="rectangle",
                data=(float(x1), float(y1), float(x2 - x1), float(y2 - y1)),
                image_size=(w, h),
                source_node=self.meta.name,
                metadata={"confidence": float(box.conf[0])},
            ))

        return annotated, rois
