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
    QScrollArea, QPushButton, QFrame, QGraphicsScene,
)
from ui.widgets.zoomable_graphics_view import ZoomableGraphicsView
from ui.widgets.coordinate_mapper import CoordinateMapper
from ui.theme import BG_BASE, BORDER_DEFAULT, RADIUS_MD

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

try:
    from systems.image_display.models import DisplayInfo
except ImportError:
    from dataclasses import dataclass
    @dataclass
    class DisplayInfo:
        actual_w: int = 0
        actual_h: int = 0
        display_w: int = 0
        display_h: int = 0


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

        # thumbnails
        self._thumb_row = QHBoxLayout()
        self._thumb_container = QWidget()
        self._thumb_container.setLayout(self._thumb_row)
        layout.addWidget(self._thumb_container)

        # Measurement result label (hidden by default)
        self._measurement_label = QLabel("")
        self._measurement_label.hide()
        layout.addWidget(self._measurement_label)

        self._rebuild_thumbs()

        # Ruler overlay (created after gv is set up)
        self._init_ruler_overlay()

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

    def _rebuild_thumbs(self):
        while self._thumb_row.count():
            child = self._thumb_row.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self._thumb_buttons = []
        for i in range(len(self._images)):
            btn = QPushButton(str(i + 1))
            btn.setFixedSize(28, 22)
            btn.setCheckable(True)
            idx = i
            btn.clicked.connect(lambda checked, ii=idx: self._select_image(ii))
            self._thumb_row.addWidget(btn)
            self._thumb_buttons.append(btn)
        self._thumb_row.addStretch()

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

        self._rebuild_thumbs()
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
        if isinstance(raw, ImageData):
            img = raw.array
            self._current_color_space = raw.color_space
        else:
            img = raw
            self._current_color_space = "bgr"

        # Check if it's a numpy array
        try:
            import numpy as np
            if isinstance(img, np.ndarray):
                self._actual_h, self._actual_w = img.shape[:2]
                self._mapper.update_image_size(self._actual_w, self._actual_h)
                self._load_pixmap(img, fit=fit)
                return
        except ImportError:
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
        for i, btn in enumerate(self._thumb_buttons):
            btn.setChecked(i == self._current_index)
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

        for i, btn in enumerate(self._thumb_buttons):
            btn.setChecked(i == self._current_index)

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
        return self._result.input_sets

    def _on_mode_changed(self, index):
        self._current_mode = self._mode_combo.itemData(index)
        self.clear_ruler()
        self._refresh_display()

    def _on_set_changed(self, index):
        self.clear_ruler()
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
        widget.pixel_hovered.connect(self.pixel_hovered.emit)
        widget.ruler_measurement.connect(self._on_ruler_measurement)
        if self._ruler_enabled:
            widget.set_ruler_enabled(True)
        self._set_layout.addWidget(widget)
        self._current_widget = widget
