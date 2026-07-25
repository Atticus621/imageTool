"""QR code / barcode detection node — supports OpenCV and pyzbar decoders."""

from __future__ import annotations

import cv2
import numpy as np

from core.logger import logger
from core.roi import ROIManager
from nodes.detection.detection_base import DetectionBase


class QRDetectNode(DetectionBase):
    """二维码/条码识别节点，支持 OpenCV 和 pyzbar 双解码器。"""

    NODE_ID = "detection/qrcode/qr_detect"
    NODE_NAME = "二维码识别"
    NODE_DESCRIPTION = (
        "检测并解码图像中的二维码和条码。\n"
        "- OpenCV: 内置支持，无需额外安装\n"
        "- pyzbar: 支持更多条码格式，pip install pyzbar"
    )
    NODE_INPUTS = [
        {"name": "images", "type": "image", "label": "图像输入"},
    ]
    NODE_OUTPUTS = [
        {"name": "images", "type": "image", "label": "标注图像"},
        {"name": "rois", "type": "roi", "label": "码区域"},
    ]
    NODE_OPTIONAL_PORTS = [
        {"name": "roi", "label": "ROI 输入", "port_type": "roi", "direction": "input", "default": False, "group": "input"},
        {"name": "forbidden", "label": "禁止区域", "port_type": "roi", "direction": "input", "default": False, "group": "input"},
    ]
    NODE_PARAMS = [
        {
            "name": "decoder",
            "type": "combo",
            "label": "解码器",
            "default": "opencv",
            "options": [
                {"value": "opencv", "label": "OpenCV 内置"},
                {"value": "pyzbar", "label": "pyzbar"},
            ],
        },
        {
            "name": "detect_qr",
            "type": "checkbox",
            "label": "检测二维码",
            "default": True,
        },
        {
            "name": "detect_barcode",
            "type": "checkbox",
            "label": "检测条码",
            "default": False,
        },
    ]

    def _get_detection_params(self) -> dict:
        return {
            "decoder": self.params.get("decoder", "opencv"),
            "detect_qr": bool(self.params.get("detect_qr", True)),
            "detect_barcode": bool(self.params.get("detect_barcode", False)),
        }

    def _detect(
        self, img: np.ndarray, color_space: str, **params
    ) -> tuple[np.ndarray | None, list]:
        decoder = params["decoder"]
        detect_qr = params["detect_qr"]
        detect_barcode = params["detect_barcode"]

        try:
            detections = self._run_decoder(img, decoder, detect_qr, detect_barcode)
        except ImportError as e:
            logger.error(f"[{self.meta.name}] 解码器 {decoder} 未安装: {e}")
            return None, []
        except Exception as e:
            logger.error(f"[{self.meta.name}] 识别失败: {e}")
            return None, []

        annotated = img.copy()
        rois = []
        roi_mgr = ROIManager.instance()
        h, w = img.shape[:2]

        for det in detections:
            bbox = det["bbox"]  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            decoded = det.get("data", "")
            code_type = det.get("type", "UNKNOWN")

            # Convert to axis-aligned rectangle
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
                metadata={
                    "decoded_data": decoded,
                    "code_type": code_type,
                    "decoder": decoder,
                },
            ))

            # Draw on annotated image
            pts = np.array(bbox, dtype=np.int32)
            cv2.polylines(annotated, [pts], True, (0, 255, 0), 2)

            label = f"{code_type}: {decoded[:30]}" if decoded else code_type
            cv2.putText(
                annotated, label, (x1, max(y1 - 5, 15)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1,
            )

        count = len(rois)
        text = f"Detected: {count} code(s)" if count > 0 else "No code detected"
        color = (0, 255, 0) if count > 0 else (0, 0, 255)
        cv2.putText(annotated, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

        return annotated, rois

    def _run_decoder(
        self, img: np.ndarray, decoder: str, detect_qr: bool, detect_barcode: bool
    ) -> list[dict]:
        """Run the selected decoder and return unified results.

        Returns list of {"bbox": [[x1,y1]..[x4,y4]], "data": str, "type": str}
        """
        if decoder == "opencv":
            return self._run_opencv(img, detect_qr)
        elif decoder == "pyzbar":
            return self._run_pyzbar(img, detect_qr, detect_barcode)
        else:
            raise ValueError(f"Unknown decoder: {decoder}")

    def _run_opencv(self, img, detect_qr):
        """Detect QR codes using OpenCV's built-in QRCodeDetector."""
        detections = []

        if not detect_qr:
            return detections

        detector = cv2.QRCodeDetector()

        # Try multi-detection first
        try:
            retval, decoded_info, points, _ = detector.detectAndDecodeMulti(img)
            if retval and points is not None:
                for i, (text, pts) in enumerate(zip(decoded_info, points)):
                    # pts is shape (4, 2)
                    bbox = pts.astype(int).tolist()
                    detections.append({
                        "bbox": bbox,
                        "data": text if text else "",
                        "type": "QRCODE",
                    })
                return detections
        except Exception:
            pass

        # Fallback: single QR detection
        try:
            retval, decoded_info, points = detector.detectAndDecode(img)
            if retval and points is not None:
                bbox = points[0].astype(int).tolist()
                detections.append({
                    "bbox": bbox,
                    "data": decoded_info if decoded_info else "",
                    "type": "QRCODE",
                })
        except Exception:
            pass

        return detections

    def _run_pyzbar(self, img, detect_qr, detect_barcode):
        """Detect QR codes and barcodes using pyzbar."""
        from pyzbar import pyzbar

        decoded_objects = pyzbar.decode(img)

        detections = []
        for obj in decoded_objects:
            obj_type = obj.type  # e.g. "QRCODE", "EAN13", "CODE128"

            # Filter by type
            if obj_type == "QRCODE" and not detect_qr:
                continue
            if obj_type != "QRCODE" and not detect_barcode:
                continue

            # pyzbar rect: (x, y, w, h)
            r = obj.rect
            bbox = [
                [r.left, r.top],
                [r.left + r.width, r.top],
                [r.left + r.width, r.top + r.height],
                [r.left, r.top + r.height],
            ]

            try:
                data = obj.data.decode("utf-8")
            except Exception:
                data = obj.data.hex()

            detections.append({
                "bbox": bbox,
                "data": data,
                "type": obj_type,
            })

        return detections
