"""core.roi — ROI 子系统。

提供统一的 ROI 数据模型、类型转换、序列化和错误追踪。

公共 API：
    ROIData        — ROI 数据容器
    ROIError       — ROI 操作异常
    ROIManager     — ROI 操作统一入口（单例）
    ROITracer      — ROI 数据流追踪器（单例）
    ROISerializer  — JSON + Base64 序列化

使用示例：
    from core.roi import ROIData, ROIManager

    roi_mgr = ROIManager.instance()
    roi = roi_mgr.create("circle", (100, 200, 50), (1920, 1080))
    mask = roi_mgr.to_mask(roi)
"""

# 触发转换器自注册
from . import converters  # noqa: F401

from .data import ROIData, ROIError
from .manager import ROIManager
from .ops import apply_roi_constraint, combine_rois
from .serializer import ROISerializer
from .tracer import ROITracer

__all__ = [
    "ROIData",
    "ROIError",
    "ROIManager",
    "ROITracer",
    "ROISerializer",
    "combine_rois",
    "apply_roi_constraint",
]
