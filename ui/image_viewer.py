"""Image viewer widget — displays pipeline execution results.

Uses QGraphicsView for zoom/pan — zero custom zoom/pan/scroll logic.
Supports multiple data types: images, text, and generic data.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, QSize, Signal, QPoint, QPointF, QRectF
from PySide6.QtGui import QPainter, QTransform
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QScrollArea, QPushButton, QFrame, QGraphicsScene, QSpinBox,
)
from ui.widgets.zoomable_graphics_view import ZoomableGraphicsView
from ui.widgets.coordinate_mapper import CoordinateMapper
from ui.theme import (
    BG_BASE, BG_INPUT, BORDER_DEFAULT, RADIUS_MD,
    TEXT_PRIMARY, TEXT_SECONDARY, ACCENT, FONT_SIZE_SM, SPACING_SM,
)

from core.logger import logger
from systems.execution.result import ExecutionResult

# Conditional imports - these may not exist in all tools
try:
    from core.image_data import ImageData
except ImportError:
    ImageData = None

try:
    from core.interfaces import IImageDisplayProvider
except ImportError:
    IImageDisplayProvider = None

from systems.image_display.models import DisplayInfo

try:
    from ui.widgets.ruler_overlay import RulerOverlay
except ImportError:
    RulerOverlay = None

try:
    from core.roi.editor.overlay import ROIOverlay
    from core.roi.editor.tcp_server import ROITcpServer
except ImportError:
    ROIOverlay = None
    ROITcpServer = None


# ------------------------------------------------------------------
# ImageSetWidget — one set of images with thumbnails
# ------------------------------------------------------------------

class ImageSetWidget(QFrame):
    """Displays a named set of images with thumbnail navigation.

    Uses QGraphicsView so zoom (wheel) and pan (middle-button drag)
    are handled natively by Qt. No custom zoom/pan/scroll logic.
    """

    image_changed = Signal()
    pixel_hovered = Signal(object)  # PixelInfo | None
    ruler_measurement = Signal(object)  # MeasurementResult

    def __init__(
        self,
        name: str,
        images: list,
        image_display: IImageDisplayProvider,
        parent=None,
    ):
        super().__init__(parent)
        self._name = name
        self._images = images
        self._image_display = image_display
        self._current_index = 0
        self._current_color_space: str = "bgr"
        self._actual_w: int = 0
        self._actual_h: int = 0
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._init_ui()
        self._init_mouse_tracking()
        self._select_image(0)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._header = QLabel(f"{self._name} ({len(self._images)} 张)")
        self._header.setWordWrap(False)
        layout.addWidget(self._header)

        # --- QGraphicsView — native zoom + pan ---
        self._gv = ZoomableGraphicsView()
        self._gv.setStyleSheet(
            f"background-color: {BG_BASE}; border: 1px solid {BORDER_DEFAULT}; border-radius: {RADIUS_MD};"
        )
        self._gv.setMinimumHeight(180)
        self._gv.setMaximumHeight(600)

        self._scene = QGraphicsScene()
        self._gv.setScene(self._scene)
        self._pixmap_item = None
        layout.addWidget(self._gv)

        # Navigation bar: ◀ [1/10] ▶  [Jump to: ___]
        self._nav_bar = QWidget()
        nav_layout = QHBoxLayout(self._nav_bar)
        nav_layout.setContentsMargins(0, 2, 0, 2)
        nav_layout.setSpacing(SPACING_SM)

        self._prev_btn = QPushButton("<-")
        self._prev_btn.setFixedSize(32, 22)
        self._prev_btn.setStyleSheet(
            f"QPushButton {{ padding: 2px 4px; font-size: {FONT_SIZE_SM}; min-height: 16px; height: 20px; }}"
        )
        self._prev_btn.clicked.connect(self._on_prev)
        nav_layout.addWidget(self._prev_btn)

        self._page_label = QLabel("0 / 0")
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._page_label.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: {FONT_SIZE_SM};"
            f"background-color: {BG_INPUT}; border: 1px solid {BORDER_DEFAULT};"
            f"border-radius: {RADIUS_MD}; padding: 2px 8px; min-width: 60px;"
        )
        nav_layout.addWidget(self._page_label)

        self._next_btn = QPushButton("->")
        self._next_btn.setFixedSize(32, 22)
        self._next_btn.setStyleSheet(
            f"QPushButton {{ padding: 2px 4px; font-size: {FONT_SIZE_SM}; min-height: 16px; height: 20px; }}"
        )
        self._next_btn.clicked.connect(self._on_next)
        nav_layout.addWidget(self._next_btn)

        nav_layout.addSpacing(8)

        jump_label = QLabel("跳转:")
        jump_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: {FONT_SIZE_SM};")
        nav_layout.addWidget(jump_label)

        self._jump_spin = QSpinBox()
        self._jump_spin.setRange(1, 1)
        self._jump_spin.setFixedSize(60, 22)
        self._jump_spin.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: {FONT_SIZE_SM};"
            f"background-color: {BG_INPUT}; border: 1px solid {BORDER_DEFAULT};"
            f"border-radius: {RADIUS_MD}; padding: 2px 4px;"
        )
        self._jump_spin.returnPressed.connect(self._on_jump)
        nav_layout.addWidget(self._jump_spin)

        nav_layout.addStretch()
        layout.addWidget(self._nav_bar)

        # Measurement result label (hidden by default)
        self._measurement_label = QLabel("")
        self._measurement_label.hide()
        layout.addWidget(self._measurement_label)

        self._update_nav_bar()

        # Ruler overlay (created after gv is set up)
        self._init_ruler_overlay()

        # ROI editor overlay
        self._init_roi_overlay()

    def _init_mouse_tracking(self):
        self._gv.viewport().setMouseTracking(True)
        self._gv.viewport().installEventFilter(self)

    def _init_ruler_overlay(self):
        self._mapper = CoordinateMapper(self._gv)
        ruler_system = getattr(self._image_display, 'ruler', None)
        self._ruler_overlay = RulerOverlay(
            parent=self._gv.viewport(),
            mapper=self._mapper,
            ruler_system=ruler_system,
        )
        self._ruler_overlay.setGeometry(self._gv.viewport().rect())
        self._ruler_overlay.hide()
        self._ruler_overlay.measurement_added.connect(self._on_measurement_added)

    def _on_measurement_added(self, result):
        self._measurement_label.setText(f"测量: {result.pixel_distance:.1f}px")
        self._measurement_label.show()
        self.ruler_measurement.emit(result)

    def set_ruler_enabled(self, enabled: bool):
        if enabled:
            self._ruler_overlay.setGeometry(self._gv.viewport().rect())
            self._ruler_overlay.set_visible(True)
            self._ruler_overlay.raise_()
        else:
            self._ruler_overlay.set_visible(False)

    def clear_ruler(self):
        self._ruler_overlay.clear_measurements()
        self._measurement_label.hide()

    # ------------------------------------------------------------------
    # ROI Editor overlay
    # ------------------------------------------------------------------

    def _init_roi_overlay(self):
        """初始化 ROI 编辑器叠加层，并启动 TCP 调试服务器。"""
        self._roi_overlay = None
        self._roi_tcp_server = None
        logger.info(f"[ROI] Initializing overlay (ROIOverlay={ROIOverlay is not None}, ROITcpServer={ROITcpServer is not None})")
        if ROIOverlay is not None:
            self._roi_overlay = ROIOverlay(
                parent=self._gv.viewport(),
                mapper=self._mapper,
            )
            self._roi_overlay.setGeometry(self._gv.viewport().rect())
            self._roi_overlay.hide()
            # 立即启动 TCP 调试服务器（无需等待 UI 启用）
            if ROITcpServer is not None:
                self._roi_tcp_server = ROITcpServer(self._roi_overlay)
                self._roi_tcp_server.start()
                logger.info("[ROI] TCP server started on 127.0.0.1:9527")

    def set_roi_editor_enabled(self, enabled: bool):
        """启用/禁用 ROI 编辑器（TCP 服务器始终运行）。"""
        if self._roi_overlay is None:
            return
        if enabled:
            self._roi_overlay.setGeometry(self._gv.viewport().rect())
            self._roi_overlay.show()
            self._roi_overlay.raise_()
            # 禁用标尺鼠标事件
            if hasattr(self, '_ruler_overlay') and self._ruler_overlay:
                self._ruler_overlay.setAttribute(
                    Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
                )
        else:
            self._roi_overlay.hide()
            # 恢复标尺鼠标事件
            if hasattr(self, '_ruler_overlay') and self._ruler_overlay:
                self._ruler_overlay.setAttribute(
                    Qt.WidgetAttribute.WA_TransparentForMouseEvents, False
                )

    def clear_roi_editor(self):
        """清除所有 ROI 形状。"""
        if self._roi_overlay:
            self._roi_overlay.clear_all()

    def _update_nav_bar(self):
        """Update navigation bar state to reflect current selection."""
        total = len(self._images)
        current = self._current_index + 1 if total > 0 else 0

        self._page_label.setText(f"{current} / {total}")
        self._jump_spin.blockSignals(True)
        self._jump_spin.setRange(1, max(1, total))
        self._jump_spin.setValue(current)
        self._jump_spin.blockSignals(False)

        self._prev_btn.setEnabled(total > 0 and self._current_index > 0)
        self._next_btn.setEnabled(total > 0 and self._current_index < total - 1)

    def _on_prev(self):
        if self._current_index > 0:
            self._select_image(self._current_index - 1)

    def _on_next(self):
        if self._current_index < len(self._images) - 1:
            self._select_image(self._current_index + 1)

    def _on_jump(self):
        target = self._jump_spin.value() - 1  # convert to 0-based
        if 0 <= target < len(self._images):
            self._select_image(target)

    # ------------------------------------------------------------------
    # Image selection / update
    # ------------------------------------------------------------------

    def update_images(self, name: str, images: list):
        if images is self._images and name == self._name:
            return
        if len(images) == len(self._images) and name == self._name:
            self._images = images
            self._update_image_display(fit=False)
            return

        self._name = name
        self._images = images
        self._header.setText(f"{self._name} ({len(self._images)} 张)")

        if self._current_index >= len(self._images):
            self._current_index = max(0, len(self._images) - 1)

        self._update_nav_bar()
        if self._images:
            self._select_image(self._current_index)

    def _select_image(self, index: int):
        if not (0 <= index < len(self._images)):
            return
        self._current_index = index
        self._update_image_display(fit=True)

    def _update_image_display(self, fit: bool = False):
        """Load the current item into the scene.

        Supports multiple data types:
        - numpy arrays: displayed as images
        - strings: displayed as text
        - ImageData: unwrapped to numpy array
        - Other: converted to string
        """
        raw = self._images[self._current_index]

        # Handle string data (text, formulas, etc.)
        if isinstance(raw, str):
            self._show_text(raw, fit=fit)
            return

        # Handle numpy array or ImageData
        if ImageData is not None and isinstance(raw, ImageData):
            img = raw.array
            self._current_color_space = raw.color_space
        else:
            img = raw
            self._current_color_space = "bgr"

        # Check if it's a numpy array
        try:
            if isinstance(img, np.ndarray):
                self._actual_h, self._actual_w = img.shape[:2]
                self._mapper.update_image_size(self._actual_w, self._actual_h)
                self._load_pixmap(img, fit=fit)
                return
        except Exception:
            pass

        # Fallback: display as text
        self._show_text(str(raw), fit=fit)

    def _show_text(self, text: str, fit: bool = False):
        """Display text content in the scene."""
        self._scene.clear()
        text_item = self._scene.addText(text)
        text_item.setDefaultTextColor(Qt.GlobalColor.white)
        font = text_item.font()
        font.setPointSize(14)
        text_item.setFont(font)
        self._scene.setSceneRect(QRectF(0, 0, 400, 100))
        if fit:
            self._gv.fitInView(
                self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio
            )
        self._update_nav_bar()
        self.image_changed.emit()

    def _load_pixmap(self, img: np.ndarray, fit: bool = False):
        """Convert the image to a viewport-sized QPixmap and add it to the scene.

        The pixmap itself is scaled to fit the viewport, but the QGraphicsItem
        is scaled so that scene coordinates still map to original image pixels.
        This keeps CoordinateMapper correct without re-computing map logic.
        """
        viewport = self._gv.viewport()
        max_size = QSize(viewport.width(), viewport.height())
        pixmap = self._image_display.convert_to_qpixmap(
            img, max_size=max_size, color_space=self._current_color_space,
        )

        self._scene.clear()
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._scene.setSceneRect(QRectF(0, 0, self._actual_w, self._actual_h))

        if pixmap.width() > 0 and pixmap.height() > 0:
            # Scale the downscaled pixmap so it covers the full image rectangle
            # in scene space. Scene coords therefore remain image pixel coords.
            scale_x = self._actual_w / pixmap.width()
            scale_y = self._actual_h / pixmap.height()
            self._pixmap_item.setTransform(
                QTransform.fromScale(scale_x, scale_y)
            )

        if fit:
            self._gv.fitInView(
                self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio
            )
            self._base_transform = self._gv.transform()

        self._update_nav_bar()
        self.image_changed.emit()

    def update_current_image(self, img: np.ndarray, color_space: str = "bgr"):
        """Update the currently displayed image without rebuilding the widget.

        Used for video loops where only the current frame changes.
        """
        if isinstance(img, ImageData):
            self._current_color_space = img.color_space
            img = img.array
        else:
            self._current_color_space = color_space

        self._actual_h, self._actual_w = img.shape[:2]
        self._mapper.update_image_size(self._actual_w, self._actual_h)
        self._load_pixmap(img, fit=False)

    @property
    def name(self) -> str:
        return self._name

    @property
    def image_count(self) -> int:
        return len(self._images)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_current_image(self) -> np.ndarray | None:
        if 0 <= self._current_index < len(self._images):
            raw = self._images[self._current_index]
            if isinstance(raw, ImageData):
                return raw.array
            return raw
        return None

    def get_current_image_color_space(self) -> str:
        return self._current_color_space

    def get_display_info(self) -> DisplayInfo | None:
        """Build DisplayInfo from the current view transform."""
        tr = self._gv.transform()
        # m11 = horizontal scale, m22 = vertical scale
        scale_x = tr.m11() if tr.m11() != 0 else 1.0
        scale_y = tr.m22() if tr.m22() != 0 else 1.0
        display_w = int(self._actual_w * scale_x)
        display_h = int(self._actual_h * scale_y)
        return DisplayInfo(
            actual_w=self._actual_w,
            actual_h=self._actual_h,
            display_w=display_w,
            display_h=display_h,
        )

    # ------------------------------------------------------------------
    # Coordinate mapping — delegated to CoordinateMapper
    # ------------------------------------------------------------------

    def map_viewport_to_image(
        self, viewport_x: float, viewport_y: float
    ) -> tuple[int, int] | None:
        """Map viewport-local coordinates to image pixel coordinates."""
        return self._mapper.viewport_to_image(viewport_x, viewport_y)

    # ------------------------------------------------------------------
    # Mouse tracking → pixel info
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent

        if obj is self._gv.viewport() and event.type() == QEvent.Type.MouseMove:
            self._handle_mouse_move(event)
        if obj is self._gv.viewport() and event.type() == QEvent.Type.Resize:
            # 更新叠加层几何尺寸
            rect = self._gv.viewport().rect()
            if hasattr(self, '_ruler_overlay') and self._ruler_overlay:
                self._ruler_overlay.setGeometry(rect)
            if hasattr(self, '_roi_overlay') and self._roi_overlay:
                self._roi_overlay.setGeometry(rect)
        return super().eventFilter(obj, event)

    def _handle_mouse_move(self, event):
        pos = event.position()
        img_coords = self.map_viewport_to_image(pos.x(), pos.y())

        if img_coords is None:
            self.pixel_hovered.emit(None)
            return

        ix, iy = img_coords
        img = self.get_current_image()
        if img is None:
            self.pixel_hovered.emit(None)
            return

        info_system = getattr(self._image_display, 'info', None)
        if info_system is None:
            self.pixel_hovered.emit(None)
            return

        pixel_info = info_system.get_pixel_info(
            img, ix, iy, self._current_color_space,
        )
        self.pixel_hovered.emit(pixel_info)


# ------------------------------------------------------------------
# ImageViewerWidget — orchestrates multiple ImageSetWidgets + ruler
# ------------------------------------------------------------------

class ImageViewerWidget(QWidget):
    """Right-side panel: toolbar, image set list, ruler overlay.

    No custom zoom/pan code — that's all in QGraphicsView.
    Coordinates ruler overlay placement across multiple ImageSetWidgets.
    """

    ruler_measurement = Signal(object)
    pixel_hovered = Signal(object)  # PixelInfo | None

    def __init__(self, image_display: IImageDisplayProvider, parent=None):
        super().__init__(parent)
        self._image_display = image_display
        self._result = ExecutionResult(success=False)
        self._current_mode = "output"
        self._current_widget: ImageSetWidget | None = None
        self._ruler_enabled = False
        self._roi_editor_enabled = False
        self._custom_sets: dict[str, list] = {}  # display_id -> list[ImageSetEntry]
        self._custom_display_ids: list[str] = []  # ordered display IDs in combo
        self._init_ui()
        logger.info("ImageViewerWidget initialized (QGraphicsView)")

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Toolbar
        toolbar = QHBoxLayout()
        self._mode_combo = QComboBox()
        self._mode_combo.setMinimumWidth(100)
        self._mode_combo.addItem("输出显示", "output")
        self._mode_combo.addItem("输入显示", "input")
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        toolbar.addWidget(QLabel("显示:"))
        toolbar.addWidget(self._mode_combo)

        self._set_combo = QComboBox()
        self._set_combo.setMinimumWidth(120)
        self._set_combo.currentIndexChanged.connect(self._on_set_changed)
        toolbar.addWidget(QLabel("图集:"))
        toolbar.addWidget(self._set_combo)

        toolbar.addStretch()

        # ROI Editor toggle button (alongside ruler)
        self._roi_editor_btn = QPushButton("ROI")
        self._roi_editor_btn.setCheckable(True)
        self._roi_editor_btn.setFixedHeight(24)
        self._roi_editor_btn.setStyleSheet(
            f"QPushButton {{ padding: 2px 8px; font-size: {FONT_SIZE_SM}; }}"
            f"QPushButton:checked {{ background-color: {ACCENT}; color: white; }}"
        )
        self._roi_editor_btn.toggled.connect(self._on_roi_editor_toggled)
        toolbar.addWidget(self._roi_editor_btn)

        # ROI Shape tool combo
        self._roi_tool_combo = QComboBox()
        self._roi_tool_combo.addItems(["Select", "Rect", "Circle", "Polygon"])
        self._roi_tool_combo.setMinimumWidth(80)
        self._roi_tool_combo.setEnabled(False)
        self._roi_tool_combo.currentTextChanged.connect(self._on_roi_tool_changed)
        toolbar.addWidget(self._roi_tool_combo)

        self._count_label = QLabel("")
        toolbar.addWidget(self._count_label)
        layout.addLayout(toolbar)

        # Single ImageSetWidget container
        self._set_container = QWidget()
        self._set_layout = QVBoxLayout(self._set_container)
        self._set_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._set_container, 1)

        # Placeholder
        self._placeholder = QLabel("暂无图像数据\n\n请搭建节点并点击 ▶ 开始 执行")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._placeholder)

        self._refresh_display()

        # ROI 编辑器：如果当前没有 ImageSetWidget，创建一个最小化的用于 TCP 调试
        if self._current_widget is None:
            self._init_roi_standalone()

    # ------------------------------------------------------------------
    # Ruler — coordinated across ImageSetWidgets
    # ------------------------------------------------------------------

    def toggle_ruler(self):
        self._ruler_enabled = not self._ruler_enabled
        if self._current_widget:
            self._current_widget.set_ruler_enabled(self._ruler_enabled)
        return self._ruler_enabled

    def clear_ruler(self):
        if self._current_widget:
            self._current_widget.clear_ruler()

    # ------------------------------------------------------------------
    # ROI Editor — coordinated across ImageSetWidgets
    # ------------------------------------------------------------------

    def _on_roi_editor_toggled(self, enabled: bool):
        self._roi_editor_enabled = enabled
        self._roi_tool_combo.setEnabled(enabled)
        if self._current_widget:
            self._current_widget.set_roi_editor_enabled(enabled)

    def _on_roi_tool_changed(self, text: str):
        tool_map = {"Select": "select", "Rect": "rect", "Circle": "circle", "Polygon": "polygon"}
        tool = tool_map.get(text, "select")
        overlay = None
        if self._current_widget and self._current_widget._roi_overlay:
            overlay = self._current_widget._roi_overlay
        elif hasattr(self, '_roi_overlay') and self._roi_overlay:
            overlay = self._roi_overlay
        if overlay:
            overlay.set_tool(tool)

    def toggle_roi_editor(self):
        self._roi_editor_btn.toggle()
        return self._roi_editor_enabled

    def clear_roi_editor(self):
        if self._current_widget:
            self._current_widget.clear_roi_editor()

    def _init_roi_standalone(self):
        """无图像时创建可见的 ROI overlay + TCP 服务器用于调试。"""
        if ROIOverlay is None or ROITcpServer is None:
            return
        from ui.widgets.zoomable_graphics_view import ZoomableGraphicsView
        from PySide6.QtWidgets import QGraphicsScene

        # 创建 graphics view 作为 overlay 容器
        self._roi_standalone_gv = ZoomableGraphicsView()
        self._roi_standalone_gv.setMinimumSize(800, 600)
        self._roi_standalone_gv.setStyleSheet(
            f"background-color: {BG_BASE}; border: 1px solid {BORDER_DEFAULT}; border-radius: {RADIUS_MD};"
        )
        self._roi_standalone_gv.setScene(QGraphicsScene())

        # 先加入布局并显示，确保 viewport 有正确的尺寸
        self._placeholder.hide()
        self._set_container.show()
        self._set_layout.addWidget(self._roi_standalone_gv)
        self._roi_standalone_gv.show()

        # 创建 overlay（viewport 现在有正确的尺寸）
        mapper = CoordinateMapper(self._roi_standalone_gv)
        self._roi_overlay = ROIOverlay(
            parent=self._roi_standalone_gv.viewport(),
            mapper=mapper,
        )
        self._roi_overlay.setGeometry(self._roi_standalone_gv.viewport().rect())
        self._roi_overlay.show()
        self._roi_overlay.raise_()

        # 启动 TCP 服务器
        self._roi_tcp_server = ROITcpServer(self._roi_overlay)
        self._roi_tcp_server.start()
        logger.info(f"[ROI] Standalone ROI editor visible, viewport={self._roi_standalone_gv.viewport().rect()}")

    # ------------------------------------------------------------------
    # Zoom
    # ------------------------------------------------------------------

    def reset_zoom(self) -> None:
        """Reset zoom on current ImageSetWidget."""
        if self._current_widget:
            self._current_widget._gv.reset_zoom()

    def get_current_image_info(self) -> dict | None:
        if self._current_widget:
            di = self._current_widget.get_display_info()
            if di:
                return {
                    "actual_w": di.actual_w,
                    "actual_h": di.actual_h,
                    "display_w": di.display_w,
                    "display_h": di.display_h,
                }
        return None

    # ------------------------------------------------------------------
    # Results display
    # ------------------------------------------------------------------

    def _on_ruler_measurement(self, result):
        self.ruler_measurement.emit(result)

    def set_execution_results(self, result: ExecutionResult):
        self._result = result
        logger.info(
            f"ImageViewer: received {len(result.input_sets)} input sets, "
            f"{len(result.output_sets)} output sets"
        )
        current_sets = self._get_current_sets()
        total = sum(len(s.images) for s in current_sets)
        self._count_label.setText(f"{len(current_sets)} 组 / {total} 张")
        self._refresh_display()

    def _get_current_sets(self):
        if self._current_mode == "output":
            return self._result.output_sets
        if self._current_mode == "input":
            return self._result.input_sets
        # Custom display mode: mode is "custom:<display_id>"
        if self._current_mode.startswith("custom:"):
            display_id = self._current_mode[7:]  # strip "custom:" prefix
            return self._custom_sets.get(display_id, [])
        return []

    def _on_mode_changed(self, index):
        self._current_mode = self._mode_combo.itemData(index)
        self.clear_ruler()
        self.clear_roi_editor()
        self._refresh_display()

    def _on_set_changed(self, index):
        self.clear_ruler()
        self.clear_roi_editor()
        self._show_current_set()

    def _refresh_display(self):
        sets = self._get_current_sets()

        # Update set combo
        self._set_combo.blockSignals(True)
        self._set_combo.clear()
        for s in sets:
            self._set_combo.addItem(f"{s.name} ({len(s.images)}张)", s.name)
        self._set_combo.blockSignals(False)

        if not sets:
            self._count_label.setText("0 组 / 0 张")
            self._placeholder.show()
            self._set_container.hide()
            return

        self._placeholder.hide()
        self._set_container.show()

        # Show the first set
        self._show_current_set()

    def _show_current_set(self):
        sets = self._get_current_sets()
        if not sets:
            return

        # Find the selected set
        set_index = self._set_combo.currentIndex()
        if set_index < 0 or set_index >= len(sets):
            set_index = 0

        s = sets[set_index]
        total = len(s.images)
        self._count_label.setText(f"{total} 张")

        # Reuse the existing widget if we are displaying the same set.
        # This avoids recreating QGraphicsView / scene / thumbnails every frame
        # when running a video loop.
        if (
            self._current_widget is not None
            and self._current_widget.name == s.name
            and self._current_widget.image_count == total
        ):
            self._current_widget.update_images(s.name, s.images)
            return

        # Remove old widget
        if self._current_widget:
            self._current_widget.deleteLater()
            self._current_widget = None

        # Clear layout
        while self._set_layout.count():
            child = self._set_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Create new widget
        widget = ImageSetWidget(s.name, s.images, self._image_display)
        widget.image_changed.connect(self.clear_ruler)
        widget.image_changed.connect(self.clear_roi_editor)
        widget.pixel_hovered.connect(self.pixel_hovered.emit)
        widget.ruler_measurement.connect(self._on_ruler_measurement)
        if self._ruler_enabled:
            widget.set_ruler_enabled(True)
        if self._roi_editor_enabled:
            widget.set_roi_editor_enabled(True)
        self._set_layout.addWidget(widget)
        self._current_widget = widget

    # ------------------------------------------------------------------
    # Custom display management
    # ------------------------------------------------------------------

    def add_custom_display(self, display_id: str, name: str) -> None:
        """Add a new custom display to the combo box."""
        if display_id in self._custom_display_ids:
            return
        self._custom_display_ids.append(display_id)
        self._mode_combo.blockSignals(True)
        self._mode_combo.addItem(f"[自定义] {name}", f"custom:{display_id}")
        self._mode_combo.blockSignals(False)

    def remove_custom_display(self, display_id: str) -> None:
        """Remove a custom display from the combo box."""
        if display_id not in self._custom_display_ids:
            return
        self._custom_display_ids.remove(display_id)
        self._custom_sets.pop(display_id, None)
        # Find and remove the combo item
        for i in range(self._mode_combo.count()):
            if self._mode_combo.itemData(i) == f"custom:{display_id}":
                self._mode_combo.removeItem(i)
                break

    def rename_custom_display(self, display_id: str, new_name: str) -> None:
        """Rename a custom display in the combo box."""
        for i in range(self._mode_combo.count()):
            if self._mode_combo.itemData(i) == f"custom:{display_id}":
                self._mode_combo.blockSignals(True)
                self._mode_combo.setItemText(i, f"[自定义] {new_name}")
                self._mode_combo.blockSignals(False)
                break

    def set_custom_display_data(self, display_id: str, sets: list) -> None:
        """Update the image data for a custom display."""
        self._custom_sets[display_id] = sets
        # If currently viewing this custom display, refresh
        if self._current_mode == f"custom:{display_id}":
            self._refresh_display()

    def sync_custom_displays(self, displays: dict[str, str]) -> None:
        """Sync the combo box with the current set of custom displays.

        Args:
            displays: {display_id: display_name} of all custom displays.
        """
        # Remove displays that no longer exist
        for did in list(self._custom_display_ids):
            if did not in displays:
                self.remove_custom_display(did)

        # Add new displays
        for did, name in displays.items():
            if did not in self._custom_display_ids:
                self.add_custom_display(did, name)
            else:
                self.rename_custom_display(did, name)
