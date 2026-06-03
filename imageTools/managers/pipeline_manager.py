# -*- coding: utf-8 -*-
"""流水线管理器 —— 步骤 CRUD + 执行 + 导入导出。"""
import cv2
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QFileDialog

from imageTools.processing_pipeline import ProcessingPipeline
from ..logger import get_logger

logger = get_logger(__name__)


class PipelineManager(QObject):
    """管理处理流水线的所有操作。"""

    changed = Signal()               # 流水线步骤变更
    applied = Signal(object)         # 流水线执行完成 → 结果图像

    def __init__(self, processor, panel, parent=None):
        super().__init__(parent)
        self._processor = processor
        self._panel = panel
        self._pipeline = ProcessingPipeline()

    # ── 属性 ──
    @property
    def pipeline(self):
        return self._pipeline

    @property
    def step_count(self) -> int:
        return self._pipeline.step_count

    def set_original(self, img):
        logger.info("set_original: shape=%s", img.shape if img is not None else None)
        self._pipeline.clear()
        self._pipeline.set_original_image(img)
        self._panel.update_display(
            self._pipeline.get_display_list(), self._pipeline._items)
        logger.debug("set_original 完成")

    # ── CRUD ──
    def add_step(self, func_name: str, params: dict, position: int = -1, inside_folder: int = -1):
        """添加处理步骤。

        Args:
            position: 插入到 _items 指定位置（用于"插入"）
            inside_folder: 在文件夹内部添加（用于"添加流程"）
        """
        if inside_folder >= 0:
            self._pipeline.add_step_inside_folder(inside_folder, func_name, params)
        elif position >= 0:
            depth = self._pipeline._compute_depth_at(position)
            self._pipeline.insert_step(position, func_name, params, depth=depth)
        else:
            self._pipeline.add_step(func_name, params)
        self._apply()

    def edit_step(self, step_idx: int):
        item = self._pipeline.get_step(step_idx)
        if item and item.type == "step" and item.step:
            return item.step
        return None

    def update_step(self, step_idx: int, func_name: str, params: dict):
        self._pipeline.update_step(step_idx, func_name, params)
        self._apply()

    def move_up(self, step_idx: int):
        if step_idx > 0:
            self._pipeline.move_up(step_idx)
            self._apply()

    def move_down(self, step_idx: int):
        if step_idx < self._pipeline.item_count - 1:
            self._pipeline.move_down(step_idx)
            self._apply()

    def toggle(self, step_idx: int):
        self._pipeline.toggle_step(step_idx)
        self._apply()

    def remove(self, step_idx: int):
        self._pipeline.remove_step(step_idx)
        self._apply()

    def insert_at(self, index: int, func_name: str, params: dict):
        """在指定位置插入步骤并刷新。"""
        self._pipeline.insert_step(index, func_name, params)
        self._apply()

    def remove_multi(self, indices: list):
        """按索引从大到小批量删除。"""
        for idx in sorted(indices, reverse=True):
            self._pipeline.remove_step(idx)
        self._apply()

    def toggle_multi(self, indices: list):
        """批量切换启用/禁用。"""
        for idx in indices:
            self._pipeline.toggle_step(idx)
        self._apply()

    def copy_steps(self, indices: list):
        """复制多个步骤到剪贴板（跳过文件夹）。"""
        clips = []
        for idx in sorted(indices):
            item = self._pipeline.get_step(idx)
            if item and item.type == "step" and item.step:
                clips.append((item.step.func_name, item.step.params.copy()))
        self._panel.set_clipboard(clips)

    def cut_steps(self, indices: list):
        """剪切步骤到剪贴板（复制 + 删除）。"""
        self.copy_steps(indices)
        self.remove_multi(indices)

    def paste_steps(self):
        """从剪贴板粘贴步骤，追加到末尾。"""
        clips = self._panel._clipboard
        if not clips:
            return
        for func_name, params in clips:
            self._pipeline.add_step(func_name, params)
        self._apply()

    def move_steps(self, from_row: int, to_row: int, count: int = 1):
        """拖拽移动步骤。

        Args:
            from_row: 起始行（不含原图，即 pipeline 索引）
            to_row: 目标行
            count: 移动步骤数量
        """
        for i in range(count):
            src = from_row if to_row > from_row else from_row + i
            dst = to_row if to_row > from_row else to_row
            self._pipeline.move_step(src, dst)
        self._apply()

    def reorder(self, src_idx: int, dst_idx: int, count: int = 1):
        """拖拽重排序 (由面板 order_changed 信号触发)。"""
        items = self._pipeline._items
        moving = items[src_idx:src_idx + count]
        del items[src_idx:src_idx + count]
        adjusted = dst_idx if dst_idx <= src_idx else dst_idx - count
        for i, item in enumerate(moving):
            items.insert(adjusted + i, item)
        self._refresh_folder_depth()
        self._apply()

    def _refresh_folder_depth(self):
        """重新计算所有项目的 folder_depth 属性。"""
        depth = 0
        for item in self._pipeline._items:
            if item.type == "folder":
                item.folder_depth = depth
                depth += 1
            else:
                item.folder_depth = depth

    def clear(self):
        self._pipeline.clear()
        self._apply()

    # ── 文件夹操作 ──
    def create_folder(self, name: str):
        """创建文件夹。"""
        if self._pipeline.get_original_image() is None:
            return
        self._pipeline.add_folder(name)
        self._apply()

    def create_subfolder(self, parent_idx: int, name: str):
        """在文件夹内创建子文件夹。"""
        if self._pipeline.get_original_image() is None:
            return
        parent = self._pipeline.get_step(parent_idx)
        if not parent or parent.type != "folder":
            return
        self._pipeline.add_folder_inside_folder(parent_idx, name)
        self._apply()

    def rename_folder(self, idx: int, new_name: str):
        """重命名文件夹。"""
        item = self._pipeline.get_step(idx)
        if item and item.type == "folder":
            item.folder_name = new_name
            self._apply()

    def delete_folder(self, idx: int):
        """删除文件夹（不删除其中的步骤）。"""
        self._pipeline.delete_folder(idx)
        self._apply()

    def toggle_folder(self, idx: int):
        """切换文件夹展开/折叠状态。"""
        item = self._pipeline.get_step(idx)
        if item and item.type == "folder":
            item.toggle_expanded()
            self._panel.update_display(
                self._pipeline.get_display_list(), self._pipeline._items)

    def apply_to_step(self, step_idx: int):
        """执行到指定步骤（供编辑预览使用）。"""
        return self._pipeline.apply_to_step(self._processor, step_idx)

    def _apply(self):
        step_count = self._pipeline.step_count
        logger.info("_apply: 执行流水线, %d 个步骤", step_count)
        result = self._pipeline.apply_all(self._processor)
        self._panel.update_display(
            self._pipeline.get_display_list(), self._pipeline._items)
        self.changed.emit()
        if result is not None:
            logger.info("_apply: 流水线结果 shape=%s, 发射 applied 信号", result.shape)
            self.applied.emit(result)
        else:
            logger.warning("_apply: 流水线结果为 None (无原始图像或执行失败)")

    def exec_function(self, func_name: str, img, **params):
        """执行单个处理方法（供预览使用）。"""
        func = getattr(self._processor, func_name, None)
        if func:
            return func(img, **params)
        return img

    # ── 导入导出 ──
    def export_json(self, parent):
        if self._pipeline.item_count == 0:
            return
        path, _ = QFileDialog.getSaveFileName(parent, "导出流水线", "", "JSON (*.json)")
        if path:
            self._pipeline.export_to_json(path)

    def import_json(self, parent):
        path, _ = QFileDialog.getOpenFileName(parent, "导入流水线", "", "JSON (*.json)")
        if path and self._pipeline.import_from_json(path):
            self._apply()
