# -*- coding: utf-8 -*-
"""标定管理器 —— XML 标定文件加载 + 坐标转换。"""
import json
import os

from PySide6.QtCore import QObject, Signal

from algorithm.calibration import Calibrator


class CalibrationManager(QObject):
    """管理标定文件的加载和坐标转换。"""

    loaded = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._calibrator = Calibrator()
        self._loaded = False

    # ── 属性 ──
    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def calibrator(self) -> Calibrator:
        return self._calibrator

    # ── 加载 ──
    def load_from_config(self) -> bool:
        """从 config.json 加载标定文件。"""
        # managers/ → qt_app/ → imageTools/ → .. (project root)
        config_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__)))))
        config_path = os.path.join(config_dir, "config.json")
        if not os.path.exists(config_path):
            return False

        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        calib_path = config.get("calibration_file", "")
        if not calib_path or not os.path.exists(calib_path):
            return False

        if self._calibrator.load_from_xml(calib_path):
            self._loaded = True
            self.loaded.emit(True)
            return True
        return False

    # ── 坐标转换 ──
    def img_to_phys(self, xy):
        """图像坐标 → 物理坐标 (mm)。"""
        if not self._loaded:
            return None
        return self._calibrator.img_to_phys(xy)

    def precision(self) -> float:
        """像素精度 (mm/px)。"""
        return self._calibrator.info.get("PixelPrecision", 0.0)
