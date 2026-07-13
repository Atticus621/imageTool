"""ROISerializer — JSON + Base64 序列化。

掩码数据用 Base64 编码（numpy → bytes → base64），
形状参数直接存 JSON。
"""

from __future__ import annotations

import base64
import json
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np

from core.logger import logger
from .converter import converter_registry
from .data import ROIData, ROIError


class ROISerializer:
    """ROI 序列化/反序列化工具。

    JSON 格式：
    {
        "version": 1,
        "rois": [
            {
                "roi_type": "circle",
                "data": [100, 200, 50],
                "image_size": [1920, 1080],
                "trace_id": "roi_a1b2c3d4",
                "metadata": {}
            },
            {
                "roi_type": "mask",
                "data": null,
                "mask_base64": "...",
                "mask_shape": [1080, 1920],
                "mask_dtype": "uint8",
                "image_size": [1920, 1080],
                ...
            }
        ]
    }
    """

    @staticmethod
    def save(roi: ROIData, path: str | Path) -> None:
        """保存单个 ROI 到 JSON 文件。"""
        ROISerializer.save_rois([roi], path)

    @staticmethod
    def load(path: str | Path) -> ROIData:
        """从 JSON 文件加载单个 ROI。"""
        rois = ROISerializer.load_rois(path)
        if not rois:
            raise ROIError(f"No ROI found in {path}")
        return rois[0]

    @staticmethod
    def save_rois(rois: list[ROIData], path: str | Path) -> None:
        """保存多个 ROI 到 JSON 文件。"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": 1,
            "rois": [ROISerializer._roi_to_json(roi) for roi in rois],
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"[ROISerializer] Saved {len(rois)} ROIs to {path}")

    @staticmethod
    def load_rois(path: str | Path) -> list[ROIData]:
        """从 JSON 文件加载多个 ROI。"""
        path = Path(path)
        if not path.exists():
            raise ROIError(f"ROI file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        version = data.get("version", 1)
        if version != 1:
            logger.warning(f"[ROISerializer] Unknown version {version}, trying anyway")

        rois = []
        for item in data.get("rois", []):
            rois.append(ROISerializer._roi_from_json(item))

        logger.info(f"[ROISerializer] Loaded {len(rois)} ROIs from {path}")
        return rois

    @staticmethod
    def roi_to_dict(roi: ROIData) -> dict:
        """将单个 ROI 转为 JSON 兼容字典。"""
        return ROISerializer._roi_to_json(roi)

    @staticmethod
    def roi_from_dict(data: dict) -> ROIData:
        """从字典创建 ROIData。"""
        return ROISerializer._roi_from_json(data)

    @staticmethod
    def _roi_to_json(roi: ROIData) -> dict:
        """内部方法：ROI → JSON 字典。"""
        converter = converter_registry.get(roi.roi_type)
        d = converter.to_dict(roi)

        # 掩码类型需要 Base64 编码
        if roi.roi_type == "mask":
            mask_data = np.asarray(roi.data, dtype=np.uint8)
            buf = BytesIO()
            np.save(buf, mask_data, allow_pickle=False)
            d["mask_base64"] = base64.b64encode(buf.getvalue()).decode("ascii")

        return d

    @staticmethod
    def _roi_from_json(data: dict) -> ROIData:
        """内部方法：JSON 字典 → ROIData。"""
        roi_type = data.get("roi_type", "")
        converter = converter_registry.get(roi_type)

        # 掩码类型需要 Base64 解码
        if roi_type == "mask" and "mask_base64" in data:
            raw = base64.b64decode(data["mask_base64"])
            buf = BytesIO(raw)
            data["data"] = np.load(buf, allow_pickle=False)

        return converter.from_dict(data)
