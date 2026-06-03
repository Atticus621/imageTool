# -*- coding: utf-8 -*-
"""图像查看器 —— 薄编排层：创建 Manager + Widget，连接信号。"""
import os
import sys
import json

from PySide6.QtCore import QObject, Qt

from imageTools.image_processor import ImageProcessor

from .logger import get_logger
from .main_window import MainWindow
from .image_canvas import ImageCanvas
from .canvas_controller import CanvasController
from .histogram_widget import HistogramWidget
from .roi_panel import ROIPanel
from .pipeline_panel import PipelinePanel

from .managers import (
    CalibrationManager, ImageManager, ViewportManager,
    RulerManager, StatusManager, ROIManager,
    PipelineManager, ProcessingManager,
)

logger = get_logger(__name__)


class ImageViewer(QObject):
    """图像查看器 —— 创建所有组件并连接信号。"""

    def __init__(self):
        super().__init__()
        logger.info("ImageViewer.__init__ 开始")

        # ── Widget 层 ──
        self._window = MainWindow()
        self._canvas = ImageCanvas()
        self._window.set_canvas(self._canvas)
        self._controller = CanvasController(self._canvas)
        logger.debug("Widget 层创建完成: MainWindow, ImageCanvas, CanvasController")

        self._histogram = HistogramWidget()
        self._roi_panel = ROIPanel()
        self._pipeline_panel = PipelinePanel()
        right_inner, right_layout = self._window.right_panel()
        right_layout.addWidget(self._histogram)
        right_layout.addWidget(self._roi_panel)
        right_layout.addWidget(self._pipeline_panel)
        right_layout.addStretch()

        # ── Manager 层 ──
        self._calib = CalibrationManager()
        self._img = ImageManager(self._canvas, self._histogram)
        self._viewport = ViewportManager(self._canvas)
        self._ruler = RulerManager(self._canvas, self._calib)
        self._status = StatusManager(self._window, self._img, self._calib, self._ruler)
        self._roi = ROIManager(self._canvas, self._roi_panel)
        self._pipeline = PipelineManager(ImageProcessor(), self._pipeline_panel)
        self._processing = ProcessingManager(
            self._window, self._pipeline, self._roi, self._img)
        logger.debug("Manager 层创建完成")

        # 注入依赖
        self._img.set_pipeline(self._pipeline.pipeline)
        logger.debug("依赖注入完成 (pipeline → ImageManager)")

        # ── 信号连接 ──
        self._wire_signals()

        # ── 启动 ──
        self._calib.load_from_config()
        if self._calib.is_loaded:
            p = self._calib.precision()
            self._window.set_status(f"标定已加载 ({p:.4f} mm/px)")
            logger.info("标定已加载: precision=%.4f mm/px", p)

        logger.info("ImageViewer.__init__ 完成")

    # ══════════════════════════════════════════════════════════════════
    # 信号连接 (全部胶水代码)
    # ══════════════════════════════════════════════════════════════════
    def _wire_signals(self):
        logger.debug("开始连接信号...")
        w, ctrl = self._window, self._controller
        rp, pp = self._roi_panel, self._pipeline_panel

        # ── 工具栏 → Manager ──
        w.open_requested.connect(self._on_open)
        w.open_image_shortcut.connect(self._open_image_dialog)
        w.fit_to_window_requested.connect(self._viewport.fit_to_window)
        w.tool_change_requested.connect(ctrl.set_tool)
        w.export_image_requested.connect(self._export_image)

        # ── 控制器 → Widget ──
        ctrl.tool_changed.connect(w.highlight_tool_button)

        # ── 控制器 → Manager ──
        ctrl.panned.connect(self._viewport.pan)
        ctrl.zoomed.connect(self._viewport.zoom)
        ctrl.ruler_started.connect(self._ruler.on_start)
        ctrl.ruler_moved.connect(self._ruler.on_move)
        ctrl.ruler_ended.connect(self._ruler.on_end)
        ctrl.roi_started.connect(self._roi.on_draw_start)
        ctrl.roi_moved.connect(self._roi.on_draw_move)
        ctrl.roi_ended.connect(self._roi.on_draw_end)
        ctrl.roi_rotate_requested.connect(self._roi.on_rotate_key)
        ctrl.roi_rotate_absolute.connect(self._roi.on_rotate_absolute)
        ctrl.mouse_moved.connect(self._status.on_mouse_move)

        # ── 面板 → Manager ──
        rp.roi_list_selection_changed.connect(self._roi.on_selection_changed)
        rp.roi_sector_changed.connect(self._roi.on_param_changed)
        rp.clear_rois_requested.connect(self._roi.clear_all)
        pp.add_processing_requested.connect(lambda: self._processing.open())
        pp.insert_requested.connect(
            lambda idx: self._processing.open(insert_position=idx + 1))
        pp.add_to_folder_requested.connect(
            lambda idx: self._processing.open(inside_folder=idx))
        pp.paste_requested.connect(self._pipeline.paste_steps)
        pp.step_edit_requested.connect(self._on_edit_step)
        pp.toggle_requested.connect(
            lambda idx: self._pipeline.toggle(idx))
        pp.toggle_multi_requested.connect(
            lambda indices: self._pipeline.toggle_multi(indices))
        pp.remove_requested.connect(
            lambda indices: self._pipeline.remove_multi(indices))
        pp.copy_requested.connect(
            lambda indices: self._pipeline.copy_steps(indices))
        pp.cut_requested.connect(
            lambda indices: self._pipeline.cut_steps(indices))
        pp.clear_requested.connect(self._pipeline.clear)
        pp.order_changed.connect(
            lambda args: self._pipeline.reorder(*args))
        pp.create_folder_requested.connect(self._pipeline.create_folder)
        pp.create_subfolder_requested.connect(
            lambda idx, name: self._pipeline.create_subfolder(idx, name))
        pp.rename_folder_requested.connect(
            lambda idx, name: self._pipeline.rename_folder(idx, name))
        pp.delete_folder_requested.connect(self._pipeline.delete_folder)
        pp.export_pipeline_requested.connect(lambda: self._pipeline.export_json(self._window))
        pp.import_pipeline_requested.connect(lambda: self._pipeline.import_json(self._window))
        pp.open_image_requested.connect(self._open_image_dialog)

        # ── Manager 间 ──
        self._pipeline.applied.connect(self._img.update_from_pipeline)
        self._img.display_updated.connect(self._roi._redraw)
        self._processing.step_added.connect(self._pipeline.add_step)
        self._calib.loaded.connect(
            lambda ok: self._window.set_status("标定已加载") if ok else None)

        logger.debug("信号连接完成 (共 %d 条)", 27)

    # ══════════════════════════════════════════════════════════════════
    # 需要跨 Manager 协调的方法
    # ══════════════════════════════════════════════════════════════════
    _CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".image_tool_config.json")

    def _on_open(self, path: str):
        """加载图像 → 初始化流水线 → 清除状态。"""
        logger.info("_on_open 收到请求: %s", path)
        if not path:
            logger.warning("_on_open: 路径为空，跳过")
            return
        if not self._img.load(path):
            logger.error("_on_open: 加载失败 path=%s", path)
            self._window.show_error("错误", f"无法加载图片:\n{path}")
            return

        self._pipeline.set_original(self._img._canvas.img_bgr)
        self._ruler.clear()
        self._roi.clear_all()

        h, w = self._img._canvas.img_height, self._img._canvas.img_width
        img_type = "灰度" if self._img.is_grayscale else "彩色"
        calib = " | 标定已加载" if self._calib.is_loaded else ""
        self._window.setWindowTitle(f"图像查看器 — {path} ({img_type})")
        self._window.set_status(
            f"已加载: {path}  |  尺寸: {w}×{h}  |  {img_type}图像{calib}")
        logger.info("_on_open 完成: %dx%d %s", w, h, img_type)

        # 保存路径
        self._save_last_image_path(path)

    def _save_last_image_path(self, path: str):
        try:
            with open(self._CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump({"last_image": path}, f)
        except Exception:
            pass

    def _load_last_image_path(self) -> str:
        try:
            if os.path.exists(self._CONFIG_PATH):
                with open(self._CONFIG_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                path = data.get("last_image", "")
                if path and os.path.exists(path):
                    return path
        except Exception:
            pass
        return ""

    def _open_image_dialog(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self._window, "选择图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp);;所有文件 (*.*)")
        if path:
            self._on_open(path)

    def _on_edit_step(self, step_idx: int):
        step = self._pipeline.edit_step(step_idx)
        if step:
            self._processing.open(
                edit_mode=True, edit_step_idx=step_idx,
                edit_func_name=step.func_name, edit_params=step.params)

    def _export_image(self):
        if self._img._canvas.img_bgr is None:
            return
        from PySide6.QtWidgets import QFileDialog
        import cv2
        path, _ = QFileDialog.getSaveFileName(
            self._window, "导出图片", "", "PNG (*.png);;JPEG (*.jpg);;BMP (*.bmp)")
        if path:
            cv2.imwrite(path, self._img._canvas.img_bgr)
            self._window.set_status(f"图像已导出: {path}")

    # ══════════════════════════════════════════════════════════════════
    # 入口
    # ══════════════════════════════════════════════════════════════════
    def run(self, image_path=None):
        logger.info("run() 开始, image_path=%s", image_path)
        self._window.show()
        if image_path:
            self._on_open(image_path)
        else:
            last = self._load_last_image_path()
            if last:
                logger.info("run() 自动加载上次图片: %s", last)
                self._on_open(last)
