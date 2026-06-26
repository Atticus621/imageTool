import time
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from PySide6.QtGui import QFont


class LogPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setFont(QFont("Consolas", 9))
        layout.addWidget(self._text_edit)

    def log(self, message: str, level: str = "INFO"):
        ts = time.strftime("%H:%M:%S")
        prefix = {
            "INFO": "",
            "WARN": "[WARN] ",
            "ERROR": "[ERROR] ",
            "DEBUG": "[DEBUG] ",
        }.get(level, "")
        self._text_edit.append(f"[{ts}] {prefix}{message}")

    def log_create(self, shape, state: dict):
        self.log(f"CREATE {state['type']} center={state.get('center')}")

    def log_select(self, shape, hit_type: str, state: dict):
        self.log(f"SELECT {state['type']} hit={hit_type} center={state.get('center')}")

    def log_move(self, shape, dx: float, dy: float, state: dict):
        self.log(f"MOVE {state['type']} delta=({dx:.1f},{dy:.1f}) new_center={state.get('center')}")

    def log_resize_edge(self, shape, edge: str, state: dict):
        self.log(f"RESIZE {state['type']} edge={edge} size={state.get('size')}")

    def log_resize_corner(self, shape, corner: int, state: dict):
        self.log(f"RESIZE {state['type']} corner={corner} size={state.get('size')}")

    def log_rotate(self, shape, state: dict):
        self.log(f"ROTATE {state['type']} angle={state.get('rotation')} handle={state.get('rotation_handle')}")

    def log_delete(self, state: dict):
        self.log(f"DELETE {state['type']} center={state.get('center')}")

    def log_api_command(self, command: dict, result: dict):
        self.log(f"API {command.get('action')} -> {result}", level="DEBUG")

    def log_validation(self, message: str, ok: bool):
        level = "INFO" if ok else "WARN"
        self.log(f"VALIDATE {'OK' if ok else 'FAIL'}: {message}", level=level)

    def clear(self):
        self._text_edit.clear()
