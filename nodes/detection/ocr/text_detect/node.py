"""OCR text detection node — multi-engine text detection and recognition."""

from __future__ import annotations

import cv2
import numpy as np

from core.logger import logger
from core.roi import ROIManager
from nodes.detection.detection_base import DetectionBase


class TextDetectNode(DetectionBase):
    """文字检测节点，支持多 OCR 引擎切换。"""

    NODE_ID = "detection/ocr/text_detect"
    NODE_NAME = "文字检测(OCR)"
    NODE_CATEGORY = "检测"
    NODE_DESCRIPTION = (
        "检测并识别图像中的文字区域。支持三种引擎：\n"
        "- PaddleOCR: pip install paddleocr paddlepaddle\n"
        "- Tesseract: 需安装 tesseract-ocr 系统依赖 + pip install pytesseract\n"
        "- EasyOCR: pip install easyocr"
    )
    NODE_INPUTS = [
        {"name": "images", "type": "image", "label": "图像输入"},
    ]
    NODE_OUTPUTS = [
        {"name": "images", "type": "image", "label": "标注图像"},
        {"name": "rois", "type": "roi", "label": "文字区域"},
    ]
    NODE_OPTIONAL_PORTS = [
        {"name": "roi", "label": "ROI 输入", "port_type": "roi", "direction": "input", "default": False, "group": "input"},
        {"name": "forbidden", "label": "禁止区域", "port_type": "roi", "direction": "input", "default": False, "group": "input"},
    ]
    NODE_PARAMS = [
        {
            "name": "engine",
            "type": "combo",
            "label": "OCR 引擎",
            "default": "paddleocr",
            "options": [
                {"value": "paddleocr", "label": "PaddleOCR"},
                {"value": "tesseract", "label": "Tesseract"},
                {"value": "easyocr", "label": "EasyOCR"},
            ],
        },
        {
            "name": "languages",
            "type": "text",
            "label": "识别语言",
            "default": "ch",
        },
        {
            "name": "min_confidence",
            "type": "float_slider",
            "label": "最低置信度",
            "default": 0.5,
            "min": 0.0,
            "max": 1.0,
            "step": 0.05,
        },
        {
            "name": "detect_only",
            "type": "checkbox",
            "label": "仅检测位置（不识别文字）",
            "default": False,
        },
    ]

    def _get_detection_params(self) -> dict:
        return {
            "engine": self.params.get("engine", "paddleocr"),
            "languages": self.params.get("languages", "ch"),
            "min_confidence": float(self.params.get("min_confidence", 0.5)),
            "detect_only": bool(self.params.get("detect_only", False)),
        }

    def _detect(
        self, img: np.ndarray, color_space: str, **params
    ) -> tuple[np.ndarray | None, list]:
        engine = params["engine"]
        lang = params["languages"]
        min_conf = params["min_confidence"]
        detect_only = params["detect_only"]

        try:
            detections = self._run_engine(img, engine, lang, detect_only)
        except ImportError as e:
            logger.error(f"[{self.meta.name}] 引擎 {engine} 未安装: {e}")
            return None, []
        except Exception as e:
            logger.error(f"[{self.meta.name}] OCR 执行失败: {e}")
            return None, []

        # Filter by confidence and build ROIs
        annotated = img.copy()
        rois = []
        roi_mgr = ROIManager.instance()
        h, w = img.shape[:2]

        for det in detections:
            bbox = det["bbox"]  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            text = det.get("text", "")
            conf = det.get("confidence", 0.0)

            if conf < min_conf:
                continue

            # Convert 4-point bbox to axis-aligned rectangle
            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            x1, y1 = max(0, int(min(xs))), max(0, int(min(ys)))
            x2, y2 = min(w, int(max(xs))), min(h, int(max(ys)))

            if x2 - x1 < 2 or y2 - y1 < 2:
                continue

            rois.append(roi_mgr.create(
                roi_type="rectangle",
                data=(float(x1), float(y1), float(x2 - x1), float(y2 - y1)),
                image_size=(w, h),
                source_node=self.meta.name,
                metadata={"text": text, "confidence": conf, "engine": engine},
            ))

            # Draw on annotated image
            pts = np.array(bbox, dtype=np.int32)
            cv2.polylines(annotated, [pts], True, (0, 255, 0), 2)

            label = f"{text} ({conf:.0%})" if text else f"({conf:.0%})"
            cv2.putText(
                annotated, label, (x1, max(y1 - 5, 15)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1,
            )

        count = len(rois)
        text = f"Detected: {count} text regions" if count > 0 else "No text detected"
        color = (0, 255, 0) if count > 0 else (0, 0, 255)
        cv2.putText(annotated, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        return annotated, rois

    def _run_engine(
        self, img: np.ndarray, engine: str, lang: str, detect_only: bool
    ) -> list[dict]:
        """Run the selected OCR engine and return unified results.

        Returns list of {"bbox": [[x1,y1]..[x4,y4]], "text": str, "confidence": float}
        """
        if engine == "paddleocr":
            return self._run_paddleocr(img, lang, detect_only)
        elif engine == "tesseract":
            return self._run_tesseract(img, lang, detect_only)
        elif engine == "easyocr":
            return self._run_easyocr(img, lang, detect_only)
        else:
            raise ValueError(f"Unknown engine: {engine}")

    def _run_paddleocr(self, img, lang, detect_only):
        from paddleocr import PaddleOCR

        ocr = PaddleOCR(use_angle_cls=not detect_only, lang=lang, show_log=False)
        result = ocr.ocr(img, cls=not detect_only)

        detections = []
        if not result or not result[0]:
            return detections

        for line in result[0]:
            bbox = line[0]  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            text_info = line[1]
            text = text_info[0] if not detect_only else ""
            conf = float(text_info[1])
            detections.append({"bbox": bbox, "text": text, "confidence": conf})

        return detections

    def _run_tesseract(self, img, lang, detect_only):
        import pytesseract

        if detect_only:
            data = pytesseract.image_to_data(
                img, lang=lang, output_type=pytesseract.Output.DICT,
                config="--psm 11",
            )
        else:
            data = pytesseract.image_to_data(
                img, lang=lang, output_type=pytesseract.Output.DICT,
            )

        detections = []
        n = len(data["text"])

        for i in range(n):
            text = data["text"][i].strip()
            conf = float(data["conf"][i]) / 100.0

            if conf < 0 or (not detect_only and not text):
                continue

            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            if w < 2 or h < 2:
                continue

            bbox = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]
            detections.append({"bbox": bbox, "text": text, "confidence": conf})

        return detections

    def _run_easyocr(self, img, lang, detect_only):
        import easyocr

        reader = easyocr.Reader([lang], verbose=False)
        result = reader.readtext(img)

        detections = []
        for (bbox, text, conf) in result:
            # easyocr returns 4-point bbox as [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            if detect_only:
                text = ""
            detections.append({"bbox": bbox, "text": text, "confidence": float(conf)})

        return detections
