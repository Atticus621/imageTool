# -*- coding: utf-8 -*-
"""图像管理器 —— 图像加载 + 颜色空间推断 + 显示更新 + 直方图。"""
import cv2
import numpy as np
from PySide6.QtCore import Qt, QObject, Signal

from ..image_canvas import _cv2_to_qpixmap
from ..logger import get_logger

logger = get_logger(__name__)


class ImageManager(QObject):
    """管理图像缓冲区和显示管线。"""

    image_loaded = Signal()
    display_updated = Signal()

    def __init__(self, canvas, histogram, parent=None):
        super().__init__(parent)
        self._canvas = canvas
        self._histogram = histogram
        self._pipeline = None  # 由外部注入

        self._color_space = "bgr"
        self._is_grayscale = False

    # ── 注入 ──
    def set_pipeline(self, pipeline):
        self._pipeline = pipeline

    # ── 属性 ──
    @property
    def color_space(self) -> str:
        return self._color_space

    @property
    def is_grayscale(self) -> bool:
        return self._is_grayscale

    # ── 图像加载 ──
    def load(self, path: str) -> bool:
        """从文件加载图像，返回是否成功。
        使用 np.fromfile + cv2.imdecode 以支持中文路径。
        """
        logger.info("load() 开始: %s", path)
        try:
            data = np.fromfile(path, dtype=np.uint8)
            logger.debug("文件读取完成: %d 字节", len(data))
            img = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
        except Exception as e:
            logger.error("load() 异常: %s", e, exc_info=True)
            return False
        if img is None:
            logger.error("load() imdecode 返回 None, path=%s", path)
            return False

        logger.debug("解码成功: shape=%s dtype=%s", img.shape, img.dtype)

        # 转 BGR
        if len(img.shape) == 2:
            self._is_grayscale = True
            bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            logger.info("灰度图 → BGR 转换完成")
        elif img.shape[2] == 4:
            self._is_grayscale = False
            bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            logger.info("BGRA → BGR 转换完成")
        else:
            bgr = img
            self._is_grayscale = (bgr[:, :, 0] == bgr[:, :, 1]).all() and \
                                 (bgr[:, :, 1] == bgr[:, :, 2]).all()
            logger.info("3通道图像, is_grayscale=%s", self._is_grayscale)

        self._color_space = "bgr"
        logger.debug("调用 canvas.load_image(), bgr shape=%s", bgr.shape)
        self._canvas.load_image(bgr)
        logger.info("canvas.load_image() 完成, pixmap isNull=%s",
                     self._canvas.pixmap_item.pixmap().isNull())

        # 更新直方图
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY) if not self._is_grayscale else bgr[:, :, 0]
        self._histogram.update_title(self._is_grayscale, self._color_space)
        self._histogram.update_histogram(rgb, gray, self._is_grayscale, self._color_space)
        logger.info("直方图已更新")

        self.image_loaded.emit()
        logger.info("load() 完成, image_loaded 信号已发射")
        return True

    # ── 显示更新 (流水线结果) ──
    def update_from_pipeline(self, img: np.ndarray):
        """将流水线输出图像转换为 RGB 并更新画布。"""
        logger.info("update_from_pipeline 开始, img shape=%s dtype=%s",
                     img.shape, img.dtype)
        if len(img.shape) == 2:
            cs = "gray"
        else:
            cs = self._infer_color_space()
        self._color_space = cs
        logger.debug("推断颜色空间: %s", cs)

        # 颜色空间 → RGB
        if cs == "gray" or len(img.shape) == 2:
            if len(img.shape) == 2:
                disp = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
                self._is_grayscale = True
                gray = img
            else:
                disp = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                self._is_grayscale = False
                gray = None
            bgr = img if len(img.shape) == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif cs == "hsv":
            bgr = cv2.cvtColor(img, cv2.COLOR_HSV2BGR)
            disp = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            self._is_grayscale = False
            gray = None
        elif cs == "lab":
            bgr = cv2.cvtColor(img, cv2.COLOR_LAB2BGR)
            disp = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            self._is_grayscale = False
            gray = None
        elif cs == "rgb":
            disp = img.copy()
            bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            self._is_grayscale = False
            gray = None
        else:
            disp = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            bgr = img
            self._is_grayscale = False
            gray = None

        h, w = img.shape[:2]
        self._canvas.set_image_data(bgr, disp, gray, h, w, self._is_grayscale)

        pixmap = _cv2_to_qpixmap(bgr)  # _cv2_to_qpixmap 期望 BGR 输入
        logger.debug("pixmap 转换完成: isNull=%s size=%sx%s",
                      pixmap.isNull(), pixmap.width(), pixmap.height())
        self._canvas.pixmap_item.setPixmap(pixmap)
        self._canvas.scene_obj.setSceneRect(0, 0, w, h)
        self._canvas.fitInView(self._canvas.scene_obj.sceneRect(), Qt.KeepAspectRatio)

        self._histogram.update_title(self._is_grayscale, self._color_space)
        if disp is not None:
            self._histogram.update_histogram(
                disp, gray, self._is_grayscale, self._color_space)
            logger.debug("直方图已更新")

        self.display_updated.emit()
        logger.info("update_from_pipeline 完成: %dx%d cs=%s", w, h, cs)

    # ── 像素读取 (供 StatusManager) ──
    def get_pixel(self, x: int, y: int) -> str:
        """返回格式化颜色字符串。"""
        if not (0 <= x < self._canvas.img_width and 0 <= y < self._canvas.img_height):
            return "--"
        if self._is_grayscale:
            g = self._canvas.img_gray
            return f"Gray: {int(g[y, x])}" if g is not None else "Gray: --"
        elif self._color_space == "hsv":
            hsv = self._canvas.img_bgr[y, x]
            return f"H:{int(hsv[0])} S:{int(hsv[1])} V:{int(hsv[2])}"
        elif self._color_space == "lab":
            lab = self._canvas.img_bgr[y, x]
            return f"L:{int(lab[0])} A:{int(lab[1])} B:{int(lab[2])}"
        else:
            r, g, b = self._canvas.img_rgb[y, x]
            return f"R:{r} G:{g} B:{b}"

    # ── 颜色空间推断 ──
    def _infer_color_space(self) -> str:
        # convert_color 现在统一输出 BGR，所以始终返回 "bgr"
        return "bgr"
