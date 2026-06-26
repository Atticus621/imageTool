"""Core interfaces — contracts between systems and UI.

Defines what UI code can depend on without coupling to concrete
system implementations. Enables testing and swapping implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.events import EventEmitter


# ------------------------------------------------------------------
# Image display
# ------------------------------------------------------------------

class IImageDisplayProvider(ABC):
    """Contract for converting images to displayable formats."""

    @abstractmethod
    def convert_to_qpixmap(self, img, max_size=None):
        """Convert a numpy image to QPixmap."""
        ...

    @abstractmethod
    def compute_display_info(self, img, max_width=400, max_height=280):
        """Compute DisplayInfo for coordinate mapping."""
        ...

    @abstractmethod
    def map_to_image(self, display_x: float, display_y: float):
        """Map display-space coordinates to image pixels."""
        ...


# ------------------------------------------------------------------
# Node graph / blueprint
# ------------------------------------------------------------------

class INodeGraphProvider(ABC):
    """Contract for node graph operations."""

    @abstractmethod
    def create_node(self, node_id: str, pos=None):
        """Create a graph node of the given type."""
        ...

    @abstractmethod
    def delete_node(self, node_name: str) -> bool:
        """Delete a graph node by name."""
        ...

    @abstractmethod
    def extract_pipeline(self) -> list:
        """Extract pipeline info for execution."""
        ...

    @abstractmethod
    def get_category_tree(self) -> dict:
        """Get node category tree for UI menus."""
        ...


# ------------------------------------------------------------------
# Execution
# ------------------------------------------------------------------

class IExecutionProvider(ABC):
    """Contract for pipeline execution."""

    @property
    @abstractmethod
    def on_started(self) -> EventEmitter: ...

    @property
    @abstractmethod
    def on_finished(self) -> EventEmitter: ...

    @property
    @abstractmethod
    def on_progress(self) -> EventEmitter: ...

    @property
    @abstractmethod
    def on_node_state_changed(self) -> EventEmitter: ...

    @abstractmethod
    def execute(self, graph) -> None: ...

    @abstractmethod
    def cancel(self) -> None: ...
