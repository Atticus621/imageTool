"""ROIManager — ROI 操作的统一入口。

节点通过此类创建、查询、应用 ROI，不直接接触转换器。
"""

from __future__ import annotations

from typing import Any

import numpy as np

from core.logger import logger
from .converter import converter_registry
from .data import ROIData, ROIError
from .ops import apply_roi_constraint, combine_rois
from .tracer import ROITracer


class ROIManager:
    """ROI 操作协调器。

    节点使用示例：
        roi = self._roi.create("circle", (100, 200, 50), (1920, 1080), "my_node")
        mask = self._roi.to_mask(roi, (1920, 1080))
        result = self._roi.apply_constraint(original, processed, rois)
    """

    _instance: ROIManager | None = None

    def __init__(self):
        self._tracer = ROITracer.instance()

    @classmethod
    def instance(cls) -> ROIManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """重置单例（仅用于测试）。"""
        cls._instance = None

    def create(
        self,
        roi_type: str,
        data: Any,
        image_size: tuple[int, int] | None = None,
        source_node: str = "",
        metadata: dict | None = None,
    ) -> ROIData:
        """创建 ROIData，自动分配 trace_id 并校验。

        Args:
            roi_type: 类型标识符（如 "circle"）。
            data: 类型特定数据。
            image_size: 参考图像尺寸 (width, height)。
            source_node: 来源节点名称，用于追踪。
            metadata: 可选元数据。

        Returns:
            校验通过的 ROIData。

        Raises:
            ROIError: 未知类型或校验失败。
        """
        trace_id = self._tracer.begin(source_node, roi_type)

        try:
            converter = converter_registry.get(roi_type)
        except KeyError as e:
            self._tracer.error(trace_id, str(e))
            self._tracer.end(trace_id, "failed")
            raise ROIError(str(e), trace_id=trace_id, cause=e)

        roi = ROIData(
            roi_type=roi_type,
            data=data,
            image_size=image_size,
            trace_id=trace_id,
            metadata=metadata or {},
        )

        warnings = converter.validate(roi)
        for w in warnings:
            self._tracer.warn(trace_id, w)

        self._tracer.end(trace_id, "created")
        logger.info(f"[ROIManager] Created {roi}")
        return roi

    def to_mask(
        self,
        roi: ROIData,
        image_size: tuple[int, int] | None = None,
    ) -> np.ndarray:
        """将 ROI 转换为二值掩码。

        Args:
            roi: 源 ROI。
            image_size: 目标尺寸。若为 None 则使用 roi.image_size。

        Returns:
            bool 类型 numpy 数组。

        Raises:
            ROIError: 转换失败。
        """
        size = image_size or roi.image_size
        if size is None:
            raise ROIError(
                f"image_size required for {roi.roi_type} conversion",
                trace_id=roi.trace_id,
            )

        self._tracer.step(roi.trace_id, "to_mask", f"size={size}")

        try:
            converter = converter_registry.get(roi.roi_type)
            return converter.to_mask(roi, size)
        except Exception as e:
            self._tracer.error(roi.trace_id, f"to_mask failed: {e}", e)
            raise ROIError(
                f"Failed to convert {roi.roi_type} to mask: {e}",
                trace_id=roi.trace_id,
                cause=e,
            )

    def combine(
        self,
        rois: list[ROIData],
        image_size: tuple[int, int],
        mode: str = "union",
    ) -> np.ndarray:
        """合并多个 ROI。

        Args:
            rois: ROI 列表。
            image_size: 目标尺寸 (width, height)。
            mode: "union", "intersection", "difference"。

        Returns:
            bool 类型 numpy 数组。
        """
        for roi in rois:
            self._tracer.step(roi.trace_id, "combine", f"mode={mode}")
        return combine_rois(rois, image_size, mode)

    def apply_constraint(
        self,
        original: np.ndarray,
        processed: np.ndarray,
        rois: list[ROIData],
    ) -> np.ndarray:
        """将处理结果约束到 ROI 区域内。

        无 ROI 连接时直接返回 processed（向后兼容）。

        Args:
            original: 原始图像。
            processed: 处理后的图像。
            rois: ROI 列表（可为空）。

        Returns:
            约束后的图像。
        """
        if not rois:
            return processed

        for roi in rois:
            self._tracer.step(roi.trace_id, "apply_constraint")

        return apply_roi_constraint(original, processed, rois)

    def bbox(self, roi: ROIData) -> tuple[int, int, int, int]:
        """计算 ROI 边界框。"""
        converter = converter_registry.get(roi.roi_type)
        return converter.bbox(roi)

    def available_types(self) -> list[str]:
        """返回所有已注册的 ROI 类型。"""
        return converter_registry.all_types()
