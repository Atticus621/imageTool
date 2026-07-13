"""掩码 ROI 转换器。"""

from __future__ import annotations

from typing import TYPE_CHECKING

import cv2
import numpy as np

from ..converter import IROIConverter, converter_registry

if TYPE_CHECKING:
    from ..data import ROIData


class MaskConverter(IROIConverter):
    """掩码 ROI 转换器。

    data 格式: numpy array (binary mask, bool or uint8).
    """

    type_id = "mask"

    def to_mask(self, roi: ROIData, image_size: tuple[int, int]) -> np.ndarray:
        w, h = image_size
        data = np.asarray(roi.data)
        if data.shape[:2] != (h, w):
            data = cv2.resize(data, (w, h), interpolation=cv2.INTER_NEAREST)
        return data.astype(bool)

    def to_dict(self, roi: ROIData) -> dict:
        # 掩码数据用列表存储（小掩码）或标记需要 Base64 编码（大掩码）
        # Base64 编码由 serializer 处理
        data = np.asarray(roi.data, dtype=np.uint8)
        return {
            "roi_type": self.type_id,
            "data": None,  # 大掩码不直接存 JSON
            "mask_shape": list(data.shape),
            "mask_dtype": str(data.dtype),
            "image_size": list(roi.image_size) if roi.image_size else None,
            "trace_id": roi.trace_id,
            "metadata": roi.metadata,
        }

    def from_dict(self, data: dict) -> ROIData:
        from ..data import ROIData as RD

        # 掩码数据需要从 Base64 解码，由 serializer 处理
        # 此处接收已解码的 numpy array
        mask_data = data.get("data")
        if mask_data is None:
            raise ValueError("Mask data missing (should be decoded by serializer)")

        image_size = tuple(data["image_size"]) if data.get("image_size") else None
        return RD(
            roi_type=self.type_id,
            data=np.asarray(mask_data, dtype=np.uint8),
            image_size=image_size,
            trace_id=data.get("trace_id", ""),
            metadata=data.get("metadata", {}),
        )

    def validate(self, roi: ROIData) -> list[str]:
        warnings = []
        data = np.asarray(roi.data)
        if data.ndim < 2:
            warnings.append(f"Mask must be at least 2D, got shape {data.shape}")
        if roi.image_size and data.shape[:2] != (roi.image_size[1], roi.image_size[0]):
            warnings.append(
                f"Mask shape {data.shape[:2]} != image_size {roi.image_size} "
                "(will be resized on conversion)"
            )
        return warnings


converter_registry.register(MaskConverter())
