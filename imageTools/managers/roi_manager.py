# -*- coding: utf-8 -*-
"""ROI 管理器 —— 区域创建、编辑、旋转、渲染、掩膜应用。"""
import math
import cv2
import numpy as np
from PySide6.QtCore import QObject, Signal, QPointF
from ..canvas_items import ROIPreviewItem, ROIRectItem, ROICircleItem


class ROIManager(QObject):
    """管理所有 ROI 区域的全生命周期。"""

    ROI_COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#e67e22",
                  "#9b59b6", "#1abc9c", "#f39c12", "#e91e63"]

    changed = Signal()  # ROI 列表变化

    def __init__(self, canvas, panel, parent=None):
        super().__init__(parent)
        self._canvas = canvas
        self._panel = panel

        self._regions = []
        self._next_number = 1
        self._selected_index = -1
        self._shape_mode = "rect"
        self._preview = None

    # ── 属性 ──
    @property
    def regions(self) -> list:
        return self._regions

    @property
    def selected_index(self) -> int:
        return self._selected_index

    # ══════════════════════════════════════════════════════════════════
    # 创建
    # ══════════════════════════════════════════════════════════════════
    def on_draw_start(self, sp: QPointF):
        self._preview = ROIPreviewItem(sp, sp, self._shape_mode)
        self._canvas.scene_obj.addItem(self._preview)

    def on_draw_move(self, sp: QPointF):
        if self._preview:
            self._preview.update_end(sp)

    def on_draw_end(self, sp: QPointF):
        if self._preview is None:
            return
        start = QPointF(self._preview._start)
        self._canvas.scene_obj.removeItem(self._preview)
        self._preview = None

        if self._shape_mode == "rect":
            x0, y0 = min(start.x(), sp.x()), min(start.y(), sp.y())
            w, h = abs(sp.x() - start.x()), abs(sp.y() - start.y())
            if w < 2 or h < 2:
                return
            coords = (x0, y0, w, h)
        else:
            cx, cy = start.x(), start.y()
            r = math.sqrt((sp.x() - cx) ** 2 + (sp.y() - cy) ** 2)
            if r < 2:
                return
            coords = (cx, cy, r)

        color = self.ROI_COLORS[(self._next_number - 1) % len(self.ROI_COLORS)]
        roi = {"type": self._shape_mode, "coords": coords,
               "color": color, "number": self._next_number}
        if self._shape_mode == "circle":
            roi.update(inner_ratio=0.5, start_angle=0.0, end_angle=360.0)
        else:
            roi["angle"] = 0.0

        self._regions.append(roi)
        self._next_number += 1
        self._redraw()
        self.changed.emit()

    # ══════════════════════════════════════════════════════════════════
    # 编辑
    # ══════════════════════════════════════════════════════════════════
    def on_selection_changed(self, list_index: int):
        self._selected_index = list_index
        if list_index < 0 or list_index >= len(self._regions):
            self._panel.hide_editor()
            return
        self._panel.show_editor(self._regions[list_index])

    def on_param_changed(self, roi_number: int, key: str, value: float):
        for roi in self._regions:
            if roi["number"] != roi_number:
                continue
            if key == "angle" and roi["type"] != "rect":
                continue
            if key in ("inner_ratio", "start_angle", "end_angle") and roi["type"] != "circle":
                continue
            roi[key] = value
            self._redraw()
            if key == "angle":
                self._panel.update_angle(value)
            break

    def on_rotate_key(self, delta: float):
        if self._selected_index < 0:
            return
        roi = self._regions[self._selected_index]
        if roi["type"] != "rect":
            return
        a = roi.get("angle", 0.0) + delta
        while a > 180:
            a -= 360
        while a <= -180:
            a += 360
        roi["angle"] = a
        self._redraw()
        self._panel.update_angle(a)

    def on_rotate_absolute(self, roi_number: int, new_angle: float):
        for roi in self._regions:
            if roi["number"] == roi_number:
                roi["angle"] = new_angle
                self._redraw()
                self._panel.update_angle(new_angle)
                break

    # ══════════════════════════════════════════════════════════════════
    # 清除
    # ══════════════════════════════════════════════════════════════════
    def clear_all(self):
        self._regions.clear()
        self._next_number = 1
        self._selected_index = -1
        self._panel.hide_editor()
        self._panel.update_display([])
        scene = self._canvas.scene_obj
        for item in scene.items():
            if isinstance(item, (ROIRectItem, ROICircleItem)):
                scene.removeItem(item)
        self.changed.emit()

    # ══════════════════════════════════════════════════════════════════
    # 渲染
    # ══════════════════════════════════════════════════════════════════
    def _redraw(self):
        scene = self._canvas.scene_obj
        for item in scene.items():
            if isinstance(item, (ROIRectItem, ROICircleItem)):
                scene.removeItem(item)
        for roi in self._regions:
            item = ROIRectItem(roi) if roi["type"] == "rect" else ROICircleItem(roi)
            item.roi_selected.connect(self._on_item_clicked)
            scene.addItem(item)
        self._panel.update_display(self._regions)

    def _on_item_clicked(self, roi_number: int):
        for i, r in enumerate(self._regions):
            if r["number"] == roi_number:
                self._selected_index = i
                self._panel.select_row(i)
                self._panel.show_editor(r)
                break

    # ══════════════════════════════════════════════════════════════════
    # 流水线集成: ROI 掩膜应用
    # ══════════════════════════════════════════════════════════════════
    def apply_mask(self, img: np.ndarray, params: dict) -> tuple:
        """根据 _selected_rois 创建掩膜并应用到图像。"""
        selected = params.pop("_selected_rois", None)
        if not selected or not self._regions:
            return img, params
        if "global" in selected:
            for k in list(params.keys()):
                if k.startswith("roi_"):
                    del params[k]
            return img, params

        chosen = [r for r in self._regions if r["number"] in selected]
        if not chosen:
            return img, params

        circles = [r for r in chosen if r["type"] == "circle"]
        if circles:
            roi = circles[0]
            cx, cy, r = roi["coords"]
            params.update(roi_type=1, roi_cx=int(cx), roi_cy=int(cy), roi_radius=int(r))
            params["inner_ratio"] = roi.get("inner_ratio", 0.5)
            params["start_angle"] = roi.get("start_angle", 0.0)
            params["end_angle"] = roi.get("end_angle", 360.0)
            return img, params

        h, w_img = img.shape[:2]
        mask = np.zeros((h, w_img), dtype=np.uint8)
        for roi in chosen:
            if roi["type"] != "rect":
                continue
            x, y, rw, rh = roi["coords"]
            angle = roi.get("angle", 0.0)
            if abs(angle) < 0.01:
                x1, y1 = max(0, int(x)), max(0, int(y))
                x2, y2 = min(w_img, int(x + rw)), min(h, int(y + rh))
                cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)
            else:
                rcx, rcy = x + rw / 2.0, y + rh / 2.0
                box = cv2.boxPoints(((rcx, rcy), (rw, rh), angle))
                cv2.fillPoly(mask, [np.int32(box)], 255)

        result = cv2.bitwise_and(img, img, mask=mask)
        for k in list(params.keys()):
            if k.startswith("roi_"):
                del params[k]
        return result, params
