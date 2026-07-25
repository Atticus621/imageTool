"""Node selector dialog — browse registry and configure parameters."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QScrollArea, QWidget, QGridLayout, QGroupBox,
    QMessageBox, QFrame,
)

from core.logger import logger
from core.node_base.registry import node_registry
from ui.widgets.node_param_panel import NodeParamPanel
from ui.theme import BG_SURFACE


class NodeSelectorWindow(QDialog):
    """Dialog for browsing registered node types and editing parameters.

    Three cascading combo boxes (category → subcategory → node) plus
    a NodeParamPanel that renders editable parameter groups.
    """

    node_type_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("节点选择")
        self.setMinimumSize(480, 550)
        self._target_node = None
        self._replace_mode = False
        self._edit_mode = False
        self._current_meta = None
        self.setStyleSheet(f"QDialog {{ background: {BG_SURFACE}; }}")

        # Parameter panel (extracted widget)
        self._param_panel = NodeParamPanel(dialog_parent=self)
        self._init_ui()
        self._populate_category()
        logger.info("NodeSelectorWindow initialized")

    # ── public mode setters ─────────────────────────────────────────────

    def set_target_node(self, node):
        self._target_node = node
        self._param_panel.set_target_node(node)

    def set_replace_mode(self, enabled: bool):
        self._replace_mode = enabled
        self._btn_ok.setText("替换" if enabled else "确定")
        self.setWindowTitle("替换节点" if enabled else "节点选择")

    def set_edit_mode(self, enabled: bool):
        self._edit_mode = enabled
        if enabled:
            self.setWindowTitle("编辑节点")
            self._btn_ok.setText("确定")

    def preselect_node(self, node_id: str, param_values: dict = None):
        meta = node_registry.get_meta(node_id)
        if meta is None:
            return

        self._combo_category.blockSignals(True)
        self._combo_subcategory.blockSignals(True)
        self._combo_node.blockSignals(True)

        # Category
        cat = node_registry.get_category(meta.id)
        idx = self._combo_category.findData(cat)
        if idx >= 0:
            self._combo_category.setCurrentIndex(idx)

        # Subcategory
        tree = node_registry.get_category_tree()
        cat_node = tree.get(cat)
        if cat_node:
            sub = node_registry.get_subcategory(meta.id)
            self._rebuild_subcategory_combo(cat_node, sub)

            # Node items
            sub_key = self._combo_subcategory.currentData()
            items = self._get_items_for_subkey(cat_node, sub_key)
            self._rebuild_node_combo(items)

        idx = self._combo_node.findData(node_id)
        if idx >= 0:
            self._combo_node.setCurrentIndex(idx)

        self._combo_category.blockSignals(False)
        self._combo_subcategory.blockSignals(False)
        self._combo_node.blockSignals(False)

        self._param_panel.show_params(meta)
        if param_values:
            self._param_panel.set_param_values(param_values)
        self._btn_ok.setEnabled(True)
        self._current_meta = meta

    # ── UI construction ─────────────────────────────────────────────────

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Node type browser
        dropdown_group = QGroupBox("节点类型")
        dropdown_layout = QGridLayout(dropdown_group)

        dropdown_layout.addWidget(QLabel("分类:"), 0, 0)
        self._combo_category = QComboBox()
        self._combo_category.currentIndexChanged.connect(self._on_category_changed)
        dropdown_layout.addWidget(self._combo_category, 0, 1)

        dropdown_layout.addWidget(QLabel("子分类:"), 1, 0)
        self._combo_subcategory = QComboBox()
        self._combo_subcategory.currentIndexChanged.connect(self._on_subcategory_changed)
        dropdown_layout.addWidget(self._combo_subcategory, 1, 1)

        dropdown_layout.addWidget(QLabel("节点:"), 2, 0)
        self._combo_node = QComboBox()
        self._combo_node.currentIndexChanged.connect(self._on_node_changed)
        dropdown_layout.addWidget(self._combo_node, 2, 1)

        layout.addWidget(dropdown_group)

        layout.addWidget(_h_separator())

        # Parameter area (scrollable)
        self._param_area = QScrollArea()
        self._param_area.setWidgetResizable(True)
        self._param_area.setWidget(self._param_panel)
        layout.addWidget(self._param_area, 1)

        # Action buttons
        btn_layout = QHBoxLayout()
        self._btn_ok = QPushButton("确定")
        self._btn_cancel = QPushButton("取消")
        self._btn_ok.setEnabled(False)
        self._btn_ok.clicked.connect(self._on_ok)
        self._btn_cancel.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self._btn_ok)
        btn_layout.addWidget(self._btn_cancel)
        layout.addLayout(btn_layout)

    # ── combo-box logic ─────────────────────────────────────────────────

    def _reset_to_safe_state(self):
        """Reset UI to a safe state after an error."""
        self._combo_subcategory.blockSignals(True)
        self._combo_subcategory.clear()
        self._combo_subcategory.blockSignals(False)
        self._combo_node.blockSignals(True)
        self._combo_node.clear()
        self._combo_node.blockSignals(False)
        self._btn_ok.setEnabled(False)
        self._param_panel.show_params(None)

    def _populate_category(self):
        tree = node_registry.get_category_tree()
        self._combo_category.blockSignals(True)
        self._combo_category.clear()
        self._combo_category.addItem("-- 请选择 --", "")
        for cat in sorted(tree.keys()):
            self._combo_category.addItem(cat, cat)
        self._combo_category.blockSignals(False)
        self._combo_subcategory.clear()
        self._combo_node.clear()

    def _on_category_changed(self, index):
        try:
            cat = self._combo_category.currentData()
            self._combo_node.clear()
            self._btn_ok.setEnabled(False)

            if not cat:
                self._combo_subcategory.clear()
                return

            tree = node_registry.get_category_tree()
            cat_node = tree.get(cat)
            if cat_node is None:
                self._combo_subcategory.clear()
                return
            self._rebuild_subcategory_combo(cat_node)
            self._on_subcategory_changed(0)
        except Exception as e:
            logger.error(f"Error in category change: {e}")
            self._reset_to_safe_state()

    def _on_subcategory_changed(self, index):
        try:
            cat = self._combo_category.currentData()
            self._btn_ok.setEnabled(False)
            if not cat:
                return

            tree = node_registry.get_category_tree()
            cat_node = tree.get(cat)
            if cat_node is None:
                return

            sub_key = self._combo_subcategory.currentData()
            items = self._get_items_for_subkey(cat_node, sub_key)
            self._rebuild_node_combo(items)
        except Exception as e:
            logger.error(f"Error in subcategory change: {e}")
            self._reset_to_safe_state()

    def _on_node_changed(self, index):
        try:
            node_id = self._combo_node.currentData()
            if not node_id:
                self._btn_ok.setEnabled(False)
                self._param_panel.show_params(None)
                return

            meta = node_registry.get_meta(node_id)
            if meta:
                self._param_panel.show_params(meta)
                self._btn_ok.setEnabled(True)
                self._current_meta = meta
        except Exception as e:
            logger.error(f"Error in node change: {e}")
            self._reset_to_safe_state()

    # ── shared combo rebuild helpers (eliminates preselect duplication) ─

    @staticmethod
    def _get_items_for_subkey(cat_node, sub_key: str) -> list:
        """Get NodeMeta items for a given subcategory key.

        Args:
            cat_node: CategoryNode from the tree.
            sub_key: Subcategory name, "__direct__" for direct items, or "" for none.

        Returns:
            List of NodeMeta objects.
        """
        from core.node_base.registry import CategoryNode
        if not isinstance(cat_node, CategoryNode):
            return []
        if sub_key == "__direct__":
            return cat_node.items
        elif sub_key:
            sub_node = cat_node.subcategories.get(sub_key)
            return sub_node.items if sub_node else []
        return []

    def _rebuild_subcategory_combo(self, cat_node, preselect: str = None):
        """Rebuild subcategory combo from a CategoryNode.

        Args:
            cat_node: CategoryNode with subcategories and/or items.
            preselect: Optional subcategory name to pre-select.
        """
        self._combo_subcategory.blockSignals(True)
        self._combo_subcategory.clear()

        # No subcategories — show "--" and load direct items
        if not cat_node.has_subcategories():
            self._combo_subcategory.addItem("--", "__direct__")
            self._combo_subcategory.blockSignals(False)
            return

        self._combo_subcategory.addItem("-- 请选择 --", "")
        for sub_name in sorted(cat_node.subcategories.keys()):
            self._combo_subcategory.addItem(sub_name, sub_name)

        self._combo_subcategory.blockSignals(False)

        if preselect:
            idx = self._combo_subcategory.findData(preselect)
            if idx >= 0:
                self._combo_subcategory.setCurrentIndex(idx)

    def _rebuild_node_combo(self, items: list):
        """Rebuild node combo from a list of NodeMeta objects.

        Args:
            items: List of NodeMeta to display.
        """
        self._combo_node.blockSignals(True)
        self._combo_node.clear()

        self._combo_node.addItem("-- 请选择 --", "")
        for item_meta in items:
            self._combo_node.addItem(item_meta.name, item_meta.id)

        self._combo_node.blockSignals(False)

    # ── OK / Replace ────────────────────────────────────────────────────

    def _on_ok(self):
        node_id = self._combo_node.currentData()
        if not node_id:
            return

        self._param_panel.apply_optional_port_changes()

        if self._replace_mode and self._target_node:
            self._do_replace(node_id)
        else:
            self.node_type_selected.emit(node_id)
        self.accept()

    def _do_replace(self, new_node_id: str):
        target = self._target_node
        if target is None:
            return

        old_meta_id = getattr(target, "_node_id", "")
        old_meta = node_registry.get_meta(old_meta_id)
        new_meta = node_registry.get_meta(new_node_id)

        if old_meta is None or new_meta is None:
            return
        if not node_registry.same_category(old_meta_id, new_node_id):
            QMessageBox.warning(self, "替换失败", "只能替换同类型的节点")
            return

        logger.info(f"Replacing node: {old_meta.name} -> {new_meta.name}")
        self.node_type_selected.emit(new_node_id)

    def get_selected_node_id(self) -> str:
        return self._combo_node.currentData() or ""

    def get_param_values(self) -> dict:
        return self._param_panel.get_param_values()


# ── helpers ────────────────────────────────────────────────────────────

def _h_separator() -> QFrame:
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setFrameShadow(QFrame.Shadow.Sunken)
    return sep
