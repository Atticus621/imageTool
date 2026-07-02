"""Core interfaces — contracts between systems and UI.

Defines what UI code can depend on without coupling to concrete
system implementations. Enables testing and swapping implementations.

All interfaces are zero-dependency on Qt/cv2 — they define pure Python
contracts. Concrete implementations may import framework types.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


# ------------------------------------------------------------------
# Image display
# ------------------------------------------------------------------

class IImageDisplayProvider(ABC):
    """Contract for converting images to displayable formats and
    coordinate mapping.

    Implemented by ImageDisplaySystem. Consumed by ImageViewerWidget,
    ImageSetWidget, and RulerSystem.
    """

    @abstractmethod
    def convert_to_qpixmap(self, img, max_size=None, color_space="bgr"):
        """Convert a numpy image to a displayable pixmap.

        Args:
            img: numpy array image.
            max_size: Optional max size constraint (framework-specific).
            color_space: The color space of the input image (default "bgr").

        Returns:
            A framework-native pixmap object.
        """
        ...

    @abstractmethod
    def compute_display_info(self, img, max_width=400, max_height=280):
        """Compute DisplayInfo for an image given display constraints.

        Stores the result as the current display info for subsequent
        coordinate mapping queries.

        Args:
            img: numpy array source image.
            max_width: Maximum display width in logical pixels.
            max_height: Maximum display height in logical pixels.

        Returns:
            DisplayInfo with actual and display dimensions.
        """
        ...

    @abstractmethod
    def get_current_display_info(self):
        """Return the most recently computed DisplayInfo, or None.

        Used by RulerSystem to access scale factors without re-computing.
        """
        ...

    @abstractmethod
    def map_to_image(self, display_x: float, display_y: float):
        """Map a display-pixmap coordinate to image pixel coordinates.

        Uses the current DisplayInfo. Returns None if no image is
        displayed or the coordinate is out of bounds.

        Args:
            display_x: X position within the displayed pixmap.
            display_y: Y position within the displayed pixmap.

        Returns:
            (image_x, image_y) tuple of ints, or None.
        """
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
    def get_category_tree(self) -> dict:
        """Get the node category tree for building UI context menus.

        Returns a nested dict: {category_name: {subcategory_name: [NodeMeta, ...]}}.
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
