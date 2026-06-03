# -*- coding: utf-8 -*-
"""主窗口 —— QMainWindow: 工具栏 + 画布/面板分割器 + 状态栏。"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QToolBar, QSplitter, QStatusBar,
    QLabel, QWidget, QVBoxLayout, QScrollArea,
    QFileDialog, QMessageBox,
)


class MainWindow(QMainWindow):
    """图像查看器主窗口。"""

    # ── 工具栏信号 ──
    open_requested = Signal(str)               # 文件路径
    fit_to_window_requested = Signal()
    export_image_requested = Signal()
    open_image_shortcut = Signal()              # Ctrl+O 快捷键

    # ── 工具切换信号 ──
    tool_change_requested = Signal(str)        # "hand", "ruler", "roi"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("图像查看器")
        self.resize(1200, 750)

        # 中央分割器
        self._splitter = QSplitter(Qt.Horizontal, self)

        # 左侧: 图像画布占位 (由外部注入)
        self._canvas_placeholder = QWidget()
        self._canvas_placeholder.setStyleSheet("background-color: #2c2c2c;")
        self._splitter.addWidget(self._canvas_placeholder)

        # 右侧: 滚动面板占位
        self._right_scroll = QScrollArea()
        self._right_scroll.setWidgetResizable(True)
        self._right_scroll.setMinimumWidth(280)
        self._right_scroll.setMaximumWidth(380)
        self._right_scroll.setStyleSheet("QScrollArea { background: #ecf0f1; border: none; }")
        self._right_inner = QWidget()
        self._right_inner.setStyleSheet("background: #ecf0f1;")
        self._right_layout = QVBoxLayout(self._right_inner)
        self._right_layout.setContentsMargins(8, 8, 8, 8)
        self._right_layout.setSpacing(8)
        self._right_scroll.setWidget(self._right_inner)
        self._splitter.addWidget(self._right_scroll)
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 0)
        self.setCentralWidget(self._splitter)

        # 工具栏
        self._build_toolbar()

        # 状态栏
        self._build_statusbar()

    # ------------------------------------------------------------------
    # 工具栏
    # ------------------------------------------------------------------
    def _build_toolbar(self):
        toolbar = QToolBar("工具")
        toolbar.setMovable(False)
        toolbar.setStyleSheet("""
            QToolBar { background: #34495e; spacing: 4px; padding: 4px; border: none; }
            QToolButton { color: white; padding: 6px 10px; border: none; border-radius: 3px;
                          font-family: 'Microsoft YaHei'; font-size: 12px; }
            QToolButton:hover { background: #3d566e; }
            QToolButton:checked { background: #2ecc71; }
        """)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        # 工具按钮 (互斥)
        act_hand = QAction("🖱 鼠标", self)
        act_hand.setCheckable(True)
        act_hand.setChecked(True)
        act_hand.triggered.connect(lambda: self.tool_change_requested.emit("hand"))
        toolbar.addAction(act_hand)

        act_ruler = QAction("📏 尺子", self)
        act_ruler.setCheckable(True)
        act_ruler.triggered.connect(lambda: self.tool_change_requested.emit("ruler"))
        toolbar.addAction(act_ruler)

        act_roi = QAction("🔲 区域", self)
        act_roi.setCheckable(True)
        act_roi.triggered.connect(lambda: self.tool_change_requested.emit("roi"))
        toolbar.addAction(act_roi)

        self._tool_actions = {"hand": act_hand, "ruler": act_ruler, "roi": act_roi}

        toolbar.addSeparator()

        # Ctrl+O 快捷键（打开图片）
        act_open_shortcut = QAction(self)
        act_open_shortcut.setShortcut(QKeySequence("Ctrl+O"))
        act_open_shortcut.triggered.connect(self.open_image_shortcut.emit)
        self.addAction(act_open_shortcut)

        act_fit = QAction("🔎 适应窗口", self)
        act_fit.triggered.connect(lambda: self.fit_to_window_requested.emit())
        toolbar.addAction(act_fit)

        toolbar.addSeparator()

        act_export = QAction("💾 导出图片", self)
        act_export.triggered.connect(lambda: self.export_image_requested.emit())
        toolbar.addAction(act_export)

    def _on_open(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp);;所有文件 (*.*)"
        )
        if path:
            self.open_requested.emit(path)

    def highlight_tool_button(self, tool: str):
        """高亮指定工具按钮。"""
        for name, action in self._tool_actions.items():
            action.setChecked(name == tool)

    # ------------------------------------------------------------------
    # 状态栏
    # ------------------------------------------------------------------
    def _build_statusbar(self):
        self._statusbar = QStatusBar(self)
        self._statusbar.setStyleSheet("""
            QStatusBar { background: #ecf0f1; border-top: 1px solid #bdc3c7; }
            QLabel { font-family: 'Consolas', 'Microsoft YaHei'; font-size: 12px; padding: 0 6px; }
        """)
        self.setStatusBar(self._statusbar)

        # 左侧: 状态消息
        self._status_msg = QLabel("就绪 — 请打开一张图片")
        self._statusbar.addWidget(self._status_msg, 1)

        # 右侧: 像素信息 (permanent = 右对齐)
        self._info_pos_label = QLabel("坐标: --")
        self._info_color_label = QLabel("颜色: --")
        self._info_world_label = QLabel("")

        sep_style = "color: #bdc3c7; padding: 0 2px;"
        sep1 = QLabel("│"); sep1.setStyleSheet(sep_style)

        self._statusbar.addPermanentWidget(self._info_world_label)
        self._statusbar.addPermanentWidget(self._info_color_label)
        self._statusbar.addPermanentWidget(sep1)
        self._statusbar.addPermanentWidget(self._info_pos_label)

    def set_status(self, text: str):
        self._status_msg.setText(text)

    def update_status_info(self, pos_text: str, color_text: str, world_text: str = ""):
        self._info_pos_label.setText(f"坐标: {pos_text}")
        self._info_color_label.setText(f"颜色: {color_text}" if color_text else "颜色: --")
        if world_text:
            self._info_world_label.setText(f"物理: {world_text}")
        else:
            self._info_world_label.setText("")

    # ------------------------------------------------------------------
    # 公共访问器
    # ------------------------------------------------------------------
    def set_canvas(self, canvas_widget):
        """用实际画布替换占位符。"""
        idx = self._splitter.indexOf(self._canvas_placeholder)
        self._canvas_placeholder.hide()
        self._splitter.replaceWidget(idx, canvas_widget)
        canvas_widget.show()
        self._canvas_placeholder = canvas_widget

    def right_panel(self):
        """返回右侧面板的内部 widget 和布局。"""
        return self._right_inner, self._right_layout

    def show_error(self, title: str, message: str):
        QMessageBox.critical(self, title, message)

    def show_warning(self, title: str, message: str):
        QMessageBox.warning(self, title, message)

    def show_info(self, title: str, message: str):
        QMessageBox.information(self, title, message)
