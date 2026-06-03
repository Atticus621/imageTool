# -*- coding: utf-8 -*-
"""直方图控件 —— QWidget paintEvent 绘制颜色分布曲线。"""

import cv2
import numpy as np
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QPainterPath
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout

from .logger import get_logger

logger = get_logger(__name__)


class HistogramWidget(QWidget):
    """用 QPainter 绘制 R/G/B 或 H/S/V 或 L/A/B 直方图。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(260, 200)
        self.setMaximumHeight(220)
        self.setStyleSheet("background: white; border: 1px solid #bdc3c7;")

        self._title = QLabel("RGB 颜色分布")
        self._title.setStyleSheet(
            "font-family: 'Microsoft YaHei'; font-size: 12px; font-weight: bold;"
            "border: none; padding: 2px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._title, alignment=Qt.AlignCenter)

    def update_title(self, is_grayscale: bool, color_space: str = "bgr"):
        cs = color_space.lower()
        if is_grayscale:
            self._title.setText("灰度分布")
        elif cs == "hsv":
            self._title.setText("HSV 颜色分布")
        elif cs == "lab":
            self._title.setText("LAB 颜色分布")
        else:
            self._title.setText("RGB 颜色分布")

    def update_histogram(self, img_rgb: np.ndarray, img_gray: np.ndarray,
                         is_grayscale: bool, color_space: str = "bgr"):
        logger.info("update_histogram: img_rgb shape=%s, is_grayscale=%s, cs=%s",
                     img_rgb.shape if img_rgb is not None else None,
                     is_grayscale, color_space)
        self._data = (img_rgb, img_gray, is_grayscale, color_space)
        self.update()
        logger.debug("update_histogram: 已触发 repaint")

    def paintEvent(self, event):
        super().paintEvent(event)
        if not hasattr(self, '_data') or self._data is None:
            logger.debug("paintEvent: 无 _data，跳过绘制")
            return

        img_rgb, img_gray, is_grayscale, color_space = self._data
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        margin_l, margin_r, margin_t, margin_b = 35, 10, 20, 25
        plot_w = w - margin_l - margin_r
        plot_h = h - margin_t - margin_b
        if plot_w <= 0 or plot_h <= 0:
            painter.end()
            return

        # 计算直方图
        channels = self._compute_channels(img_rgb, img_gray, is_grayscale, color_space)
        if not channels:
            painter.end()
            return

        # 坐标轴
        pen_axis = QPen(QColor("#7f8c8d"), 1)
        painter.setPen(pen_axis)
        painter.drawLine(margin_l, margin_t, margin_l, h - margin_b)
        painter.drawLine(margin_l, h - margin_b, w - margin_r, h - margin_b)

        # X 刻度
        font_tick = QFont("Arial", 7)
        painter.setFont(font_tick)
        for val in [0, 64, 128, 192, 255]:
            x = margin_l + val / 255.0 * plot_w
            painter.drawLine(int(x), h - margin_b, int(x), h - margin_b + 4)
            painter.drawText(int(x) - 10, h - margin_b + 16, str(val))

        # 曲线
        for hist_arr, color_hex in channels:
            pen = QPen(QColor(color_hex), 1.5)
            painter.setPen(pen)
            max_val = hist_arr.max()
            if max_val <= 0:
                continue
            path = QPainterPath()
            first = True
            for i in range(len(hist_arr)):
                x = margin_l + i / (len(hist_arr) - 1) * plot_w if len(hist_arr) > 1 else margin_l
                y = (h - margin_b) - (hist_arr[i] / max_val) * plot_h
                if first:
                    path.moveTo(x, y)
                    first = False
                else:
                    path.lineTo(x, y)
            painter.drawPath(path)

        # 底部标签
        cs = color_space.lower()
        if cs == "hsv":
            x_label = "H(0-179) / S,V(0-255)"
        elif cs == "lab":
            x_label = "L(0-255) / A,B(0-255)"
        else:
            x_label = "像素值 (0-255)"
        painter.setPen(QColor("#7f8c8d"))
        painter.drawText(int(w / 2 - 40), h - 4, x_label)

        painter.end()

    def _compute_channels(self, img_rgb, img_gray, is_grayscale, cs):
        channels = []
        try:
            if is_grayscale:
                hist = cv2.calcHist([img_gray], [0], None, [256], [0, 256]).flatten()
                if hist.max() > 0:
                    channels = [(hist, "#555555")]
            elif cs == "hsv":
                bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
                hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
                hist_h = cv2.calcHist([hsv], [0], None, [256], [0, 256]).flatten()
                hist_s = cv2.calcHist([hsv], [1], None, [256], [0, 256]).flatten()
                hist_v = cv2.calcHist([hsv], [2], None, [256], [0, 256]).flatten()
                if max(hist_h.max(), hist_s.max(), hist_v.max()) > 0:
                    channels = [(hist_h, "#e74c3c"), (hist_s, "#2ecc71"), (hist_v, "#3498db")]
            elif cs == "lab":
                bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
                lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
                hist_l = cv2.calcHist([lab], [0], None, [256], [0, 256]).flatten()
                hist_a = cv2.calcHist([lab], [1], None, [256], [0, 256]).flatten()
                hist_b = cv2.calcHist([lab], [2], None, [256], [0, 256]).flatten()
                if max(hist_l.max(), hist_a.max(), hist_b.max()) > 0:
                    channels = [(hist_l, "#e74c3c"), (hist_a, "#2ecc71"), (hist_b, "#3498db")]
            else:
                hist_r = cv2.calcHist([img_rgb], [0], None, [256], [0, 256]).flatten()
                hist_g = cv2.calcHist([img_rgb], [1], None, [256], [0, 256]).flatten()
                hist_b = cv2.calcHist([img_rgb], [2], None, [256], [0, 256]).flatten()
                if max(hist_r.max(), hist_g.max(), hist_b.max()) > 0:
                    channels = [(hist_r, "#e74c3c"), (hist_g, "#2ecc71"), (hist_b, "#3498db")]
        except Exception:
            pass
        return channels
