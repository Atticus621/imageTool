"""Simulation API — send synthetic input events to widgets for remote debugging.

Endpoints allow external tools (or manual curl) to simulate mouse wheel,
click, and move events so that event-handling paths can be exercised and
logged without a physical mouse.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.logger import logger

router = APIRouter(prefix="/api/v1/simulation", tags=["simulation"])


# ------------------------------------------------------------------
# Widget registry — MainWindow registers widgets at startup
# ------------------------------------------------------------------

_widget_registry: dict[str, Any] = {}


def register_widget(name: str, widget: Any) -> None:
    """Register a widget for simulation targeting."""
    _widget_registry[name] = widget
    logger.info(f"[Simulation] Registered widget: {name}")


def get_widget(name: str) -> Any | None:
    return _widget_registry.get(name)


def _resolve_target(widget: Any) -> Any:
    """Resolve a registered widget to the actual event target.

    If the widget is a container (like ImageViewerWidget), find the
    first visible QGraphicsView inside it.  Otherwise return as-is.
    """
    # If it's already a QGraphicsView-like (has viewport()), use it directly
    if hasattr(widget, "viewport") and hasattr(widget, "scene"):
        return widget

    # Try to find a QGraphicsView child
    from PySide6.QtWidgets import QGraphicsView
    views = widget.findChildren(QGraphicsView)
    for view in views:
        if view.isVisible():
            return view

    # Fallback — return the widget itself
    return widget


# ------------------------------------------------------------------
# Request models
# ------------------------------------------------------------------

class WheelRequest(BaseModel):
    target: str = "image_viewer"
    delta: int = 120
    x: int | None = None
    y: int | None = None


class MoveRequest(BaseModel):
    target: str = "image_viewer"
    x: int = 0
    y: int = 0


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.get("/widgets")
def list_widgets():
    """List registered simulation targets."""
    return {
        "success": True,
        "data": list(_widget_registry.keys()),
    }


@router.post("/wheel")
def simulate_wheel(req: WheelRequest):
    """Simulate a mouse wheel event on a registered widget.

    The event is posted to the Qt event loop via QApplication.postEvent,
    so it arrives on the main thread even though this handler runs on
    the uvicorn thread.
    """
    registered = get_widget(req.target)
    if registered is None:
        raise HTTPException(
            status_code=404,
            detail=f"Widget '{req.target}' not registered. "
                   f"Available: {list(_widget_registry.keys())}",
        )

    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtCore import QPointF, QPoint, Qt

    widget = _resolve_target(registered)
    viewport = widget.viewport() if hasattr(widget, "viewport") else widget
    if req.x is not None and req.y is not None:
        local_pos = QPointF(req.x, req.y)
    else:
        center = viewport.rect().center()
        local_pos = QPointF(center)

    global_pos = viewport.mapToGlobal(local_pos.toPoint())

    event = QWheelEvent(
        local_pos,              # pos
        global_pos,             # globalPos
        QPoint(0, 0),          # pixelDelta (unknown)
        QPoint(0, req.delta),  # angleDelta
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,                 # inverted
    )

    QApplication.postEvent(viewport, event)
    logger.info(
        f"[Simulation] Wheel event posted to '{req.target}': "
        f"delta={req.delta}, pos=({local_pos.x():.0f},{local_pos.y():.0f})"
    )

    return {
        "success": True,
        "data": {
            "target": req.target,
            "delta": req.delta,
            "pos": {"x": local_pos.x(), "y": local_pos.y()},
        },
    }


@router.post("/move")
def simulate_move(req: MoveRequest):
    """Simulate a mouse move event on a registered widget."""
    registered = get_widget(req.target)
    if registered is None:
        raise HTTPException(
            status_code=404,
            detail=f"Widget '{req.target}' not registered.",
        )

    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtCore import QPointF, QEvent, Qt

    widget = _resolve_target(registered)
    viewport = widget.viewport() if hasattr(widget, "viewport") else widget
    local_pos = QPointF(req.x, req.y)
    global_pos = viewport.mapToGlobal(local_pos.toPoint())

    event = QMouseEvent(
        QEvent.Type.MouseMove,
        local_pos,
        global_pos,
        Qt.MouseButton.NoButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )

    QApplication.postEvent(viewport, event)
    logger.info(
        f"[Simulation] Move event posted to '{req.target}': "
        f"pos=({req.x},{req.y})"
    )

    return {
        "success": True,
        "data": {"target": req.target, "x": req.x, "y": req.y},
    }
