"""Pytest configuration and shared fixtures."""

import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance (shared across entire test session)."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def graphics_view(qapp):
    """Create a ZoomableGraphicsView instance for testing."""
    from ui.widgets.zoomable_graphics_view import ZoomableGraphicsView

    gv = ZoomableGraphicsView()
    gv.resize(400, 300)
    gv.show()
    yield gv
    gv.close()


@pytest.fixture
def scene_with_image(graphics_view, qapp):
    """Create a QGraphicsScene with a test image."""
    from PySide6.QtGui import QPixmap, QImage
    from PySide6.QtCore import QRectF

    # Create a simple 100x100 test image
    image = QImage(100, 100, QImage.Format.Format_RGB32)
    image.fill(0xFF8800)  # Orange
    pixmap = QPixmap.fromImage(image)

    from PySide6.QtWidgets import QGraphicsScene
    scene = QGraphicsScene()
    scene.addPixmap(pixmap)
    scene.setSceneRect(QRectF(pixmap.rect()))
    graphics_view.setScene(scene)
    graphics_view.fitInView(scene.sceneRect())

    return graphics_view


@pytest.fixture
def coordinate_mapper(scene_with_image):
    """Create a CoordinateMapper with a view that has a test image."""
    from ui.widgets.coordinate_mapper import CoordinateMapper

    mapper = CoordinateMapper(scene_with_image)
    mapper.update_image_size(100, 100)
    return mapper


@pytest.fixture
def event_guard():
    """Create an EventGuard instance."""
    from ui.widgets.event_guard import EventGuard
    return EventGuard()
