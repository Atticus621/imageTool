"""ROIData — 纯数据容器和 ROIError 异常类。

ROIData 是不可变的数据类，不包含任何转换逻辑。
所有操作通过 ROIManager 和 IROIConverter 进行。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ROIData:
    """统一的 ROI 数据载体。

    Attributes:
        roi_type: 类型标识符（如 "circle", "polygon", "mask"）。
                  字符串而非枚举，新增类型无需修改此类。
        data: 类型特定数据。
              circle: (cx, cy, radius)
              polygon: Nx2 array 或 list of (x, y)
              rectangle: (x, y, width, height)
              mask: numpy binary array
        image_size: 参考图像尺寸 (width, height)，可选。
        trace_id: 追踪标识，用于错误排查。由 ROITracer 自动分配。
        metadata: 可选元数据（来源节点、置信度等）。
    """

    roi_type: str
    data: Any
    image_size: tuple[int, int] | None = None
    trace_id: str = ""
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.trace_id:
            object.__setattr__(self, "trace_id", f"roi_{uuid.uuid4().hex[:8]}")

    def __repr__(self):
        size_str = f", size={self.image_size}" if self.image_size else ""
        return f"ROIData(type={self.roi_type!r}, trace={self.trace_id}{size_str})"


class ROIError(Exception):
    """ROI 操作异常，携带 trace_id 用于追踪。

    Attributes:
        trace_id: 关联的 ROI 追踪标识。
        cause: 原始异常（如果有）。
    """

    def __init__(
        self,
        message: str,
        trace_id: str = "",
        cause: Exception | None = None,
    ):
        self.trace_id = trace_id
        self.cause = cause
        prefix = f"[{trace_id}] " if trace_id else ""
        super().__init__(f"{prefix}{message}")
        if cause:
            self.__cause__ = cause
