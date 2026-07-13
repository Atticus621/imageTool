"""IROIConverter — ROI 类型转换策略接口 + ConverterRegistry。

每种 ROI 类型实现 IROIConverter 接口并注册到 ConverterRegistry。
新增类型只需新建文件并注册，无需修改已有代码。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import numpy as np

from core.logger import logger

if TYPE_CHECKING:
    from .data import ROIData


class IROIConverter(ABC):
    """ROI 类型转换策略接口。

    每种 ROI 类型（circle, polygon, mask, ...）实现此接口，
    提供掩码转换、序列化、校验等能力。
    """

    @property
    @abstractmethod
    def type_id(self) -> str:
        """类型标识符，如 'circle', 'polygon'。"""
        ...

    @abstractmethod
    def to_mask(self, roi: ROIData, image_size: tuple[int, int]) -> np.ndarray:
        """将 ROI 转换为二值掩码。

        Args:
            roi: 源 ROI 数据。
            image_size: 目标尺寸 (width, height)。

        Returns:
            bool 类型的 numpy 数组，shape=(height, width)。
        """
        ...

    @abstractmethod
    def to_dict(self, roi: ROIData) -> dict:
        """将 ROI 序列化为 JSON 兼容字典。"""
        ...

    @abstractmethod
    def from_dict(self, data: dict) -> ROIData:
        """从字典反序列化为 ROIData。"""
        ...

    @abstractmethod
    def validate(self, roi: ROIData) -> list[str]:
        """校验 ROI 数据合法性。

        Returns:
            警告/错误消息列表，空列表表示通过。
        """
        ...

    def bbox(self, roi: ROIData) -> tuple[int, int, int, int]:
        """计算 ROI 的边界框 (x, y, width, height)。

        默认实现通过掩码计算。子类可覆盖以提供更高效的实现。
        """
        mask = self.to_mask(roi, roi.image_size or (1, 1))
        ys, xs = np.where(mask)
        if len(xs) == 0:
            return (0, 0, 0, 0)
        x, y = int(xs.min()), int(ys.min())
        w = int(xs.max()) - x + 1
        h = int(ys.max()) - y + 1
        return (x, y, w, h)


class ConverterRegistry:
    """ROI 转换器注册表。

    每种 ROI 类型的转换器在模块加载时自注册。
    """

    _converters: dict[str, IROIConverter] = {}

    @classmethod
    def register(cls, converter: IROIConverter) -> None:
        """注册一个转换器。同 type_id 重复注册会覆盖并记录警告。"""
        tid = converter.type_id
        if tid in cls._converters:
            logger.warning(f"[ConverterRegistry] Overwriting converter for '{tid}'")
        cls._converters[tid] = converter
        logger.info(f"[ConverterRegistry] Registered converter: {tid}")

    @classmethod
    def get(cls, type_id: str) -> IROIConverter:
        """获取指定类型的转换器。

        Raises:
            KeyError: 未注册的类型。
        """
        converter = cls._converters.get(type_id)
        if converter is None:
            available = list(cls._converters.keys())
            raise KeyError(
                f"Unknown ROI type '{type_id}'. Registered: {available}"
            )
        return converter

    @classmethod
    def has(cls, type_id: str) -> bool:
        """检查类型是否已注册。"""
        return type_id in cls._converters

    @classmethod
    def all_types(cls) -> list[str]:
        """返回所有已注册的类型标识符。"""
        return list(cls._converters.keys())

    @classmethod
    def clear(cls) -> None:
        """清空所有注册（仅用于测试）。"""
        cls._converters.clear()


# 全局单例
converter_registry = ConverterRegistry()
