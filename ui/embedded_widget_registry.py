"""Embedded widget registry — decorator-based factory registration.

Usage::

    @EmbeddedWidgetRegistry.register("processing/statistics/histogram")
    def _create_histogram(node):
        from ui.widgets.node_histogram_widget import NodeHistogramWidget
        widget = EmbeddedWidgetRegistry.create_widget(node, NodeHistogramWidget)
        node.add_embedded_widget(widget)
"""


class EmbeddedWidgetRegistry:
    """Registry mapping node type IDs to embedded-widget factory functions.

    Factory signature:  fn(node: GraphNode) -> None
    The factory is responsible for creating the widget and calling
    node.add_embedded_widget().
    """

    _factories: dict[str, callable] = {}

    @classmethod
    def register(cls, node_id: str):
        """Decorator: register a factory function for a node type.

        Args:
            node_id: Node type identifier (e.g. "processing/statistics/histogram").
        """
        def decorator(fn):
            cls._factories[node_id] = fn
            return fn
        return decorator

    @classmethod
    def create_widget(cls, node, widget_class, **kwargs):
        """Create an embedded widget with correct parent initialization.

        This is the standard factory method for creating embedded widgets.
        It ensures the widget is created with parent=node.view, which is
        required for the widget to be visible on the node.

        Args:
            node: GraphNode instance.
            widget_class: The NodeBaseWidget subclass to create.
            **kwargs: Additional keyword arguments passed to the widget constructor.

        Returns:
            An instance of widget_class with parent=node.view.
        """
        parent = getattr(node, 'view', None)
        return widget_class(parent=parent, **kwargs)

    @classmethod
    def create(cls, node_id: str, node) -> bool:
        """Create and attach an embedded widget for a node.

        Args:
            node_id: Node type identifier.
            node: GraphNode instance.

        Returns:
            True if a widget was created, False otherwise.
        """
        from core.logger import logger

        factory = cls._factories.get(node_id)
        if factory is not None:
            logger.info(f"[EmbeddedWidget] Using custom factory for {node_id}")
            factory(node)
            return True

        return False

    @classmethod
    def has_factory(cls, node_id: str) -> bool:
        return node_id in cls._factories
