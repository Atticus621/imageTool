"""NodeGraphQt library bug workarounds.

All monkey-patches, private-API access, and library defect compensations
MUST live in this file.  Business logic belongs in handlers/ -- this module
only provides low-level helper functions to work around known library issues.

Every public function documents:
  1. Which library bug it works around
  2. Symptoms when the workaround is NOT applied
  3. What code paths it affects
"""

import warnings

from PySide6.QtCore import Qt

from NodeGraphQt.nodes.port_node import PortInputNode, PortOutputNode
from NodeGraphQt.qgraphics.node_base import NodeItem

from core.logger import logger


# ──────────────────────────────────────────────────────────────────────
# Workaround 1: double-click on port node labels does nothing
# ──────────────────────────────────────────────────────────────────────

_orig_node_item_dbl_click = NodeItem.mouseDoubleClickEvent


def _patched_node_item_dbl_click(self, event):
    """See apply_double_click_unlock_patch() for rationale."""
    if event.button() == Qt.LeftButton:
        if not self.disabled:
            items = self.scene().items(event.scenePos())
            if self._text_item in items:
                self._text_item.set_locked(False)   # unlock port nodes
                self._text_item.set_editable(True)
                self._text_item.setFocus()
                event.ignore()
                return
        viewer = self.viewer()
        if viewer:
            viewer.node_double_clicked.emit(self.id)
    return _orig_node_item_dbl_click(self, event)


def apply_double_click_unlock_patch():
    """Monkey-patch NodeItem.mouseDoubleClickEvent to unlock port node text.

    Library bug:
        PortInputNodeItem / PortOutputNodeItem call _text_item.set_locked(True)
        in __init__.  QGraphicsTextItem with NoTextInteraction ignores
        mousePressEvent, so the press falls through to the parent NodeItem.
        NodeItem.mouseDoubleClickEvent then calls set_editable(True) which is
        a no-op for locked text items.  Result: double-clicking a port node
        label does nothing (cannot rename).

    Symptoms without this patch:
        Double-clicking "输入1"/"输出1" labels on port nodes inside a
        sub-blueprint has no effect.  Only the right-click context menu
        "重命名端口" works (via QInputDialog fallback).

    Affected code paths:
        - User double-clicks PortInputNode / PortOutputNode label
        - NodeItem.mouseDoubleClickEvent (inherited by PortInputNodeItem
          and PortOutputNodeItem)
    """
    NodeItem.mouseDoubleClickEvent = _patched_node_item_dbl_click
    logger.info("[Workaround] Applied double-click unlock patch on NodeItem")


def revert_double_click_unlock_patch():
    """Restore original mouseDoubleClickEvent (for testing)."""
    NodeItem.mouseDoubleClickEvent = _orig_node_item_dbl_click


# ──────────────────────────────────────────────────────────────────────
# Workaround 2: GroupNode ports disappear after deserialization
# ──────────────────────────────────────────────────────────────────────

def _resolve_port_name(dict_key, port_model, existing_names):
    """Return (effective_name, needs_rekey) for a model.inputs/outputs entry.

    The dict key may be stale after a port rename (see sync_port_name_to_group).
    Prefer port_model.name over the dict key; if they differ and port_model.name
    is already a live port, skip creation entirely (defense-in-depth).
    """
    model_name = getattr(port_model, 'name', None)
    if model_name and model_name != dict_key:
        if model_name in existing_names:
            return None, False  # already exists → skip
        return model_name, True  # use model name, needs rekey
    return dict_key, False


def rebuild_group_node_ports(group_node):
    """Rebuild Port objects from model data after deserialization.

    Library bug:
        When a GroupNode is deserialized (loaded from file or from a parent
        SubGraph session), port DATA is correctly restored in model.inputs /
        model.outputs (PortModel dicts), but the actual Port objects in
        node._inputs / node._outputs lists are NOT recreated.  This means:
          - group_node.input_ports() returns [] (empty)
          - group_node.output_ports() returns [] (empty)
          - The GroupNode has no visible port dots
          - _build_port_nodes() creates no port nodes → SubGraph is empty

    Additionally defends against stale dict keys caused by port renames:
    if a PortModel.name differs from its dict key, the model name takes
    precedence and the dict is re-keyed.  This prevents duplicate ports
    when loading projects saved before the sync_port_name_to_group fix.

    Symptoms without this workaround:
        After collapsing and re-expanding a nested sub-blueprint, the
        GroupNode's ports disappear and the SubGraph cannot be reopened
        (the expand operation creates an empty SubGraph with no port nodes).

    Affected code paths:
        - MainWindow._on_node_double_clicked() → GroupNode expand
        - SubGraph._deserialize() → _build_port_nodes()

    Args:
        group_node: A NodeGraphQt.GroupNode that may have been deserialized.
    """
    model_inputs = group_node.model.inputs
    model_outputs = group_node.model.outputs
    existing_in = {p.name() for p in group_node.input_ports()}
    existing_out = {p.name() for p in group_node.output_ports()}

    for dict_key in list(model_inputs.keys()):
        pm = model_inputs[dict_key]
        name, needs_rekey = _resolve_port_name(dict_key, pm, existing_in)
        if name is None:
            continue  # port already exists under its model name → skip
        if name not in existing_in:
            mc = getattr(pm, 'multi_connection', False)
            dn = getattr(pm, 'display_name', True)
            group_node.add_input(name, multi_input=mc, display_name=dn)
        if needs_rekey:
            model_inputs[name] = model_inputs.pop(dict_key)

    for dict_key in list(model_outputs.keys()):
        pm = model_outputs[dict_key]
        name, needs_rekey = _resolve_port_name(dict_key, pm, existing_out)
        if name is None:
            continue
        if name not in existing_out:
            mc = getattr(pm, 'multi_connection', False)
            dn = getattr(pm, 'display_name', True)
            group_node.add_output(name, multi_output=mc, display_name=dn)
        if needs_rekey:
            model_outputs[name] = model_outputs.pop(dict_key)

    group_node.view.draw_node()


# ──────────────────────────────────────────────────────────────────────
# Workaround 3: expand_group_node raises KeyError on stale session
# ──────────────────────────────────────────────────────────────────────

def expand_group_node_with_retry(parent_graph, group_node):
    """Expand a GroupNode, retrying with a cleared session on KeyError.

    Library bug:
        SubGraph.expand_group_node deserializes the saved session from
        group_node.get_sub_graph_session().  If the serialized session
        contains PortInputNode / PortOutputNode references that don't match
        the GroupNode's current ports (e.g. after an earlier rename), the
        _deserialize → _build_port_nodes lookup fails with KeyError.

    Symptoms without this workaround:
        KeyError on port name lookup (e.g. '输入1') when expanding a
        previously expanded & collapsed GroupNode.  The exception bubbles
        up to the double-click handler and the SubGraph never opens.

    Affected code paths:
        - MainWindow._on_node_double_clicked() → parent_graph.expand_group_node()

    Args:
        parent_graph: The graph containing the GroupNode (NodeGraph or SubGraph).
        group_node: The GroupNode to expand.

    Returns:
        SubGraph instance, or None on failure.
    """
    try:
        return parent_graph.expand_group_node(group_node)
    except KeyError:
        logger.warning(
            f"Stale session for group node '{group_node.name()}', "
            f"clearing session and retrying"
        )
        group_node.set_sub_graph_session({})
        return parent_graph.expand_group_node(group_node)


# ──────────────────────────────────────────────────────────────────────
# Workaround 4: Port has no set_name() method
# ──────────────────────────────────────────────────────────────────────

def get_group_view_text_item(group_view, port_item):
    """Safely find the QGraphicsTextItem associated with a port.

    NodeGraphQt stores port labels as QGraphicsTextItem children inside
    private dicts group_view._input_items and group_view._output_items.
    This function wraps that private access in one place.

    Args:
        group_view: A GroupNodeItem (or NodeItem subclass).
        port_item: A PortItem whose label text item we want.

    Returns:
        QGraphicsTextItem or None.
    """
    return (group_view._input_items.get(port_item) or
            group_view._output_items.get(port_item))


def sync_port_name_to_group(parent_port, new_name):
    """Sync a port name change from a SubGraph port node to the parent GroupNode.

    Library bug:
        NodeGraphQt.Port has a name() getter (returns port.model.name) but
        NO set_name() setter.  When a PortInputNode / PortOutputNode inside
        a SubGraph is renamed, the change must be manually propagated:
          1. Update the Port data model (port.model.name)
          2. Update the PortItem graphics (port.view.name)
          3. Update the QGraphicsTextItem label in the GroupNode view
          4. Redraw the GroupNode to realign port positions

    Additionally, BaseNode.add_input / add_output store the PortModel in
    model.inputs / model.outputs dicts keyed by the *original* port name
    (see base_node.py line 458, 500).  If we don't re-key the dict entry
    after a rename, rebuild_group_node_ports will see the old key as a
    "missing" port and create a duplicate (e.g. renaming "输入1" → "自定义"
    leaves {"输入1": PortModel(name="自定义")} in the dict, so
    rebuild_group_node_ports creates a second "输入1" port on next expand).

    Symptoms without this workaround:
        AttributeError: 'Port' object has no attribute 'set_name'.
        The port name changes inside the SubGraph but the GroupNode's port
        label on the outside stays the old name.
        After renaming a sub-blueprint input, exiting and re-entering the
        sub-blueprint auto-generates a duplicate port with the old name.

    Affected code paths:
        - PortInputNode / PortOutputNode rename → sub_graph.property_changed
          → _on_sub_graph_property_changed

    Args:
        parent_port: The NodeGraphQt.Port object on the parent GroupNode.
        new_name: The new name to apply.
    """
    old_name = parent_port.model.name
    group_node = parent_port.node()

    # 1. Update the port data model
    parent_port.model.name = new_name
    # 2. Update the PortItem (graphics object)
    parent_port.view.name = new_name
    # 3. Fix the model.inputs / model.outputs dict key so
    #    rebuild_group_node_ports doesn't re-create a duplicate port
    #    under the old name (see docstring for details).
    if old_name != new_name:
        if parent_port in group_node.input_ports():
            port_dict = group_node.model.inputs
        elif parent_port in group_node.output_ports():
            port_dict = group_node.model.outputs
        else:
            logger.warning(
                f"sync_port_name_to_group: parent_port not found in "
                f"input_ports() or output_ports() of '{group_node.name()}'"
            )
            port_dict = None
        if port_dict is not None and old_name in port_dict:
            port_dict[new_name] = port_dict.pop(old_name)
    # 4. Update the displayed label text in the GroupNode view
    group_view = group_node.view
    port_item = parent_port.view
    text_item = get_group_view_text_item(group_view, port_item)
    if text_item:
        text_item.setPlainText(new_name)
    # 5. Redraw to realign port positions after text size change
    group_view.draw_node()


def is_port_rename_event(node, prop_name):
    """Check if a sub-graph property change is a port node rename.

    Args:
        node: The node whose property changed.
        prop_name: The property name that changed.

    Returns:
        bool: True if this is a port node name change that should be synced.
    """
    return (prop_name == "name" and
            isinstance(node, (PortInputNode, PortOutputNode)) and
            node.parent_port is not None)


# ──────────────────────────────────────────────────────────────────────
# Signal connection helpers for SubGraph lifecycle
# ──────────────────────────────────────────────────────────────────────

def disconnect_safely(signal, slot):
    """Disconnect a Qt signal-slot pair, suppressing RuntimeWarning.

    PySide6 raises RuntimeWarning (not RuntimeError) when disconnecting a
    signal that was never connected.  This wrapper suppresses that warning
    and catches any exceptions, making it safe to call before connecting.

    Args:
        signal: A Qt Signal instance.
        slot: A callable slot.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore", category=RuntimeWarning, message=".*disconnect.*"
        )
        try:
            signal.disconnect(slot)
        except (TypeError, RuntimeError):
            pass


def connect_sub_graph_signals(sub_graph, on_property_changed, on_node_double_clicked):
    """Safely connect signals on a newly created or re-expanded SubGraph.

    Disconnects first to prevent duplicate connections when the SubGraph
    is returned from an existing (already-connected) session.

    Args:
        sub_graph: The SubGraph instance.
        on_property_changed: Slot for sub_graph.property_changed.
        on_node_double_clicked: Slot for sub_graph.node_double_clicked.
    """
    disconnect_safely(sub_graph.property_changed, on_property_changed)
    disconnect_safely(sub_graph.node_double_clicked, on_node_double_clicked)
    sub_graph.property_changed.connect(on_property_changed)
    sub_graph.node_double_clicked.connect(on_node_double_clicked)
