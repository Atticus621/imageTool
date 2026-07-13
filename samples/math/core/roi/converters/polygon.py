"""多边形 ROI 转换器。"""

from __future__ import annotations

from typing import TYPE_CHECKING

import cv2
import numpy as np

from ..converter import IROIConverter, converter_registry

if TYPE_CHECKING:
    from ..data import ROIData


class PolygonConverter(IROIConverter):
    """多边形 ROI 转换器。

    data 格式: Nx2 array/list of (x, y) vertices.
    """

    type_id = "polygon"

    def to_mask(self, roi: ROIData, image_size: tuple[int, int]) -> np.ndarray:
        w, h = image_size
        mask = np.zeros((h, w), dtype=np.uint8)
        pts = np.asarray(roi.data, dtype=np.int32)
        if pts.size == 0:
            return mask.astype(bool)
        if pts.ndim == 2:
            pts = pts.reshape(1, -1, 2)
        cv2.fillPoly(mask, pts, 1)
        return mask.astype(bool)

    def to_dict(self, roi: ROIData) -> dict:
        pts = np.asarray(roi.data, dtype=np.float64)
        return {
            "roi_type": self.type_id,
            "data": pts.tolist(),
            "image_size": list(roi.image_size) if roi.image_size else None,
            "trace_id": roi.trace_id,
            "metadata": roi.metadata,
        }

    def from_dict(self, data: dict) -> ROIData:
        from ..data import ROIData as RD

        image_size = tuple(data["image_size"]) if data.get("image_size") else None
        return RD(
            roi_type=self.type_id,
            data=np.asarray(data["data"], dtype=np.int32),
            image_size=image_size,
            trace_id=data.get("trace_id", ""),
            metadata=data.get("metadata", {}),
        )

    def validate(self, roi: ROIData) -> list[str]:
        warnings = []
        pts = np.asarray(roi.data)
        if pts.ndim != 2 or pts.shape[1] != 2:
            warnings.append(f"Polygon data must be Nx2, got shape {pts.shape}")
        elif pts.shape[0] < 3:
            warnings.append(f"Polygon has only {pts.shape[0]} vertices (need >= 3)")
        return warnings


converter_registry.register(PolygonConverter())
