# -*- coding: utf-8 -*-
"""流水线面板 —— QTreeWidget 实现，原生支持折叠/嵌套/拖拽。"""

from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QTreeWidget, QTreeWidgetItem,
    QMenu, QAbstractItemView, QInputDialog, QPushButton,
)

# 自定义数据角色
ROLE_TYPE = Qt.UserRole       # "step" / "folder" / "original" / "preview"
ROLE_INDEX = Qt.UserRole + 1  # _items 索引


class PipelinePanel(QGroupBox):
    """处理流水线管理面板（QTreeWidget 实现）。"""

    open_image_requested = Signal()
    add_processing_requested = Signal()
    insert_requested = Signal(int)                   # _items 索引 (在步骤后插入)
    add_to_folder_requested = Signal(int)            # folder_idx (在文件夹内添加)
    paste_requested = Signal()
    step_edit_requested = Signal(int)
    toggle_requested = Signal(int)
    toggle_multi_requested = Signal(list)
    remove_requested = Signal(list)
    copy_requested = Signal(list)
    cut_requested = Signal(list)
    clear_requested = Signal()
    order_changed = Signal(list)                     # [src, dst, count]
    create_folder_requested = Signal(str)
    create_subfolder_requested = Signal(int, str)
    rename_folder_requested = Signal(int, str)
    delete_folder_requested = Signal(int)
    export_pipeline_requested = Signal()
    import_pipeline_requested = Signal()

    def __init__(self, parent=None):
        super().__init__("处理流水线", parent)
        self._clipboard = []
        self._preview_item = None

        self.setStyleSheet("""
            QGroupBox { font-family: 'Microsoft YaHei'; font-size: 13px; font-weight: bold;
                        background: #ecf0f1; border: 1px solid #bdc3c7; border-radius: 4px;
                        margin-top: 8px; padding-top: 16px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
        """)

        layout = QVBoxLayout(self)

        # ── 树形列表 ──
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setStyleSheet("font-family: 'Consolas'; font-size: 10px;")
        self._tree.setMinimumHeight(120)

        # 多选
        self._tree.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # 拖拽
        self._tree.setDragDropMode(QAbstractItemView.InternalMove)
        self._tree.setDefaultDropAction(Qt.MoveAction)
        self._tree.setDragDropOverwriteMode(False)
        self._tree.setRootIsDecorated(True)   # 显示文件夹展开/折叠箭头

        # 信号
        self._tree.itemClicked.connect(self._on_click)
        self._tree.itemDoubleClicked.connect(self._on_double_click)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        self._tree.model().rowsMoved.connect(self._on_rows_moved)
        self._tree.installEventFilter(self)

        layout.addWidget(self._tree)

        # ── 导入/导出按钮行 ──
        btn_row = QHBoxLayout()
        btn_style = """
            QPushButton { color: black; padding: 3px 8px; border: none; border-radius: 3px;
                          font-family: 'Microsoft YaHei'; font-size: 10px; }
            QPushButton:hover { opacity: 0.9; }
        """
        btn_export = QPushButton("💾 导出")
        btn_export.setStyleSheet(btn_style + "background: #3498db;")
        btn_export.clicked.connect(self.export_pipeline_requested.emit)
        btn_row.addWidget(btn_export)

        btn_import = QPushButton("📂 导入")
        btn_import.setStyleSheet(btn_style + "background: #9b59b6;")
        btn_import.clicked.connect(self.import_pipeline_requested.emit)
        btn_row.addWidget(btn_import)

        layout.addLayout(btn_row)

    # ═══════════════════════════════════════
    # 拖拽: 禁止拖到原图行
    # ═══════════════════════════════════════
    def eventFilter(self, obj, event):
        if obj is self._tree and event.type() == QEvent.Drop:
            pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
            target = self._tree.itemAt(pos)
            if target and target.data(0, ROLE_TYPE) == "original":
                event.ignore()
                return True
        return super().eventFilter(obj, event)

    def _on_rows_moved(self, _parent, start, end, _dest_parent, dest):
        """拖拽后同步数据。"""
        new_order = self._read_tree_order()
        self.order_changed.emit(new_order)

    def _read_tree_order(self) -> list:
        """读取树的当前顺序，返回 _items 索引列表。"""
        order = []
        root = self._tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            self._collect_order(item, order)
        return order

    def _collect_order(self, item, order):
        idx = item.data(0, ROLE_INDEX)
        item_type = item.data(0, ROLE_TYPE)
        if item_type in ("step", "folder") and idx is not None:
            order.append(idx)
        for i in range(item.childCount()):
            self._collect_order(item.child(i), order)

    # ═══════════════════════════════════════
    # 剪贴板
    # ═══════════════════════════════════════
    def set_clipboard(self, steps_data: list):
        self._clipboard = steps_data

    def has_clipboard(self) -> bool:
        return len(self._clipboard) > 0

    # ═══════════════════════════════════════
    # 单击 / 双击
    # ═══════════════════════════════════════
    def _on_click(self, item, col):
        if item.data(0, ROLE_TYPE) == "folder":
            item.setExpanded(not item.isExpanded())

    def _on_double_click(self, item, col):
        item_type = item.data(0, ROLE_TYPE)
        idx = item.data(0, ROLE_INDEX)
        if item_type == "step" and idx is not None:
            self.step_edit_requested.emit(idx)

    # ═══════════════════════════════════════
    # 选中索引
    # ═══════════════════════════════════════
    def selected_indices(self) -> list:
        indices = []
        for item in self._tree.selectedItems():
            t = item.data(0, ROLE_TYPE)
            idx = item.data(0, ROLE_INDEX)
            if t in ("step", "folder") and idx is not None:
                indices.append(idx)
        return sorted(indices)

    def selected_index(self) -> int:
        indices = self.selected_indices()
        return indices[0] if len(indices) == 1 else -1

    # ═══════════════════════════════════════
    # 右键菜单
    # ═══════════════════════════════════════
    def _show_context_menu(self, pos):
        item = self._tree.itemAt(pos)
        menu = QMenu(self)

        if item is None:
            # ── 空白区域 ──
            menu.addAction("📂 打开图片").triggered.connect(self.open_image_requested.emit)
            menu.addSeparator()
            menu.addAction("➕ 添加流程").triggered.connect(self.add_processing_requested.emit)
            menu.addAction("📁 添加流程文件夹").triggered.connect(self._on_create_folder)
            act_paste = menu.addAction("📋 粘贴")
            act_paste.setEnabled(self.has_clipboard())
            act_paste.triggered.connect(self.paste_requested.emit)
            menu.addSeparator()
            menu.addAction("🧹 清空全部").triggered.connect(self.clear_requested.emit)

        elif item.data(0, ROLE_TYPE) == "folder":
            # ── 文件夹 ──
            idx = item.data(0, ROLE_INDEX)
            menu.addAction("✏️ 重命名").triggered.connect(lambda: self._on_rename_folder(idx))
            menu.addAction("➕ 添加流程").triggered.connect(lambda: self.add_to_folder_requested.emit(idx))
            menu.addAction("📁 添加流程文件夹").triggered.connect(lambda: self._on_create_subfolder(idx))
            menu.addSeparator()
            menu.addAction("🔄 启用/禁用").triggered.connect(lambda: self.toggle_requested.emit(idx))
            menu.addSeparator()
            menu.addAction("🗑️ 删除文件夹").triggered.connect(lambda: self.delete_folder_requested.emit(idx))

        elif item.data(0, ROLE_TYPE) == "step":
            # ── 步骤 ──
            indices = self.selected_indices()
            single = len(indices) == 1

            act_edit = menu.addAction("✏️ 修改")
            act_edit.setEnabled(single)
            if single:
                act_edit.triggered.connect(lambda: self.step_edit_requested.emit(indices[0]))

            if single:
                menu.addAction("➕ 插入").triggered.connect(lambda: self.insert_requested.emit(indices[0]))

            menu.addSeparator()

            if single:
                menu.addAction("🔄 启用/禁用").triggered.connect(lambda: self.toggle_requested.emit(indices[0]))
            else:
                menu.addAction(f"🔄 启用/禁用 ({len(indices)} 项)").triggered.connect(
                    lambda: self.toggle_multi_requested.emit(indices))

            menu.addSeparator()

            if single:
                menu.addAction("📋 复制").triggered.connect(lambda: self.copy_requested.emit(indices))
            else:
                menu.addAction(f"📋 复制 ({len(indices)} 项)").triggered.connect(
                    lambda: self.copy_requested.emit(indices))

            if single:
                menu.addAction("✂️ 剪切").triggered.connect(lambda: self.cut_requested.emit(indices))
            else:
                menu.addAction(f"✂️ 剪切 ({len(indices)} 项)").triggered.connect(
                    lambda: self.cut_requested.emit(indices))

            act_paste = menu.addAction("📋 粘贴")
            act_paste.setEnabled(self.has_clipboard())
            act_paste.triggered.connect(self.paste_requested.emit)

            menu.addSeparator()

            if single:
                menu.addAction("🗑️ 删除").triggered.connect(lambda: self.remove_requested.emit(indices))
            else:
                menu.addAction(f"🗑️ 删除 ({len(indices)} 项)").triggered.connect(
                    lambda: self.remove_requested.emit(indices))

            menu.addAction("🧹 清空全部").triggered.connect(self.clear_requested.emit)

        menu.exec_(self._tree.viewport().mapToGlobal(pos))

    def _on_create_folder(self):
        name, ok = QInputDialog.getText(self, "添加流程文件夹", "文件夹名称:")
        if ok:
            self.create_folder_requested.emit(name.strip())

    def _on_create_subfolder(self, parent_idx: int):
        name, ok = QInputDialog.getText(self, "添加流程文件夹", "文件夹名称:")
        if ok:
            self.create_subfolder_requested.emit(parent_idx, name.strip())

    def _on_rename_folder(self, idx: int):
        name, ok = QInputDialog.getText(self, "重命名文件夹", "新名称:")
        if ok and name.strip():
            self.rename_folder_requested.emit(idx, name.strip())

    # ═══════════════════════════════════════
    # 刷新显示
    # ═══════════════════════════════════════
    def update_display(self, display_list: list, items=None):
        """用 pipeline 数据重建树。display_list 提供编号文本，items 提供结构。"""
        saved_expanded = self._save_expanded_state()

        self._tree.blockSignals(True)
        self._tree.clear()
        self._preview_item = None

        # 原图
        root_item = QTreeWidgetItem([display_list[0] if display_list else "0: 原图"])
        root_item.setData(0, ROLE_TYPE, "original")
        root_item.setFlags(root_item.flags() & ~Qt.ItemIsDragEnabled)
        self._tree.addTopLevelItem(root_item)

        if items is None or not items:
            self._tree.blockSignals(False)
            return

        # display_list[1:] 对应 items[0:]
        stack = []  # (depth, QTreeWidgetItem)

        for idx, item in enumerate(items):
            # 从 display_list 获取带编号的文本
            dl_idx = idx + 1  # display_list 跳过 "0: 原图"
            if dl_idx < len(display_list):
                # 去掉缩进前缀（QTreeWidget 自动处理）
                text = display_list[dl_idx].lstrip()
            else:
                text = item.folder_name if item.type == "folder" else "?"

            tree_item = QTreeWidgetItem([text])

            if item.type == "folder":
                tree_item.setData(0, ROLE_TYPE, "folder")
                tree_item.setData(0, ROLE_INDEX, idx)
                font = tree_item.font(0)
                font.setBold(True)
                tree_item.setFont(0, font)
                if not item.enabled:
                    tree_item.setForeground(0, QColor("#95a5a6"))  # 禁用文件夹 → 灰色
                else:
                    tree_item.setForeground(0, Qt.black)           # 启用文件夹 → 黑色
                self._insert_tree_item(tree_item, item.folder_depth, stack)
                tree_item.setExpanded(saved_expanded.get(idx, True))

            elif item.type == "step" and item.step:
                tree_item.setData(0, ROLE_TYPE, "step")
                tree_item.setData(0, ROLE_INDEX, idx)
                if not item.step.enabled:
                    tree_item.setForeground(0, QColor("#95a5a6"))  # 禁用步骤 → 灰色
                else:
                    tree_item.setForeground(0, Qt.black)           # 启用步骤 → 黑色
                self._insert_tree_item(tree_item, item.folder_depth, stack)

        self._tree.blockSignals(False)

    def _save_expanded_state(self) -> dict:
        """保存当前所有文件夹的折叠状态。{items_idx: expanded}"""
        state = {}
        def walk(item):
            if item.data(0, ROLE_TYPE) == "folder":
                idx = item.data(0, ROLE_INDEX)
                if idx is not None:
                    state[idx] = item.isExpanded()
            for i in range(item.childCount()):
                walk(item.child(i))
        root = self._tree.invisibleRootItem()
        for i in range(root.childCount()):
            walk(root.child(i))
        return state

    def _insert_tree_item(self, tree_item, depth, stack):
        """根据深度将树节点插入到正确的位置。"""
        # 弹出栈中深度 >= 当前深度的项
        while stack and stack[-1][0] >= depth:
            stack.pop()

        if stack:
            parent = stack[-1][1]
            parent.addChild(tree_item)
        else:
            self._tree.addTopLevelItem(tree_item)

        stack.append((depth, tree_item))

    # ═══════════════════════════════════════
    # 预览虚文字
    # ═══════════════════════════════════════
    def show_preview(self, display_text: str, after_index: int = -1):
        """显示预览项。

        Args:
            after_index: _items 索引，预览显示在该项之后。-1 表示末尾。
        """
        self.remove_preview()
        self._tree.blockSignals(True)

        preview = QTreeWidgetItem([f"$ {display_text}"])
        preview.setData(0, ROLE_TYPE, "preview")
        preview.setForeground(0, Qt.gray)
        preview.setFlags(preview.flags() & ~(Qt.ItemIsSelectable | Qt.ItemIsDragEnabled))

        if after_index >= 0:
            target = self._find_tree_item_by_index(after_index)
            if target:
                # 如果目标不可见（在折叠文件夹内），向上找可见的父级
                visible_target = target
                while not visible_target.isHidden():
                    parent = visible_target.parent()
                    if parent is None:
                        break
                    if not parent.isExpanded():
                        visible_target = parent
                    else:
                        break

                # 检查目标是否真的不可见
                if target.isHidden():
                    # 插入到可见父级之后
                    parent = visible_target.parent()
                    if parent:
                        idx = parent.indexOfChild(visible_target)
                        parent.insertChild(idx + 1, preview)
                    else:
                        idx = self._tree.indexOfTopLevelItem(visible_target)
                        self._tree.insertTopLevelItem(idx + 1, preview)
                elif target.data(0, ROLE_TYPE) == "folder" and target.isExpanded():
                    target.addChild(preview)
                else:
                    parent = target.parent()
                    if parent:
                        idx = parent.indexOfChild(target)
                        parent.insertChild(idx + 1, preview)
                    else:
                        idx = self._tree.indexOfTopLevelItem(target)
                        self._tree.insertTopLevelItem(idx + 1, preview)
            else:
                self._tree.addTopLevelItem(preview)
        else:
            self._tree.addTopLevelItem(preview)

        self._preview_item = preview
        self._tree.blockSignals(False)

    def update_preview_text(self, display_text: str):
        if self._preview_item:
            self._preview_item.setText(0, f"$ {display_text}")

    def remove_preview(self):
        if self._preview_item is not None:
            parent = self._preview_item.parent()
            if parent:
                parent.removeChild(self._preview_item)
            else:
                idx = self._tree.indexOfTopLevelItem(self._preview_item)
                if idx >= 0:
                    self._tree.takeTopLevelItem(idx)
            self._preview_item = None

    def _find_tree_item_by_index(self, items_idx: int):
        """根据 _items 索引查找树节点。"""
        for item in self._tree.selectedItems():
            if item.data(0, ROLE_INDEX) == items_idx:
                return item
        # 遍历所有
        def search(parent):
            for i in range(parent.childCount()):
                child = parent.child(i)
                if child.data(0, ROLE_INDEX) == items_idx:
                    return child
                result = search(child)
                if result:
                    return result
            return None

        root = self._tree.invisibleRootItem()
        for i in range(root.childCount()):
            top = root.child(i)
            if top.data(0, ROLE_INDEX) == items_idx:
                return top
            result = search(top)
            if result:
                return result
        return None
