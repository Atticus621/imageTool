"""Context menu builder for the node graph."""


class ContextMenuBuilder:
    """Builds right-click context menus from the NodeRegistry category tree.

    The `create_node` callback is injected so the builder doesn't need
    a reference to the NodeGraphWidget — it just calls the callback with
    (node_id, graph, pos, emit_signal).
    """

    def __init__(self, node_registry, create_node_callback):
        self._registry = node_registry
        self._create_node = create_node_callback

    def build_menu_from_tree(self, parent_menu, tree):
        """Recursively build a menu from the category tree.

        Args:
            parent_menu: NodeGraphQt Menu object.
            tree: CategoryNode or dict[str, CategoryNode] from registry.
        """
        from core.node_base.registry import CategoryNode

        # Case 1: CategoryNode — add its items and recurse into subcategories
        if isinstance(tree, CategoryNode):
            for meta in tree.items:
                parent_menu.add_command(
                    meta.name,
                    self._make_create_node_action(meta.id),
                )
            for sub_name, sub_node in tree.subcategories.items():
                sub_menu = parent_menu.add_menu(sub_name)
                self.build_menu_from_tree(sub_menu, sub_node)

        # Case 2: dict[str, CategoryNode] — top-level categories
        elif isinstance(tree, dict):
            for key, value in tree.items():
                if isinstance(value, CategoryNode):
                    # Has items or subcategories → create a submenu
                    if value.items or value.subcategories:
                        sub_menu = parent_menu.add_menu(key)
                        self.build_menu_from_tree(sub_menu, value)
                elif isinstance(value, dict):
                    # Legacy dict format
                    sub_menu = parent_menu.add_menu(key)
                    self.build_menu_from_tree(sub_menu, value)

    def _make_create_node_action(self, node_id: str):
        """Return a context-menu callback that creates a node at cursor pos."""
        create = self._create_node  # capture locally

        def action(graph):
            pos = graph.cursor_pos()
            create(node_id, graph=graph, pos=pos, emit_signal=True)
        return action
