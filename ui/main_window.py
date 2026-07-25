import os

os.environ["QT_API"] = "pyside6"

from pathlib import Path

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QMenuBar, QStatusBar, QMenu, QMessageBox, QFileDialog, QDialog,
)

from core.logger import logger
from core.config import config
from core.node_base.registry import node_registry
from core.system.auto_register import get_all_registrations, get_sorted_by_dependencies
from ui.qt_engine import QtExecutionEngine as ExecutionEngine
from systems.execution.result import ExecutionResult, ImageSetEntry
from systems.display_manager import DisplayWindowManager
from ui.node_graph.widget import NodeGraphWidget
from ui.node_graph.graph_node import GraphNode
from ui.node_selector import NodeSelectorWindow
from ui.project_file_controller import ProjectFileController
from ui.widgets.info_panel import InfoPanelWidget
from ui.widgets.node_property_panel import NodePropertyPanel
from ui.execution_controller import ExecutionController


class MainWindow(QMainWindow):
    """Main application window — thin orchestrator.

    Systems must be provided via a SystemRegistry.  Use
    ``MainWindow.from_registry(registry)`` to create.
    """

    @classmethod
    def from_registry(cls, registry) -> "MainWindow":
        window = cls(registry=registry)
        return window

    def __init__(self, registry=None):
        super().__init__()
        self._systems = {}
        self._system_registrations = get_all_registrations()

        self.setWindowTitle(config.get("ui.window_title", "ImageTools"))
        self.resize(
            config.get("ui.window_width", 1600),
            config.get("ui.window_height", 900),
        )

        # Load systems from registry
        for name in get_sorted_by_dependencies():
            try:
                self._systems[name] = registry.get(name)
            except KeyError:
                logger.warning(f"[MainWindow] System not found in registry: {name}")

        self._image_display = self._systems.get("ImageDisplay")
        self._blueprint = self._systems.get("Blueprint")
        self._project = self._systems.get("Project")

        self._init()

    def _init(self):
        """Single unified initialization."""
        self._node_graph_widget = None
        self._node_selector = None
        self._engine = ExecutionEngine(self)
        self._display_manager = DisplayWindowManager()

        self._exec_ctrl = ExecutionController(
            engine=self._engine,
            graph_getter=lambda: self._node_graph_widget.graph,
            on_before_execute=self._reset_all_node_states,
            parent=self,
        )
        self._exec_ctrl.state_changed.connect(self._sync_execution_ui)

        # Project file controller — owns all project I/O + save prompts
        self._project_ctrl = ProjectFileController(self._project, self)

        self._init_ui()
        self._build_menu()
        self._build_toolbar()
        self._init_statusbar()

        self._project_ctrl.status_message.connect(self._statusbar.showMessage)
        self._project_ctrl.title_changed.connect(self.setWindowTitle)
        self._wire_systems()
        self._connect_signals()

        self._project_ctrl.update_window_title()
        logger.info("MainWindow initialized")

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side: blueprint canvas + property panel (vertical split)
        self._left_splitter = QSplitter(Qt.Orientation.Vertical)
        self._node_graph_widget = NodeGraphWidget()
        self._node_property_panel = NodePropertyPanel()

        self._left_splitter.addWidget(self._node_graph_widget)
        self._left_splitter.addWidget(self._node_property_panel)
        self._left_splitter.setSizes([600, 200])
        self._left_splitter.setStretchFactor(0, 3)
        self._left_splitter.setStretchFactor(1, 1)

        self._right_panel = self._create_right_panel()

        self._splitter.addWidget(self._left_splitter)
        self._splitter.addWidget(self._right_panel)

        left_ratio = config.get("ui.left_panel_ratio", 0.55)
        right_ratio = config.get("ui.right_panel_ratio", 0.45)
        total = config.get("ui.window_width", 1600)
        self._splitter.setSizes([int(total * left_ratio), int(total * right_ratio)])

        layout.addWidget(self._splitter)

    def _create_right_panel(self) -> QWidget:
        from ui.image_viewer import ImageViewerWidget

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._image_viewer = ImageViewerWidget(self._image_display)
        self._info_panel = InfoPanelWidget()

        # Register for remote simulation
        from core.network.api.v1.simulation import register_widget
        register_widget("image_viewer", self._image_viewer)

        layout.addWidget(self._image_viewer, 1)
        layout.addWidget(self._info_panel, 0)

        return container

    def _init_statusbar(self):
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._statusbar.showMessage("就绪")

    def _connect_signals(self):
        graph = self._node_graph_widget.graph
        graph.node_created.connect(self._on_node_created)
        graph.node_double_clicked.connect(self._on_node_double_clicked)
        graph.node_selection_changed.connect(self._on_node_selection_changed)
        self._node_graph_widget.node_replace_requested.connect(self._on_replace_requested)
        self._node_graph_widget.node_delete_requested.connect(self._on_delete_requested)
        self._node_graph_widget.node_created_with_meta.connect(self._on_node_created_with_meta)
        self._node_graph_widget.add_to_display_requested.connect(self._on_add_to_display)

        self._engine.execution_started.connect(self._on_engine_started)
        self._engine.execution_finished.connect(self._on_engine_finished)
        self._engine.node_state_changed.connect(self._on_node_state_changed)
        self._engine.progress_updated.connect(self._on_progress_updated)
        self._engine.image_output.connect(self._on_image_output)
        self._image_viewer.ruler_measurement.connect(self._on_ruler_measurement)
        self._image_viewer.pixel_hovered.connect(self._info_panel.update_info)

        # Property panel param changes → sync to GraphNode
        self._node_property_panel.param_changed.connect(self._on_property_param_changed)

        # Project system signals
        self._project.on_project_modified.connect(self._on_project_modified)
        self._project.on_project_loaded.connect(self._on_project_loaded)

    # ------------------------------------------------------------------
    # System wiring
    # ------------------------------------------------------------------

    def _wire_systems(self):
        """Wire all systems to the graph and execution callbacks."""
        graph_getter = lambda: self._node_graph_widget.graph

        # BlueprintSystem needs extra execution callbacks
        if "Blueprint" in self._systems:
            try:
                self._systems["Blueprint"].wire(
                    graph_getter=graph_getter,
                    on_execute=self._exec_ctrl.execute,
                    on_stop=self._exec_ctrl.stop,
                    on_clear=self._on_new_project,
                    on_loop_on=self._exec_ctrl.enable_loop,
                    on_loop_off=self._exec_ctrl.disable_loop,
                )
                logger.info("[MainWindow] Wired system: Blueprint")
            except Exception as e:
                logger.error(f"[MainWindow] Failed to wire Blueprint: {e}")

        # Other systems use generic wire
        for name, system in self._systems.items():
            if name == "Blueprint":
                continue
            reg = self._system_registrations.get(name)
            if reg and reg.auto_wire and hasattr(system, 'wire'):
                try:
                    system.wire(graph_getter=graph_getter)
                    logger.info(f"[MainWindow] Wired system: {name}")
                except Exception as e:
                    logger.error(f"[MainWindow] Failed to wire {name}: {e}")

        # Wire DisplayManager to ProjectSystem for persistence
        if "Project" in self._systems:
            project_system = self._systems["Project"]
            project_system.set_display_manager(self._display_manager)

    def _build_menu(self):
        """从系统注册自动构建菜单"""
        menu_bar = self.menuBar()

        # 文件菜单
        file_menu = menu_bar.addMenu("文件(&F)")

        # 收集所有系统的菜单项
        for name in get_sorted_by_dependencies():
            reg = self._system_registrations.get(name)
            if not reg:
                continue

            for item in reg.menu_items:
                if item.separator_before:
                    file_menu.addSeparator()

                # 跳过没有方法的分隔符项
                if not item.method:
                    if item.separator_after:
                        file_menu.addSeparator()
                    continue

                action = QAction(item.text, self)
                if item.shortcut:
                    action.setShortcut(QKeySequence(item.shortcut))

                # 优先查找 MainWindow 的方法，然后查找系统的方法
                if hasattr(self, item.method):
                    method = getattr(self, item.method)
                    action.triggered.connect(method)
                else:
                    system = self._systems.get(name)
                    if system and hasattr(system, item.method):
                        method = getattr(system, item.method)
                        action.triggered.connect(method)
                    else:
                        logger.warning(f"[MainWindow] Method not found: {name}.{item.method}")

                file_menu.addAction(action)

                if item.separator_after:
                    file_menu.addSeparator()

        # 添加退出菜单项
        file_menu.addSeparator()
        file_menu.addAction("退出", self.close)

        # 运行菜单
        run_menu = menu_bar.addMenu("运行(&R)")
        run_menu.addAction("单次执行", self._exec_ctrl.execute_once)
        run_menu.addAction("停止执行", self._exec_ctrl.stop)
        run_menu.addSeparator()
        self._action_loop = QAction("循环运行", self)
        self._action_loop.setCheckable(True)
        self._action_loop.triggered.connect(self._exec_ctrl.toggle_loop)
        run_menu.addAction(self._action_loop)

        # 视图菜单
        view_menu = menu_bar.addMenu("视图(&V)")
        view_menu.addAction("重置缩放", self._on_reset_zoom)
        view_menu.addAction("适应选中", self._on_fit_selection)
        view_menu.addSeparator()
        self._action_ruler = QAction("尺子工具", self)
        self._action_ruler.setCheckable(True)
        self._action_ruler.triggered.connect(self._on_toggle_ruler)
        view_menu.addAction(self._action_ruler)

        # 帮助菜单
        help_menu = menu_bar.addMenu("帮助(&H)")
        help_menu.addAction("关于", self._on_about)

    def _build_toolbar(self):
        """从系统注册自动构建工具栏"""
        toolbar = self.addToolBar("执行")
        toolbar.setMovable(False)

        # 执行按钮
        self._btn_single = QAction("▶ 单次", self)
        self._btn_single.triggered.connect(self._exec_ctrl.execute_once)
        toolbar.addAction(self._btn_single)

        self._btn_loop = QAction("🔁 循环", self)
        self._btn_loop.triggered.connect(self._exec_ctrl.toggle_loop)
        toolbar.addAction(self._btn_loop)

        toolbar.addSeparator()

        # 收集所有系统的工具栏项
        for name in get_sorted_by_dependencies():
            reg = self._system_registrations.get(name)
            if not reg:
                continue

            for item in reg.toolbar_items:
                if item.separator_before:
                    toolbar.addSeparator()

                action = QAction(item.text, self)

                # 优先查找 MainWindow 的方法，然后查找系统的方法
                if hasattr(self, item.method):
                    method = getattr(self, item.method)
                    action.triggered.connect(method)
                else:
                    system = self._systems.get(name)
                    if system and hasattr(system, item.method):
                        method = getattr(system, item.method)
                        action.triggered.connect(method)

                toolbar.addAction(action)

                if item.separator_after:
                    toolbar.addSeparator()

        toolbar.addSeparator()

        # 其他工具栏按钮
        self._btn_clear = QAction("✕ 清空", self)
        self._btn_clear.triggered.connect(self._on_new_project)
        toolbar.addAction(self._btn_clear)

        toolbar.addSeparator()

        self._btn_ruler = QAction("📏 尺子", self)
        self._btn_ruler.setCheckable(True)
        self._btn_ruler.triggered.connect(self._on_toggle_ruler)
        toolbar.addAction(self._btn_ruler)

    # ------------------------------------------------------------------
    # Node / graph event handlers
    # ------------------------------------------------------------------

    @Slot(object)
    def _on_node_created(self, node):
        logger.info(f"Node created in graph: {node.name()}")

    @Slot(object, str)
    def _on_node_created_with_meta(self, node, node_id: str):
        # Widget is now created automatically by set_node_meta()
        logger.info(f"Node created with meta: {node.name()} ({node_id}), opening editor")
        self._open_node_editor(node, node_id)

    @Slot(list)
    def _on_node_selection_changed(self, selected_nodes):
        # Query actual selection — signal only emits *newly* selected nodes,
        # which is empty when dragging an already-selected node.
        actual = self._node_graph_widget.graph.selected_nodes()
        if not actual:
            self._node_property_panel.set_node(None)
            self._statusbar.showMessage("就绪")
            return

        node = actual[-1]
        self._node_property_panel.set_node(node)
        name = node.name()
        node_id = getattr(node, "_node_id", "")
        unconnected_in = sum(1 for p in node.input_ports() if not p.connected_ports())
        unconnected_out = sum(1 for p in node.output_ports() if not p.connected_ports())
        total_in = len(node.input_ports())
        total_out = len(node.output_ports())

        info = f"节点: {name}"
        if node_id:
            info += f" ({node_id})"
        info += f"  |  输入端口: {total_in} (未连: {unconnected_in})"
        info += f"  |  输出端口: {total_out} (未连: {unconnected_out})"

        state = getattr(node, "_state", "idle")
        state_map = {"idle": "待执行", "running": "执行中", "success": "成功", "error": "失败"}
        info += f"  |  状态: {state_map.get(state, state)}"

        self._statusbar.showMessage(info)

    @Slot(object)
    def _on_node_double_clicked(self, node):
        from NodeGraphQt import GroupNode
        from NodeGraphQt.nodes.port_node import PortInputNode, PortOutputNode
        from ui.adapters.node_graph_workarounds import (
            rebuild_group_node_ports,
            expand_group_node_with_retry,
            connect_sub_graph_signals,
        )

        # Port nodes: double-click to rename the port node
        if isinstance(node, (PortInputNode, PortOutputNode)):
            self._node_graph_widget.rename_node_inline(node)
            return

        if isinstance(node, GroupNode):
            logger.info(f"Expand group node: {node.name()}")
            # Workaround 2: library deserialization doesn't recreate Port objects
            rebuild_group_node_ports(node)

            parent_graph = node.graph
            if parent_graph:
                # Workaround 3: stale session causes KeyError on expand
                sub_graph = expand_group_node_with_retry(parent_graph, node)
                if sub_graph:
                    connect_sub_graph_signals(
                        sub_graph,
                        self._on_sub_graph_property_changed,
                        self._on_node_double_clicked,
                    )
                    # Add SubGraph-only context menu items (add input/output port)
                    self._node_graph_widget.setup_sub_graph_menu(sub_graph)
            return

        node_id = getattr(node, "_node_id", "")
        if node_id:
            logger.info(f"Edit node: {node.name()} ({node_id})")
            self._open_node_editor(node, node_id)
        else:
            logger.info(f"Select type for node: {node.name()}")
            self._open_node_selector(node)

    def _on_sub_graph_property_changed(self, node, prop_name, value):
        """Sync port name when PortInputNode/PortOutputNode is renamed in SubGraph."""
        from ui.adapters.node_graph_workarounds import (
            is_port_rename_event,
            sync_port_name_to_group,
        )
        if is_port_rename_event(node, prop_name):
            sync_port_name_to_group(node.parent_port, value)

    @Slot(object)
    def _on_replace_requested(self, node):
        logger.info(f"Replace requested for: {node.name()}")
        self._pending_replace_node = node
        self._open_node_selector(node, replace_mode=True)

    def _on_delete_requested(self, node):
        logger.info(f"Deleting node: {node.name()}")
        self._node_graph_widget.graph.remove_node(node)

    def _on_add_to_display(self, node):
        """Handle 'add to display' request from node context menu."""
        from ui.dialogs.new_display_dialog import NewDisplayDialog

        existing = self._display_manager.get_displays()
        dialog = NewDisplayDialog(existing, parent=self)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        if dialog.is_create_mode:
            # Create new display
            name = dialog.new_display_name
            display_id = self._display_manager.create_display(name)
            self._display_manager.add_node_to_display(node.name(), display_id)
            self._image_viewer.add_custom_display(display_id, name)
            self._project.mark_modified()
        else:
            # Add to existing display
            display_id = dialog.selected_display_id
            self._display_manager.add_node_to_display(node.name(), display_id)
            self._project.mark_modified()

        logger.info(f"Node '{node.name()}' added to display")

    @Slot(str)
    def _on_node_type_selected(self, node_id: str):
        if hasattr(self, '_pending_replace_node') and self._pending_replace_node:
            self._node_graph_widget.replace_node(self._pending_replace_node, node_id)
            self._pending_replace_node = None
        elif self._node_selector and self._node_selector._edit_mode:
            target = self._node_selector._target_node
            if target:
                param_values = self._node_selector.get_param_values()
                target._param_values.update(param_values)
                target.sync_port_visibility()
                logger.info(f"Updated node params: {target.name()} -> {param_values}")
                # Refresh inline property panel to stay in sync
                self._node_property_panel.set_node(target)
        else:
            self._node_graph_widget.create_node_by_id(node_id)

    def _open_node_editor(self, node, node_id: str):
        if self._node_selector is None:
            self._node_selector = NodeSelectorWindow(self)
            self._node_selector.node_type_selected.connect(self._on_node_type_selected)

        self._node_selector.set_target_node(node)
        self._node_selector.set_edit_mode(True)
        self._node_selector.preselect_node(
            node_id,
            param_values=node._param_values if hasattr(node, '_param_values') else None,
        )
        self._node_selector.show()
        self._node_selector.raise_()
        self._node_selector.activateWindow()

    def _open_node_selector(self, node=None, replace_mode=False):
        if self._node_selector is None:
            self._node_selector = NodeSelectorWindow(self)
            self._node_selector.node_type_selected.connect(self._on_node_type_selected)
        self._node_selector.set_target_node(node)
        self._node_selector.set_replace_mode(replace_mode)
        self._node_selector.show()
        self._node_selector.raise_()
        self._node_selector.activateWindow()

    # ------------------------------------------------------------------
    # Project event handlers
    # ------------------------------------------------------------------

    def _on_project_modified(self):
        """Handle project modification."""
        title = self.windowTitle()
        if not title.endswith("*"):
            self.setWindowTitle(f"{title}*")

    def _on_project_loaded(self, project):
        """Handle project loaded — sync custom displays to viewer."""
        self._image_viewer.sync_custom_displays(self._display_manager.get_displays())

    # ------------------------------------------------------------------
    # Execution control
    # ------------------------------------------------------------------

    def _on_new_project(self):
        self._project_ctrl.new_project()

    def _sync_execution_ui(self):
        """Single sync point for toolbar/menu — called on every state change."""
        ctrl = self._exec_ctrl
        self._btn_loop.setText("■ 停止" if ctrl.loop_mode else "🔁 循环")
        self._action_loop.setChecked(ctrl.loop_mode)
        self._btn_single.setEnabled(not ctrl.is_running)

    def _on_engine_started(self):
        self._statusbar.showMessage("正在执行...")
        logger.info("Engine started")

    @Slot(str, object)
    def _on_property_param_changed(self, param_name: str, value):
        """Property panel param changed — already written to GraphNode by panel."""
        logger.debug(f"Property panel param changed: {param_name} = {value}")

    # ------------------------------------------------------------------
    # Embedded widget support — override in subclasses for node-specific updates
    # ------------------------------------------------------------------

    def _update_embedded_widgets(self):
        """Update embedded widgets on graph nodes.

        Override this method in subclasses to handle node-specific
        embedded widget updates. Default implementation handles histogram nodes.
        """
        try:
            from nodes.processing.statistics.histogram.node import HistogramNode
        except ImportError:
            return

        graph = self._node_graph_widget.graph
        for gn in graph.all_nodes():
            if not isinstance(gn, GraphNode):
                continue
            node_id = getattr(gn, "_node_id", "")
            if node_id != "processing/statistics/histogram":
                continue
            widget = gn.get_embedded_widget()
            if widget is None:
                continue
            pending = HistogramNode.pop_pending_data(gn.name())
            if pending is not None:
                widget.set_hist_data(*pending)
                logger.info(f"[MainWindow] Updated embedded histogram for {gn.name()}")

    @Slot(object)
    def _on_engine_finished(self, result: ExecutionResult):
        # Collect custom display data
        custom_sets = self._collect_custom_sets(result)
        result.custom_sets = custom_sets

        # Sync custom displays in viewer
        self._image_viewer.sync_custom_displays(self._display_manager.get_displays())

        self._image_viewer.set_execution_results(result)
        self._update_embedded_widgets()

        if self._exec_ctrl.loop_mode:
            self._statusbar.showMessage(f"循环执行中... (上次: {'成功' if result.success else '失败'})")
        else:
            if result.success:
                self._statusbar.showMessage("执行完成 - 成功")
            else:
                self._statusbar.showMessage("执行完成 - 有节点失败")
            logger.info(f"Engine finished: success={result.success}")

    def _on_node_state_changed(self, name: str, state: str):
        graph = self._node_graph_widget.graph
        for node in graph.all_nodes():
            if node.name() == name and isinstance(node, GraphNode):
                node.update_state_color(state)
                break

    def _on_property_param_changed(self, param_name: str, value):
        """Inline property panel param changed — already synced to GraphNode by the panel."""
        pass  # NodePropertyPanel handles the write-back directly

    def _on_progress_updated(self, current: int, total: int):
        self._statusbar.showMessage(f"执行中... {current}/{total}")

    def _on_image_output(self, entries):
        from systems.execution.result import ExecutionResult
        result = ExecutionResult(success=True, output_sets=entries)
        self._image_viewer.set_execution_results(result)

    def _reset_all_node_states(self):
        graph = self._node_graph_widget.graph
        for node in graph.all_nodes():
            if isinstance(node, GraphNode):
                node.update_state_color("idle")

    def _collect_custom_sets(self, result: ExecutionResult) -> list[ImageSetEntry]:
        """Collect image entries for custom displays from execution result."""
        # Group all available sets by node name prefix
        all_sets = {}
        for entry in result.output_sets + result.input_sets:
            # Entry name format: "node_name:port_name"
            node_name = entry.name.split(":")[0] if ":" in entry.name else entry.name
            if node_name not in all_sets:
                all_sets[node_name] = []
            all_sets[node_name].append(entry)

        # Build custom sets from display associations
        display_images: dict[str, list] = {}  # display_id -> list of images
        for node_name, display_id in self._display_manager._node_displays.items():
            if display_id not in display_images:
                display_images[display_id] = []
            # Find matching entries
            for entry_name, entries in all_sets.items():
                if entry_name == node_name or node_name in entry_name:
                    for entry in entries:
                        display_images[display_id].extend(entry.images)

        # Convert to ImageSetEntry list
        custom_sets = []
        for display_id, images in display_images.items():
            if images:
                name = self._display_manager.get_display_name(display_id) or display_id
                custom_sets.append(ImageSetEntry(name=name, images=images))
                # Also update viewer's custom display data
                self._image_viewer.set_custom_display_data(
                    display_id,
                    [ImageSetEntry(name=name, images=images)],
                )

        return custom_sets

    # ------------------------------------------------------------------
    # View / toolbar actions
    # ------------------------------------------------------------------

    def _on_reset_zoom(self):
        self._node_graph_widget.graph.reset_zoom()
        self._image_viewer.reset_zoom()

    def _on_fit_selection(self):
        self._node_graph_widget.graph.fit_to_selection()

    def _on_toggle_ruler(self):
        enabled = self._image_viewer.toggle_ruler()
        self._btn_ruler.setChecked(enabled)
        self._action_ruler.setChecked(enabled)
        if enabled:
            self._statusbar.showMessage("尺子工具已启用 - 在图像上拖拽画线进行测量")
            logger.info("Ruler tool enabled")
        else:
            self._statusbar.showMessage("尺子工具已关闭")
            logger.info("Ruler tool disabled")

    def _on_ruler_measurement(self, result):
        self._statusbar.showMessage(f"测量结果: {result.pixel_distance:.1f} 像素")

    def _on_about(self):
        app_name = config.get("app.name", "ImageTools")
        app_version = config.get("app.version", "0.1.0")
        window_title = config.get("ui.window_title", "图像处理蓝图工具")
        QMessageBox.about(
            self,
            f"关于 {app_name}",
            f"{app_name} {app_version}\n\n{window_title}",
        )

    # ------------------------------------------------------------------
    # Project operations
    # ------------------------------------------------------------------

    def _on_open_project(self):
        self._project_ctrl.open_project()

    def _on_save_project(self) -> bool:
        return self._project_ctrl.save_project()

    def _on_save_project_as(self) -> bool:
        return self._project_ctrl.save_project_as()

    def _on_save_as_template(self):
        self._project_ctrl.save_as_template()

    def _update_window_title(self):
        self._project_ctrl.update_window_title()

    def closeEvent(self, event):
        self._project_ctrl.handle_close(event)


# ------------------------------------------------------------------
# Embedded widget factories — registered via decorator.
# Defined at module level so the decorators run at import time.
# ------------------------------------------------------------------

from ui.embedded_widget_registry import EmbeddedWidgetRegistry


@EmbeddedWidgetRegistry.register("processing/statistics/histogram")
def _create_histogram_embedded(node):
    from ui.widgets.node_histogram_widget import NodeHistogramWidget
    widget = EmbeddedWidgetRegistry.create_widget(node, NodeHistogramWidget)
    node.add_embedded_widget(widget)


@EmbeddedWidgetRegistry.register("processing/color/color_convert")
def _create_color_conversion_embedded(node):
    from ui.widgets.color_conversion_widget import ColorConversionWidget
    widget = EmbeddedWidgetRegistry.create_widget(node, ColorConversionWidget)
    node.add_embedded_widget(widget)
    # Connect widget signal to update node param
    widget.colorSpaceChanged.connect(
        lambda value, n=node: _on_color_space_changed(n, value))
    # Initialize widget with current param value
    current_value = node._param_values.get("target_type", "bgr")
    widget.set_value(current_value)


def _on_color_space_changed(node, value: str):
    """Update node's target_type parameter when widget changes."""
    node._param_values["target_type"] = value
