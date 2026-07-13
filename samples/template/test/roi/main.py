import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                                QToolBar, QPushButton, QDockWidget, QLineEdit,
                                QLabel, QApplication)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup

try:
    from .canvas import ROICanvas
    from .logger_panel import LogPanel
    from .command_api import CommandAPI
except ImportError:
    from canvas import ROICanvas
    from logger_panel import LogPanel
    from command_api import CommandAPI


class ROIEditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ROI Drawing System")
        self.setMinimumSize(1024, 768)
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        self._canvas = ROICanvas()
        self.setCentralWidget(self._canvas)

        self._init_toolbar()
        self._init_log_panel()
        self._init_command_bar()

    def _init_toolbar(self):
        toolbar = self.addToolBar("Tools")
        toolbar.setMovable(False)

        self._tool_group = QActionGroup(self)
        self._tool_group.setExclusive(True)

        self._select_action = QAction("Select", self)
        self._select_action.setCheckable(True)
        self._select_action.triggered.connect(lambda: self._set_tool("select"))
        self._tool_group.addAction(self._select_action)
        toolbar.addAction(self._select_action)

        self._rect_action = QAction("Rectangle", self)
        self._rect_action.setCheckable(True)
        self._rect_action.setChecked(True)
        self._rect_action.triggered.connect(lambda: self._set_tool("rect"))
        self._tool_group.addAction(self._rect_action)
        toolbar.addAction(self._rect_action)

        self._circle_action = QAction("Circle", self)
        self._circle_action.setCheckable(True)
        self._circle_action.triggered.connect(lambda: self._set_tool("circle"))
        self._tool_group.addAction(self._circle_action)
        toolbar.addAction(self._circle_action)

        self._polygon_action = QAction("Polygon", self)
        self._polygon_action.setCheckable(True)
        self._polygon_action.triggered.connect(lambda: self._set_tool("polygon"))
        self._tool_group.addAction(self._polygon_action)
        toolbar.addAction(self._polygon_action)

        toolbar.addSeparator()

        delete_action = QAction("Delete", self)
        delete_action.setShortcut("Delete")
        delete_action.triggered.connect(self._canvas.delete_selected)
        toolbar.addAction(delete_action)

        clear_action = QAction("Clear All", self)
        clear_action.triggered.connect(self._canvas.clear_all)
        toolbar.addAction(clear_action)

    def _init_log_panel(self):
        self._log_panel = LogPanel()
        dock = QDockWidget("Log", self)
        dock.setWidget(self._log_panel)
        dock.setMinimumWidth(300)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

    def _init_command_bar(self):
        cmd_widget = QWidget()
        cmd_layout = QHBoxLayout(cmd_widget)
        cmd_layout.setContentsMargins(4, 4, 4, 4)

        cmd_label = QLabel("Command:")
        self._cmd_input = QLineEdit()
        self._cmd_input.setPlaceholderText('{"action": "get_state"}')
        self._cmd_input.returnPressed.connect(self._execute_command)

        exec_btn = QPushButton("Execute")
        exec_btn.clicked.connect(self._execute_command)

        cmd_layout.addWidget(cmd_label)
        cmd_layout.addWidget(self._cmd_input)
        cmd_layout.addWidget(exec_btn)

        self._cmd_api = CommandAPI(self._canvas)

        dock = QDockWidget("Command API", self)
        dock.setWidget(cmd_widget)
        dock.setTitleBarWidget(QWidget())
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)

    def _connect_signals(self):
        self._canvas.log_message.connect(self._on_log_message)

    def _set_tool(self, tool: str):
        self._canvas.set_tool(tool)

    def _on_log_message(self, msg: str):
        level = "WARN" if "[WARN]" in msg else "DEBUG" if "[DEBUG]" in msg else "INFO"
        self._log_panel.log(msg, level)

    def _execute_command(self):
        text = self._cmd_input.text().strip()
        if not text:
            return
        result = self._cmd_api.execute(text)
        self._log_panel.log(f"CMD: {text}", level="DEBUG")
        self._log_panel.log(f"RESULT: {result}", level="DEBUG")
        self._cmd_input.clear()


def main():
    app = QApplication(sys.argv)
    window = ROIEditorWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
