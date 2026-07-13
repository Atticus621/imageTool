import json
from PySide6.QtCore import QPointF


class CommandAPI:
    def __init__(self, canvas):
        self._canvas = canvas

    def execute(self, json_str: str) -> dict:
        try:
            cmd = json.loads(json_str)
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON: {e}"}

        action = cmd.get("action")
        if not action:
            return {"error": "Missing 'action' field"}

        handler = {
            "move": self._cmd_move,
            "click": self._cmd_click,
            "drag": self._cmd_drag,
            "select": self._cmd_select,
            "delete": self._cmd_delete,
            "get_state": self._cmd_get_state,
            "clear": self._cmd_clear,
            "draw_rect": self._cmd_draw_rect,
            "draw_circle": self._cmd_draw_circle,
        }.get(action)

        if handler is None:
            return {"error": f"Unknown action: {action}"}
        return handler(cmd)

    def _cmd_move(self, cmd: dict) -> dict:
        x = cmd.get("x", 0)
        y = cmd.get("y", 0)
        self._canvas.simulate_mouse_move(QPointF(x, y))
        return {"status": "ok", "moved_to": (x, y)}

    def _cmd_click(self, cmd: dict) -> dict:
        x = cmd.get("x", 0)
        y = cmd.get("y", 0)
        self._canvas.simulate_mouse_click(QPointF(x, y))
        return {"status": "ok", "clicked": (x, y)}

    def _cmd_drag(self, cmd: dict) -> dict:
        x1, y1 = cmd.get("x1", 0), cmd.get("y1", 0)
        x2, y2 = cmd.get("x2", 0), cmd.get("y2", 0)
        self._canvas.simulate_mouse_drag(QPointF(x1, y1), QPointF(x2, y2))
        return {"status": "ok", "dragged": ((x1, y1), (x2, y2))}

    def _cmd_select(self, cmd: dict) -> dict:
        index = cmd.get("index", 0)
        shapes = self._canvas.shapes
        if 0 <= index < len(shapes):
            self._canvas.select_shape(shapes[index])
            return {"status": "ok", "selected_index": index}
        return {"error": f"Index {index} out of range (0-{len(shapes) - 1})"}

    def _cmd_delete(self, cmd: dict) -> dict:
        deleted = self._canvas.delete_selected()
        return {"status": "ok", "deleted": deleted}

    def _cmd_get_state(self, cmd: dict) -> dict:
        states = [s.get_state_dict() for s in self._canvas.shapes]
        return {"status": "ok", "shapes": states, "count": len(states)}

    def _cmd_clear(self, cmd: dict) -> dict:
        self._canvas.clear_all()
        return {"status": "ok", "cleared": True}

    def _cmd_draw_rect(self, cmd: dict) -> dict:
        x1, y1 = cmd.get("x1", 0), cmd.get("y1", 0)
        x2, y2 = cmd.get("x2", 0), cmd.get("y2", 0)
        self._canvas.simulate_mouse_drag(QPointF(x1, y1), QPointF(x2, y2), shape_type="rect")
        return {"status": "ok", "drew_rect": ((x1, y1), (x2, y2))}

    def _cmd_draw_circle(self, cmd: dict) -> dict:
        x1, y1 = cmd.get("x1", 0), cmd.get("y1", 0)
        x2, y2 = cmd.get("x2", 0), cmd.get("y2", 0)
        self._canvas.simulate_mouse_drag(QPointF(x1, y1), QPointF(x2, y2), shape_type="circle")
        return {"status": "ok", "drew_circle": ((x1, y1), (x2, y2))}
