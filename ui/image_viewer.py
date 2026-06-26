"""Image viewer widget — displays pipeline execution results.

Depends on ImageDisplaySystem for image-to-Qt conversion and coordinate
mapping. Contains no cv2/numpy imports — all image processing is delegated.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, QSize, Signal, QPoint, QRect
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QScrollArea, QPushButton, QFrame,
)

from core.logger import logger
from core.engine.result import ExecutionResult
from systems.image_display.models import DisplayInfo
from systems.image_display.system import ImageDisplaySystem
from ui.widgets.ruler_overlay import RulerOverlay


class ImageSetWidget(QFrame):
    """Displays a named set of images with thumbnail navigation."""

    image_changed = Signal()

    def __init__(
        self,
        name: str,
        images: list,
        image_display: ImageDisplaySystem,
        parent=None,
    ):
        super().__init__(parent)
        self._name = name
        self._images = images
        self._image_display = image_display
        self._current_index = 0
        self._display_info: DisplayInfo | None = None
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._header = QLabel(f"{self._name} ({len(self._images)} 张)")
        self._header.setStyleSheet("font-weight: bold; font-size: 10px;")
        self._header.setWordWrap(False)
        layout.addWidget(self._header)

        self._img_label = QLabel()
        self._img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_label.setMinimumHeight(180)
        self._img_label.setMaximumHeight(300)
        self._img_label.setStyleSheet(
            "background-color: #1a1a2e; border: 1px solid #333; border-radius: 4px;"
        )
        layout.addWidget(self._img_label)

        self._thumb_row = QHBoxLayout()
        self._thumb_container = QWidget()
        self._thumb_container.setLayout(self._thumb_row)
        layout.addWidget(self._thumb_container)

        self._rebuild_thumbs()
        self._select_image(0)

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

    def update_images(self, name: str, images: list):
        if images is self._images and name == self._name:
            return
        if len(images) == len(self._images) and name == self._name:
            # Pixel-only refresh (e.g. camera loop mode) — don't emit
            # image_changed so the ruler measurement survives.
            self._images = images
            self._select_image(self._current_index, emit=False)
            return

        self._name = name
        self._images = images
        self._header.setText(f"{self._name} ({len(self._images)} 张)")

        if self._current_index >= len(self._images):
            self._current_index = max(0, len(self._images) - 1)

        self._rebuild_thumbs()
        if self._images:
            self._select_image(self._current_index)

    def _select_image(self, index: int, emit: bool = True):
        if 0 <= index < len(self._images):
            self._current_index = index
            img = self._images[index]
            max_size = QSize(400, 280)

            # Delegate to ImageDisplaySystem — single source of truth
            # for DisplayInfo (fixes the DPR-related ruler measurement bug).
            self._display_info = self._image_display.compute_display_info(img, 400, 280)
            pixmap = self._image_display.convert_to_qpixmap(img, max_size)
            self._img_label.setPixmap(pixmap)

            for i, btn in enumerate(self._thumb_buttons):
                btn.setChecked(i == index)

            if emit:
                self.image_changed.emit()

    def get_current_image(self) -> np.ndarray | None:
        if 0 <= self._current_index < len(self._images):
            return self._images[self._current_index]
        return None

    def get_display_info(self) -> DisplayInfo | None:
        """Return the DisplayInfo for the current image.

        Used by ImageViewerWidget for coordinate mapping.
        """
        return self._display_info

    def get_pixmap_rect_in_label(self) -> tuple[float, float, float, float] | None:
        """Return (offset_x, offset_y, display_w, display_h) for the pixmap
        within the label. Used for centering offset calculation."""
        if self._display_info is None:
            return None
        label_w = self._img_label.width()
        label_h = self._img_label.height()
        offset_x = (label_w - self._display_info.display_w) / 2
        offset_y = (label_h - self._display_info.display_h) / 2
        return (
            offset_x, offset_y,
            self._display_info.display_w, self._display_info.display_h,
        )


class ImageViewerWidget(QWidget):
    """Right-side panel displaying pipeline execution results (input/output sets).

    Coordinates ruler overlay placement and delegates coordinate mapping
    to ImageDisplaySystem.
    """

    ruler_measurement = Signal(object)

    def __init__(self, image_display: ImageDisplaySystem, parent=None):
        super().__init__(parent)
        self._image_display = image_display
        self._result = ExecutionResult(success=False)
        self._current_mode = "output"
        self._set_widgets: list[ImageSetWidget] = []
        self._ruler_enabled = False
        self._init_ui()
        self._init_ruler_overlay()
        logger.info("ImageViewerWidget initialized")

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        toolbar = QHBoxLayout()
        self._mode_combo = QComboBox()
        self._mode_combo.setStyleSheet("font-size: 10px;")
        self._mode_combo.setMinimumWidth(100)
        self._mode_combo.addItem("输出图集", "output")
        self._mode_combo.addItem("输入图集", "input")
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        toolbar.addWidget(QLabel("显示:"))
        toolbar.addWidget(self._mode_combo)
        toolbar.addStretch()
        self._count_label = QLabel("")
        toolbar.addWidget(self._count_label)
        layout.addLayout(toolbar)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._set_container = QWidget()
        self._set_layout = QVBoxLayout(self._set_container)
        self._set_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._set_layout.setSpacing(6)
        self._scroll_area.setWidget(self._set_container)
        layout.addWidget(self._scroll_area, 1)

        self._placeholder = QLabel("暂无图像数据\n\n请搭建节点并点击 ▶ 开始 执行")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(self._placeholder)

        self._refresh_display()

    def _init_ruler_overlay(self):
        # RulerOverlay uses a map_fn callable for coordinate mapping,
        # decoupled from the parent widget hierarchy.
        self._ruler_overlay = RulerOverlay(
            parent=self,
            map_fn=self.map_to_image,
        )
        self._ruler_overlay.hide()
        self._ruler_overlay.measurement_added.connect(self._on_ruler_measurement)
        self._ruler_overlay.measurement_cleared.connect(self._on_ruler_cleared)

    def toggle_ruler(self):
        self._ruler_enabled = not self._ruler_enabled
        if self._ruler_enabled:
            self._update_ruler_overlay_geometry()
            self._ruler_overlay.set_visible(True)
            self._ruler_overlay.raise_()
        else:
            self._ruler_overlay.set_visible(False)
        return self._ruler_enabled

    def _update_ruler_overlay_geometry(self):
        viewport = self._scroll_area.viewport()
        pos = viewport.mapTo(self, QPoint(0, 0))
        self._ruler_overlay.setGeometry(
            pos.x(), pos.y(),
            viewport.width(), viewport.height(),
        )

    def clear_ruler(self):
        self._ruler_overlay.clear_measurements()

    # ------------------------------------------------------------------
    # Coordinate mapping — delegates scale calculation to DisplayInfo
    # ------------------------------------------------------------------

    def map_to_image(
        self, overlay_x: float, overlay_y: float
    ) -> tuple[int, int] | None:
        """Map a ruler overlay coordinate to image pixel coordinates.

        The overlay-local (x,y) is converted to global space, matched
        against visible ImageSetWidget labels, and then the centering
        offset + DisplayInfo.map_to_image() does the actual mapping.
        """
        click_global = self._ruler_overlay.mapToGlobal(
            QPoint(int(overlay_x), int(overlay_y))
        )

        for widget in self._set_widgets:
            if not widget.isVisible():
                continue

            label = widget._img_label
            label_global = label.mapToGlobal(QPoint(0, 0))
            label_rect = QRect(label_global, label.size())

            if not label_rect.contains(click_global):
                continue

            display_info = widget.get_display_info()
            if display_info is None:
                continue

            rect = widget.get_pixmap_rect_in_label()
            if rect is None:
                continue
            offset_x, offset_y, disp_w, disp_h = rect

            # Convert label-local coords to pixmap-local coords
            local_x = click_global.x() - label_global.x()
            local_y = click_global.y() - label_global.y()
            pixmap_x = local_x - offset_x
            pixmap_y = local_y - offset_y

            # Delegate to DisplayInfo — single source of truth
            result = display_info.map_to_image(pixmap_x, pixmap_y)
            if result is not None:
                logger.debug(
                    f"[map_to_image] label=({label.width()},{label.height()}) "
                    f"display=({disp_w},{disp_h}) "
                    f"actual=({display_info.actual_w},{display_info.actual_h}) "
                    f"pixmap_pos=({pixmap_x:.1f},{pixmap_y:.1f}) "
                    f"→ image=({result[0]},{result[1]})"
                )
                return result

        return None

    def get_current_image_info(self) -> dict | None:
        for widget in self._set_widgets:
            if widget.isVisible():
                di = widget.get_display_info()
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

    def _on_ruler_cleared(self):
        pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._ruler_enabled:
            self._update_ruler_overlay_geometry()

    def set_execution_results(self, result: ExecutionResult):
        self._result = result
        logger.info(
            f"ImageViewer: received {len(result.input_sets)} input sets, "
            f"{len(result.output_sets)} output sets"
        )
        current_sets = self._get_current_sets()
        total = sum(len(s.images) for s in current_sets)
        self._count_label.setText(f"{len(current_sets)} 组 / {total} 张")
        # Don't clear ruler on every result — loop mode would wipe measurements
        self._refresh_display()

    def _get_current_sets(self):
        if self._current_mode == "output":
            return self._result.output_sets
        return self._result.input_sets

    def _on_mode_changed(self, index):
        self._current_mode = self._mode_combo.itemData(index)
        self.clear_ruler()
        self._rebuild_display()

    def _refresh_display(self):
        sets = self._get_current_sets()
        total = sum(len(s.images) for s in sets)
        self._count_label.setText(f"{len(sets)} 组 / {total} 张")

        if not sets:
            for w in self._set_widgets:
                w.hide()
            self._placeholder.show()
            self._scroll_area.hide()
            return

        self._placeholder.hide()
        self._scroll_area.show()

        for i, s in enumerate(sets):
            if i < len(self._set_widgets):
                self._set_widgets[i].update_images(s.name, s.images)
                self._set_widgets[i].show()
            else:
                widget = ImageSetWidget(
                    s.name, s.images, self._image_display
                )
                widget.image_changed.connect(self.clear_ruler)
                self._set_layout.addWidget(widget)
                self._set_widgets.append(widget)

        for i in range(len(sets), len(self._set_widgets)):
            self._set_widgets[i].hide()

    def _rebuild_display(self):
        for w in self._set_widgets:
            w.deleteLater()
        self._set_widgets.clear()

        while self._set_layout.count():
            child = self._set_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        sets = self._get_current_sets()
        total = sum(len(s.images) for s in sets)
        self._count_label.setText(f"{len(sets)} 组 / {total} 张")

        if not sets:
            self._placeholder.show()
            self._scroll_area.hide()
            return

        self._placeholder.hide()
        self._scroll_area.show()

        for s in sets:
            widget = ImageSetWidget(s.name, s.images, self._image_display)
            widget.image_changed.connect(self.clear_ruler)
            self._set_layout.addWidget(widget)
            self._set_widgets.append(widget)
