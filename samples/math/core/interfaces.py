"""Core interfaces — contracts between systems and UI.

Defines what UI code can depend on without coupling to concrete
system implementations. Enables testing and swapping implementations.

All interfaces are zero-dependency on Qt/cv2 — they define pure Python
contracts. Concrete implementations may import framework types.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


# ------------------------------------------------------------------
# Result display (generic — works for images, text, data, etc.)
# ------------------------------------------------------------------

class IResultDisplayProvider(ABC):
    """Contract for displaying execution results.

    Generic interface that works with any data type.
    Concrete implementations handle type-specific rendering.
    """

    @abstractmethod
    def display_result(self, data: Any) -> bool:
        """Display result data. Returns True if successful.

        Args:
            data: The data to display (image, text, table, etc.)
        """
        ...

    @abstractmethod
    def clear(self):
        """Clear the display."""
        ...


# ------------------------------------------------------------------
# Image display (optional — for image-specific tools)
# ------------------------------------------------------------------

class IImageDisplayProvider(IResultDisplayProvider):
    """Extended contract for image display with coordinate mapping.

    Inherits from IResultDisplayProvider. Only implement this if your
    tool needs image display with zoom/pan/coordinate features.
    """

    @abstractmethod
    def convert_to_qpixmap(self, img, max_size=None, color_space="bgr"):
        """Convert a numpy image to a displayable pixmap."""
        ...

    @abstractmethod
    def compute_display_info(self, img, max_width=400, max_height=280):
        """Compute display info for coordinate mapping."""
        ...

    @abstractmethod
    def get_current_display_info(self):
        """Return the most recently computed DisplayInfo, or None."""
        ...

    @abstractmethod
    def map_to_image(self, display_x: float, display_y: float):
        """Map display coordinates to image pixel coordinates."""
        ...


# ------------------------------------------------------------------
# Node graph / blueprint
# ------------------------------------------------------------------

class INodeGraphProvider(ABC):
    """Contract for node graph operations.

    Implemented by BlueprintSystem. Consumed by MainWindow,
    NodeGraphWidget, and NodeSelectorWindow.
    """

    @abstractmethod
    def create_node(self, node_id: str, pos=None):
        """Create a graph node of the given type at the given position.

        Args:
            node_id: The node type identifier (e.g. 'image_source/camera').
            pos: Optional (x, y) tuple for the node's position.

        Returns:
            The created graph node, or None on failure.
        """
        ...

    @abstractmethod
    def delete_node(self, node_name: str) -> bool:
        """Delete a graph node by name.

        Returns True if the node was found and deleted, False otherwise.
        """
        ...

    @abstractmethod
    def extract_pipeline(self) -> list:
        """Extract PipelineNodeInfo list from the current graph.

        Returns a list of PipelineNodeInfo for execution.
        """
        ...

    @abstractmethod
    def get_category_tree(self):
        """Get the node category tree for building UI context menus.

        Returns a dict[str, CategoryNode] where each CategoryNode has
        .subcategories (dict) and .items (list of NodeMeta).
        """
        ...


# ------------------------------------------------------------------
# Execution
# ------------------------------------------------------------------

class IExecutionProvider(ABC):
    """Contract for pipeline execution.

    Implemented by ExecutionEngine (systems/execution/engine.py).
    Consumed by MainWindow for triggering and monitoring execution.

    EventEmitter attributes (not enforced by ABC — instance attributes
    set in __init__):

        on_started:           EventEmitter()  — fired when execution begins
        on_finished:          EventEmitter(result: ExecutionResult)
        on_progress:          EventEmitter(current: int, total: int)
        on_node_state_changed:EventEmitter(name: str, state: str)
    """

    @abstractmethod
    def execute(self, graph) -> None:
        """Start pipeline execution on a background thread.

        Args:
            graph: The NodeGraphQt graph containing nodes to execute.
        """
        ...

    @abstractmethod
    def cancel(self) -> None:
        """Cancel the current execution (thread-safe)."""
        ...
