# -*- coding: utf-8 -*-
"""处理对话框管理器 —— 打开/管理 ProcessingDialog 生命周期。"""
from PySide6.QtCore import QObject, Signal

from imageTools.image_processor import ImageProcessor, PROCESS_PRESETS, PARAM_RANGES
from ..processing_dialog import ProcessingDialog


class ProcessingManager(QObject):
    """管理处理对话框的打开和回调。"""

    step_added = Signal(str, dict)  # (func_name, params)

    def __init__(self, window, pipeline_manager, roi_manager, image_manager, parent=None):
        super().__init__(parent)
        self._window = window
        self._pipeline = pipeline_manager
        self._roi = roi_manager
        self._img = image_manager
        self._dialog = None

    def open(self, edit_mode=False, edit_step_idx=-1,
             edit_func_name=None, edit_params=None,
             insert_position=-1, inside_folder=-1):
        """打开处理对话框。

        Args:
            insert_position: >= 0 时在指定位置插入（"插入"操作）
            inside_folder: >= 0 时在文件夹内添加（"添加流程"操作）
        """
        if self._img._canvas.img_bgr is None:
            self._window.show_warning("提示", "请先打开一张图片")
            return

        pm = self._pipeline
        rm = self._roi
        im = self._img
        panel = pm._panel

        def preview_cb(func_name, params):
            result = pm.pipeline.apply_all(pm._processor)
            if result is None:
                result = pm.pipeline.get_original_image()
            params_copy = dict(params)
            result, params_copy = rm.apply_mask(result, params_copy)
            r = pm.exec_function(func_name, result, **params_copy)
            if r is not None:
                im.update_from_pipeline(r)

        def close_cb():
            panel.remove_preview()
            pm._apply()

        def add_cb(fn, p):
            panel.remove_preview()
            if inside_folder >= 0:
                pm.add_step(fn, p, inside_folder=inside_folder)
            else:
                pm.add_step(fn, p, position=insert_position)

        dlg = ProcessingDialog(
            PROCESS_PRESETS, PARAM_RANGES,
            preview_callback=preview_cb, close_callback=close_cb,
            edit_mode=edit_mode, edit_func_name=edit_func_name,
            edit_params=edit_params,
            roi_regions=rm.regions,
            adaptive_callback=self._on_adaptive,
            kmeans_callback=self._on_kmeans,
            parent=self._window)

        if not edit_mode:
            dlg.add_requested.connect(add_cb)
            dlg.selection_changed.connect(
                lambda _disp, func, params: panel.update_preview_text(
                    f"{func} ({', '.join(f'{k}={v}' for k, v in params.items() if v != 0 and not k.startswith('_'))})"
                ))
        if edit_mode:
            def edit_done(fn, p):
                panel.remove_preview()
                pm.update_step(edit_step_idx, fn, p)
            dlg.set_edit_complete_callback(edit_done)

        self._dialog = dlg

        # 添加模式: 显示预览虚文字
        if not edit_mode:
            if inside_folder >= 0:
                # 在文件夹内添加：预览在文件夹最后一个子项之后
                after_idx = pm.pipeline._find_folder_end(inside_folder) - 1
            elif insert_position >= 0:
                # 在指定位置插入：预览在前一项之后
                after_idx = insert_position - 2
            else:
                # 末尾：预览在最后一项之后
                after_idx = pm.pipeline.item_count - 1
            panel.show_preview("...", after_idx)

        dlg.show()

    def _on_adaptive(self, func_name, params, channel):
        """自适应阈值回调（Otsu 单通道）。"""
        result = self._pipeline.pipeline.apply_all(self._pipeline._processor)
        if result is None:
            result = self._pipeline.pipeline.get_original_image()
        cs = params.get("color_space", "hsv")
        return ImageProcessor.compute_adaptive_threshold(result, cs, channel=channel)

    def _on_kmeans(self, func_name, params):
        """K-means 自动分割回调（所有通道）。"""
        result = self._pipeline.pipeline.apply_all(self._pipeline._processor)
        if result is None:
            result = self._pipeline.pipeline.get_original_image()
        cs = params.get("color_space", "hsv")
        return ImageProcessor.compute_kmeans_threshold(result, cs)
