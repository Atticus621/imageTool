"""CoordinateMapper — 坐标转换的单一真相源。

消除分散在 ImageSetWidget._img_to_screen、_map_overlay_to_image、
map_viewport_to_image 和 RulerOverlay._map_to_image、_img_to_screen
中的重复实现。

坐标系统：
    - viewport 坐标：QGraphicsView 的 viewport 内的像素坐标
    - scene 坐标：QGraphicsScene 内的坐标
    - image 坐标：图像像素坐标

由于图像放置在 scene 原点 (0, 0)，image 坐标 = scene 坐标。
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF
from PySide6.QtWidgets import QGraphicsView

from core.logger import logger


class CoordinateMapper:
    """坐标转换器，绑定到一个 QGraphicsView 实例。

    使用方式：
        mapper = CoordinateMapper(graphics_view)
        mapper.update_image_size(1920, 1080)

        # viewport → image
        img_pos = mapper.viewport_to_image(100, 200)

        # image → viewport
        vp_pos = mapper.image_to_viewport(500, 300)
    """

    def __init__(self, graphics_view: QGraphicsView):
        self._gv = graphics_view
        self._img_w: int = 0
        self._img_h: int = 0

    def update_image_size(self, w: int, h: int) -> None:
        """更新图像尺寸。切换图片时调用。"""
        self._img_w = w
        self._img_h = h

    def viewport_to_image(self, vp_x: float, vp_y: float) -> tuple[int, int] | None:
        """viewport 坐标 → 图像像素坐标。越界返回 None。

        Args:
            vp_x: viewport 内的 X 坐标
            vp_y: viewport 内的 Y 坐标

        Returns:
            (img_x, img_y) 或 None（越界时）
        """
        sp = self._gv.mapToScene(QPoint(int(vp_x), int(vp_y)))
        ix, iy = int(sp.x()), int(sp.y())
        if 0 <= ix < self._img_w and 0 <= iy < self._img_h:
            logger.debug(f"[CoordMapper] viewport({vp_x:.0f},{vp_y:.0f}) → image({ix},{iy})")
            return (ix, iy)
        logger.debug(f"[CoordMapper] viewport({vp_x:.0f},{vp_y:.0f}) → None (out of bounds)")
        return None

    def image_to_viewport(self, img_x: int, img_y: int) -> QPointF:
        """图像像素坐标 → viewport 坐标。

        图像在 scene 原点 (0, 0)，所以 image coords = scene coords。
        只需 mapFromScene (scene → viewport)。

        Args:
            img_x: 图像像素 X 坐标
            img_y: 图像像素 Y 坐标

        Returns:
            viewport 内的 QPointF 坐标
        """
        result = QPointF(self._gv.mapFromScene(QPointF(img_x, img_y)))
        logger.debug(f"[CoordMapper] image({img_x},{img_y}) → viewport({result.x():.0f},{result.y():.0f})")
        return result
