# -*- coding: utf-8 -*-
"""图像画布 —— QGraphicsView 子类，负责图像显示和覆盖层管理。"""

import cv2
import numpy as np
from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import QImage, QPixmap, QPainter
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem

from .logger import get_logger

logger = get_logger(__name__)


def _cv2_to_qpixmap(img: np.ndarray) -> QPixmap:
    """将 numpy BGR/RGB 图像转换为 QPixmap。

    Args:
        img: BGR (3-channel) 或 RGB (3-channel) numpy array

    Returns:
        QPixmap
    """
    if img is None or img.size == 0:
        logger.warning("_cv2_to_qpixmap: 输入图像为空")
        return QPixmap()

    if len(img.shape) == 2:
        # 灰度图
        h, w = img.shape
        logger.debug("_cv2_to_qpixmap: 灰度 %dx%d", w, h)
        gray = np.ascontiguousarray(img)
        qimg = QImage(gray.data, w, h, w, QImage.Format_Grayscale8)
        pm = QPixmap.fromImage(qimg.copy())
        logger.debug("灰度 QPixmap 转换完成: isNull=%s", pm.isNull())
        return pm
    else:
        h, w, ch = img.shape
        if ch == 3:
            # BGR → RGB，确保连续内存
            rgb = np.ascontiguousarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            qimg = QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888)
            pm = QPixmap.fromImage(qimg.copy())
            logger.debug("_cv2_to_qpixmap: RGB %dx%d isNull=%s", w, h, pm.isNull())
            return pm
        elif ch == 4:
            rgba = np.ascontiguousarray(cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA))
            qimg = QImage(rgba.data, w, h, w * 4, QImage.Format_RGBA8888)
            pm = QPixmap.fromImage(qimg.copy())
            logger.debug("_cv2_to_qpixmap: RGBA %dx%d isNull=%s", w, h, pm.isNull())
            return pm
    logger.error("_cv2_to_qpixmap: 不支持的 shape=%s", img.shape)
    return QPixmap()


class ImageCanvas(QGraphicsView):
    """图像画布 —— 支持缩放、平移、覆盖层。"""

    # 信号 (保留给协调器使用)
    mouse_moved = Signal(QPointF)          # 鼠标移动 (scene 坐标)
    canvas_resized = Signal()              # 画布大小变化

    def __init__(self, parent=None):
        super().__init__(parent)

        # Scene 设置
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        # Pixmap item
        self._pixmap_item = QGraphicsPixmapItem()
        self._scene.addItem(self._pixmap_item)

        # 视图设置
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setOptimizationFlag(QGraphicsView.DontAdjustForAntialiasing, False)
        self.setViewportUpdateMode(QGraphicsView.SmartViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)

        # 样式
        self.setStyleSheet("background-color: #2c2c2c; border: none;")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 交互
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        # 控制器 (CanvasController 注入)
        self._controller = None

        # 图像数据 (供外部读取)
        self._img_bgr = None
        self._img_rgb = None
        self._img_gray = None
        self._img_h = 0
        self._img_w = 0
        self._is_grayscale = False

    # ------------------------------------------------------------------
    # 属性
    # ------------------------------------------------------------------
    @property
    def img_bgr(self):
        return self._img_bgr

    @property
    def img_rgb(self):
        return self._img_rgb

    @property
    def img_gray(self):
        return self._img_gray

    @property
    def img_width(self):
        return self._img_w

    @property
    def img_height(self):
        return self._img_h

    @property
    def is_grayscale(self):
        return self._is_grayscale

    @property
    def scene_obj(self):
        return self._scene

    @property
    def pixmap_item(self):
        return self._pixmap_item

    def set_image_data(self, bgr, rgb, gray, h, w, is_gray):
        """供 ImageManager 设置图像缓冲区 (避免私有属性写入)。"""
        self._img_bgr = bgr
        self._img_rgb = rgb
        self._img_gray = gray
        self._img_h = h
        self._img_w = w
        self._is_grayscale = is_gray

    # ------------------------------------------------------------------
    # 图像加载
    # ------------------------------------------------------------------
    def load_image(self, img_bgr: np.ndarray):
        """从 BGR numpy 数组加载图像。

        Args:
            img_bgr: OpenCV BGR 图像
        """
        if img_bgr is None:
            logger.warning("load_image: img_bgr 为 None，跳过")
            return

        logger.info("load_image 开始: shape=%s dtype=%s", img_bgr.shape, img_bgr.dtype)
        self._img_bgr = img_bgr
        self._img_h, self._img_w = img_bgr.shape[:2]

        # 检测灰度
        if len(img_bgr.shape) == 2:
            self._is_grayscale = True
            self._img_gray = img_bgr
            self._img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_GRAY2RGB)
        elif img_bgr.shape[2] == 4:
            self._is_grayscale = False
            self._img_gray = None
            self._img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGRA2RGB)
        else:
            b, g, r = img_bgr[:, :, 0], img_bgr[:, :, 1], img_bgr[:, :, 2]
            if np.array_equal(b, g) and np.array_equal(g, r):
                self._is_grayscale = True
                self._img_gray = b
            else:
                self._is_grayscale = False
                self._img_gray = None
            self._img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        logger.debug("灰度检测完成: is_grayscale=%s", self._is_grayscale)

        # 转换为 QPixmap 并显示
        # _cv2_to_qpixmap 期望 BGR 输入，这里用原始 BGR
        pixmap = _cv2_to_qpixmap(self._img_bgr)
        logger.debug("pixmap 转换: isNull=%s size=%sx%s",
                      pixmap.isNull(), pixmap.width(), pixmap.height())
        self._pixmap_item.setPixmap(pixmap)
        logger.debug("setPixmap 完成, item visible=%s, item scene=%s",
                      self._pixmap_item.isVisible(),
                      self._pixmap_item.scene() is not None)

        # 更新 scene rect
        self._scene.setSceneRect(QRectF(0, 0, self._img_w, self._img_h))
        logger.debug("setSceneRect: %dx%d", self._img_w, self._img_h)

        # 适应窗口
        self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)
        logger.debug("fitInView 完成, viewport size=%sx%s",
                      self.viewport().width(), self.viewport().height())

        # 强制刷新视口
        self.viewport().update()
        logger.info("load_image 完成: %dx%d", self._img_w, self._img_h)

    # ------------------------------------------------------------------
    # 控制器注入
    # ------------------------------------------------------------------
    def set_controller(self, controller):
        """注入 CanvasController。"""
        self._controller = controller

    # ------------------------------------------------------------------
    # 事件 → 委托给控制器
    # ------------------------------------------------------------------
    def mousePressEvent(self, event):
        if self._controller:
            sp = self.mapToScene(event.position().toPoint())
            self._controller.handle_press(sp, event.position().toPoint())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        sp = self.mapToScene(event.position().toPoint())
        if self._controller:
            if event.buttons() == Qt.NoButton:
                self._controller.handle_mouse_move(sp)
            else:
                self._controller.handle_move(sp, event.position().toPoint())
        self.mouse_moved.emit(sp)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._controller:
            sp = self.mapToScene(event.position().toPoint())
            self._controller.handle_release(sp, event.position().toPoint())
        super().mouseReleaseEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        # 窗口首次显示时，重新 fitInView 以确保图像正确显示
        if self._img_bgr is not None:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self.fitInView(
                self._scene.sceneRect(), Qt.KeepAspectRatio))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.canvas_resized.emit()
        if self._controller:
            self._controller.handle_resize()
        # 图像加载后，窗口大小变化时重新适应
        if self._img_bgr is not None:
            self.fitInView(self._scene.sceneRect(), Qt.KeepAspectRatio)

    def wheelEvent(self, event):
        if self._controller:
            sp = self.mapToScene(event.position().toPoint())
            self._controller.handle_wheel(sp, event.angleDelta().y())
        else:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.scale(factor, factor)

    def keyPressEvent(self, event):
        if self._controller:
            self._controller.handle_key(event.key())
        super().keyPressEvent(event)
