"""CommandAPI — JSON 命令接口，支持本地执行和 TCP 远程调用。"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF

if TYPE_CHECKING:
    from core.roi.editor.overlay import ROIOverlay


class CommandAPI:
    """JSON 命令接口，用于程序化控制 ROI 编辑器。"""

    def __init__(self, overlay: ROIOverlay):
        self._overlay = overlay

    def execute(self, command: dict) -> dict:
        """执行 JSON 命令，返回结果字典。"""
        action = command.get("action")
        if not action:
            return {"status": "error", "error": "missing 'action' field"}

        handlers = {
            "clear": self._clear,
            "get_state": self._get_state,
            "draw_rect": self._draw_rect,
            "draw_circle": self._draw_circle,
            "draw_polygon": self._draw_polygon,
            "select": self._select,
            "move": self._move,
            "delete": self._delete,
            "set_tool": self._set_tool,
        }

        handler = handlers.get(action)
        if not handler:
            return {"status": "error", "error": f"unknown action: {action}"}

        try:
            return handler(command)
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _clear(self, cmd: dict) -> dict:
        self._overlay.clear_all()
        return {"status": "ok"}

    def _get_state(self, cmd: dict) -> dict:
        shapes = self._overlay.shapes
        return {
            "status": "ok",
            "count": len(shapes),
            "shapes": [s.get_state_dict() for s in shapes],
        }

    def _draw_rect(self, cmd: dict) -> dict:
        from core.roi.editor.shapes.rectangle import RectangleShape
        from PySide6.QtCore import QRectF
        x1, y1 = cmd["x1"], cmd["y1"]
        x2, y2 = cmd["x2"], cmd["y2"]
        shape = RectangleShape(QRectF(QPointF(x1, y1), QPointF(x2, y2)))
        self._overlay.add_shape(shape)
        return {"status": "ok", "shape": shape.get_state_dict()}

    def _draw_circle(self, cmd: dict) -> dict:
        from core.roi.editor.shapes.circle import CircleShape
        import math
        x1, y1 = cmd["x1"], cmd["y1"]
        x2, y2 = cmd["x2"], cmd["y2"]
        radius = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        shape = CircleShape(QPointF(x1, y1), radius)
        self._overlay.add_shape(shape)
        return {"status": "ok", "shape": shape.get_state_dict()}

    def _draw_polygon(self, cmd: dict) -> dict:
        from core.roi.editor.shapes.polygon import PolygonShape
        points = cmd["points"]
        shape = PolygonShape()
        for p in points:
            shape.add_vertex(QPointF(p[0], p[1]))
        self._overlay.add_shape(shape)
        return {"status": "ok", "shape": shape.get_state_dict()}

    def _select(self, cmd: dict) -> dict:
        index = cmd["index"]
        shapes = self._overlay.shapes
        if 0 <= index < len(shapes):
            self._overlay.select_shape(shapes[index])
            return {"status": "ok"}
        return {"status": "error", "error": f"index {index} out of range"}

    def _move(self, cmd: dict) -> dict:
        shape = self._overlay.selected_shape
        if shape:
            shape.move(cmd["x"], cmd["y"])
            self._overlay.update()
            return {"status": "ok"}
        return {"status": "error", "error": "no shape selected"}

    def _delete(self, cmd: dict) -> dict:
        if self._overlay.delete_selected():
            return {"status": "ok"}
        return {"status": "error", "error": "no shape selected"}

    def _set_tool(self, cmd: dict) -> dict:
        self._overlay.set_tool(cmd["tool"])
        return {"status": "ok"}
