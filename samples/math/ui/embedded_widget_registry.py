"""Embedded widget registry — decorator-based factory registration + auto-pin.

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

    Also supports auto-pinning: if no custom factory is registered,
    the system checks for pinned parameters and auto-generates widgets.
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

        # 1. Check for custom factory first
        factory = cls._factories.get(node_id)
        if factory is not None:
            logger.info(f"[EmbeddedWidget] Using custom factory for {node_id}")
            factory(node)
            return True

        # 2. Auto-pin: check for pinned parameters
        logger.debug(f"[EmbeddedWidget] No factory for {node_id}, trying auto-pin")
        return cls._auto_pin(node)

    @classmethod
    def _auto_pin(cls, node) -> bool:
        """Auto-create pinned widgets for parameters with pinned=True."""
        from core.node_base.registry import node_registry
        from core.logger import logger
        from ui.widgets.pinned_param_widget import PinnedComboWidget, PinnedCheckboxWidget, PinnedSliderWidget
        from core.node_base.node import ParamType

        node_id = getattr(node, "_node_id", "")
        meta = node_registry.get_meta(node_id)
        if meta is None:
            logger.warning(f"[AutoPin] No meta found for node_id: {node_id}")
            return False

        pinned_params = [p for p in meta.params if p.pinned]
        if not pinned_params:
            logger.debug(f"[AutoPin] No pinned params for {node_id}")
            return False

        logger.info(f"[AutoPin] Found {len(pinned_params)} pinned params for {node_id}")

        # Use the last pinned widget as the embedded widget
        last_widget = None
        for param in pinned_params:
            widget = None
            if param.param_type == ParamType.COMBO:
                widget = cls.create_widget(node, PinnedComboWidget,
                    param_name=param.name, label=param.label,
                    options=param.options, default=param.default)
            elif param.param_type == ParamType.CHECKBOX:
                widget = cls.create_widget(node, PinnedCheckboxWidget,
                    param_name=param.name, label=param.label,
                    default=bool(param.default))
            elif param.param_type in (ParamType.INT_SLIDER, ParamType.FLOAT_SLIDER):
                is_float = (param.param_type == ParamType.FLOAT_SLIDER)
                widget = cls.create_widget(node, PinnedSliderWidget,
                    param_name=param.name, label=param.label,
                    default=param.default,
                    min_val=param.min_val or 0, max_val=param.max_val or 100,
                    step=param.step or (0.1 if is_float else 1), is_float=is_float)

            if widget is not None:
                last_widget = widget
                if param.default is not None:
                    node._param_values[param.name] = param.default
                # Sync widget → node._param_values
                widget.valueChanged.connect(
                    lambda value, n=node, p=param.name: n._param_values.__setitem__(p, value)
                )
                logger.info(f"[AutoPin] Created widget: {type(widget).__name__} for param: {param.name}")

        if last_widget is not None:
            node.add_embedded_widget(last_widget)
            logger.info(f"[AutoPin] Added embedded widget to {node_id}")

        return True

    @classmethod
    def has_factory(cls, node_id: str) -> bool:
        return node_id in cls._factories
