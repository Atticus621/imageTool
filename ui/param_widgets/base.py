"""ParamWidget — abstract base class for parameter widget handlers.

Each ParamType gets its own subclass implementing the standard interface:
create_widget, get_value, set_value. The __init_subclass__ hook auto-registers
every subclass into _PARAM_WIDGET_REGISTRY, so NodeSelectorWindow never needs
to know about specific types.

Adding a new parameter type is now:
    1. Create a new file in this package with a ParamWidget subclass
    2. Set ``param_type = ParamType.NEW_TYPE`` as a class attribute
    3. Import it in __init__.py
    → Zero changes to NodeSelectorWindow.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from PySide6.QtCore import Signal

from core.node_base.node import ParamType, ParamDefinition


_PARAM_WIDGET_REGISTRY: dict[ParamType, type[ParamWidget]] = {}


class ParamWidget(ABC):
    """Strategy for one parameter type: create widget, read/write value, react to dependencies.

    Subclasses MUST set ``param_type`` as a class attribute.
    ``__init_subclass__`` auto-registers the subclass into the global registry.
    """

    param_type: ParamType

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        if cls.param_type is not None:
            _PARAM_WIDGET_REGISTRY[cls.param_type] = cls

    def __init__(self, param: ParamDefinition) -> None:
        self.param = param
        self._widget: QWidget | None = None  # type: ignore[name-defined]

    @property
    def widget(self):
        """The Qt widget created by create_widget()."""
        return self._widget

    # ── Core interface (must override) ──────────────────────────────

    @abstractmethod
    def create_widget(self):
        """Build and return the Qt widget. Stored internally as self._widget.

        Called once, after __init__.
        """
        ...

    @abstractmethod
    def get_value(self) -> Any:
        """Read and return the current value from the widget."""
        ...

    @abstractmethod
    def set_value(self, value: Any) -> None:
        """Write a value into the widget (e.g. during edit mode pre-population)."""
        ...

    # ── Layout control ──────────────────────────────────────────────

    def needs_own_label(self) -> bool:
        """Return True if this widget renders its own label internally.

        When True, the grid layout spans the widget across both columns
        (no separate QLabel is added in column 0).

        Only ``ChannelRangeParamWidget`` overrides this.
        """
        return False

    # ── Dependency hook ─────────────────────────────────────────────

    def on_dependency_change(self, source_name: str, source_value: Any) -> bool:
        """Called when a parameter this widget ``depends_on`` changes value.

        Subclasses override to implement dynamic behaviour:
        - Visibility toggling
        - Label updates
        - Option list repopulation
        - Range min/max updates

        Args:
            source_name: The name of the source param (the ``depends_on`` value).
            source_value: The source param's current value.

        Returns:
            True if this widget handled the change.
        """
        return False

    # ── Change notification ─────────────────────────────────────────

    def get_value_changed_signal(self) -> Signal | None:  # type: ignore[valid-type]
        """Return a Qt Signal that emits when this widget's value changes.

        Used by the dependency system to know when to call
        ``on_dependency_change`` on dependent widgets.

        Returns None if the widget doesn't support change notification
        (dependency wiring will be skipped for it).
        """
        return None


def get_widget_class(param_type: ParamType) -> type[ParamWidget] | None:
    """Look up the registered ParamWidget class for a ParamType."""
    return _PARAM_WIDGET_REGISTRY.get(param_type)


def create_param_widget(param: ParamDefinition) -> ParamWidget | None:
    """Factory: instantiate and build the ParamWidget for a ParamDefinition.

    Returns None if the param type is not registered.
    """
    cls = _PARAM_WIDGET_REGISTRY.get(param.param_type)
    if cls is None:
        return None
    handler = cls(param)
    handler.create_widget()
    return handler
