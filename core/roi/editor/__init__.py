"""ROI Editor — 可视化 ROI 绘图编辑器模块。

叠加在 QGraphicsView viewport 上，支持在图像上绘制矩形、圆形、多边形。
形状数据存储在图像坐标系中，随图像缩放/平移自动同步。
"""

from core.roi.editor.overlay import ROIOverlay

__all__ = ["ROIOverlay"]
