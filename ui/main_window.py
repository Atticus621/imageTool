import os

os.environ["QT_API"] = "pyside6"

from pathlib import Path

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QMenuBar, QStatusBar, QMenu, QMessageBox, QFileDialog,
)

from core.logger import logger
from core.config import config
from core.node_base.registry import node_registry
from core.system.auto_register import get_all_registrations, get_sorted_by_dependencies
from ui.qt_engine import QtExecutionEngine as ExecutionEngine
from systems.execution.result import ExecutionResult
from core.interfaces import IImageDisplayProvider, INodeGraphProvider
from ui.node_graph_widget import NodeGraphWidget, GraphNode
from ui.node_selector import NodeSelectorWindow
from ui.widgets.info_panel import InfoPanelWidget
from ui.execution_controller import ExecutionController


class MainWindow(QMainWindow):
    """主窗口 - 支持自动注册和手动注入两种方式"""

    @classmethod
    def from_registry(cls, registry) -> "MainWindow":
        """从注册表创建 MainWindow（自动模式）

        Args:
            registry: SystemRegistry 实例

        Returns:
            MainWindow 实例
        """
        # 使用 __init__ 并传递 registry
        window = cls(registry=registry)
        return window

    def __init__(
        self,
        image_display: IImageDisplayProvider | None = None,
        blueprint: INodeGraphProvider | None = None,
        project=None,
        registry=None,
    ):
        super().__init__()
        self._systems = {}
        self._system_registrations = get_all_registrations()

        self.setWindowTitle(config.get("ui.window_title", "ImageTools"))
        self.resize(
            config.get("ui.window_width", 1600),
            config.get("ui.window_height", 900),
        )

        # 如果提供了 registry，使用自动模式
        if registry is not None:
            # 从注册表获取所有系统
            for name in get_sorted_by_dependencies():
                try:
                    self._systems[name] = registry.get(name)
                except KeyError:
                    logger.warning(f"[MainWindow] System not found in registry: {name}")

            # 设置快捷访问属性
            self._image_display = self._systems.get("ImageDisplay")
            self._blueprint = self._systems.get("Blueprint")
            self._project = self._systems.get("Project")

            # 初始化 UI（自动模式）
            self._init_from_registry()
        else:
            # 手动注入模式（向后兼容）
            if image_display is None:
                from systems.image_display.system import ImageDisplaySystem
                self._image_display = ImageDisplaySystem()
            else:
                self._image_display = image_display

            if blueprint is None:
                from systems.blueprint.system import BlueprintSystem
                self._blueprint = BlueprintSystem()
            else:
                self._blueprint = blueprint

            if project is None:
                from pathlib import Path
                from systems.project.system import ProjectSystem
                root_dir = Path(__file__).parent.parent
                self._project = ProjectSystem(root_dir)
            else:
                self._project = project

            # 注册到 systems 字典
            self._systems["ImageDisplay"] = self._image_display
            self._systems["Blueprint"] = self._blueprint
            self._systems["Project"] = self._project

            # 初始化 UI（标准模式）
            self._init_standard()

    def _init_from_registry(self):
        """从注册表初始化（自动模式）"""
        self._node_graph_widget = None
        self._node_selector = None
        self._engine = ExecutionEngine(self)

        # Execution state machine
        self._exec_ctrl = ExecutionController(
            engine=self._engine,
            graph_getter=lambda: self._node_graph_widget.graph,
            on_before_execute=self._reset_all_node_states,
            parent=self,
        )
        self._exec_ctrl.state_changed.connect(self._sync_execution_ui)

        self._init_ui()
        self._auto_build_menu()
        self._auto_build_toolbar()
        self._init_statusbar()
        self._auto_wire_systems()
        self._connect_signals()

        logger.info("MainWindow initialized (auto mode)")

    def _init_standard(self):
        """标准初始化（手动模式）"""
        self._node_graph_widget = None
        self._node_selector = None
        self._engine = ExecutionEngine(self)

        # Execution state machine
        self._exec_ctrl = ExecutionController(
            engine=self._engine,
            graph_getter=lambda: self._node_graph_widget.graph,
            on_before_execute=self._reset_all_node_states,
            parent=self,
        )
        self._exec_ctrl.state_changed.connect(self._sync_execution_ui)

        self._init_ui()
        self._init_menu()
        self._init_toolbar()
        self._init_statusbar()
        self._wire_blueprint_system()
        self._wire_project_system()
        self._connect_signals()

        logger.info("MainWindow initialized (standard mode)")

        # Execution state machine — centralized in ExecutionController
        self._exec_ctrl = ExecutionController(
            engine=self._engine,
            graph_getter=lambda: self._node_graph_widget.graph,
            on_before_execute=self._reset_all_node_states,
            parent=self,
        )
        self._exec_ctrl.state_changed.connect(self._sync_execution_ui)

        self._init_ui()
        self._init_menu()
        self._init_toolbar()
        self._init_statusbar()
        self._wire_blueprint_system()
        self._wire_project_system()
        self._connect_signals()

        logger.info("MainWindow initialized")

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        self._node_graph_widget = NodeGraphWidget()
        self._right_panel = self._create_right_panel()

        self._splitter.addWidget(self._node_graph_widget)
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

    def _init_menu(self):
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("文件(&F)")

        new_action = QAction("新建项目", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._on_new_project)
        file_menu.addAction(new_action)

        open_action = QAction("打开项目", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._on_open_project)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        save_action = QAction("保存", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._on_save_project)
        file_menu.addAction(save_action)

        save_as_action = QAction("另存为", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self._on_save_project_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        save_template_action = QAction("保存为模板", self)
        save_template_action.triggered.connect(self._on_save_as_template)
        file_menu.addAction(save_template_action)

        file_menu.addSeparator()

        file_menu.addAction("退出", self.close)

        # Run menu
        run_menu = menu_bar.addMenu("运行(&R)")
        run_menu.addAction("单次执行", self._exec_ctrl.execute_once)
        run_menu.addAction("停止执行", self._exec_ctrl.stop)
        run_menu.addSeparator()
        self._action_loop = QAction("循环运行", self)
        self._action_loop.setCheckable(True)
        self._action_loop.triggered.connect(self._exec_ctrl.toggle_loop)
        run_menu.addAction(self._action_loop)

        # View menu
        view_menu = menu_bar.addMenu("视图(&V)")
        view_menu.addAction("重置缩放", self._on_reset_zoom)
        view_menu.addAction("适应选中", self._on_fit_selection)
        view_menu.addSeparator()
        self._action_ruler = QAction("尺子工具", self)
        self._action_ruler.setCheckable(True)
        self._action_ruler.triggered.connect(self._on_toggle_ruler)
        view_menu.addAction(self._action_ruler)

        # Help menu
        help_menu = menu_bar.addMenu("帮助(&H)")
        help_menu.addAction("关于", self._on_about)

    def _init_statusbar(self):
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._statusbar.showMessage("就绪")

    def _init_toolbar(self):
        toolbar = self.addToolBar("执行")
        toolbar.setMovable(False)

        self._btn_single = QAction("▶ 单次", self)
        self._btn_single.triggered.connect(self._exec_ctrl.execute_once)
        toolbar.addAction(self._btn_single)

        self._btn_loop = QAction("🔁 循环", self)
        self._btn_loop.triggered.connect(self._exec_ctrl.toggle_loop)
        toolbar.addAction(self._btn_loop)

        toolbar.addSeparator()

        self._btn_save = QAction("💾 保存", self)
        self._btn_save.triggered.connect(self._on_save_project)
        toolbar.addAction(self._btn_save)

        toolbar.addSeparator()

        self._btn_clear = QAction("✕ 清空", self)
        self._btn_clear.triggered.connect(self._on_new_project)
        toolbar.addAction(self._btn_clear)

        toolbar.addSeparator()

        self._btn_ruler = QAction("📏 尺子", self)
        self._btn_ruler.setCheckable(True)
        self._btn_ruler.triggered.connect(self._on_toggle_ruler)
        toolbar.addAction(self._btn_ruler)

    def _connect_signals(self):
        graph = self._node_graph_widget.graph
        graph.node_created.connect(self._on_node_created)
        graph.node_double_clicked.connect(self._on_node_double_clicked)
        graph.node_selection_changed.connect(self._on_node_selection_changed)
        self._node_graph_widget.node_replace_requested.connect(self._on_replace_requested)
        self._node_graph_widget.node_delete_requested.connect(self._on_delete_requested)
        self._node_graph_widget.node_created_with_meta.connect(self._on_node_created_with_meta)

        self._engine.execution_started.connect(self._on_engine_started)
        self._engine.execution_finished.connect(self._on_engine_finished)
        self._engine.node_state_changed.connect(self._on_node_state_changed)
        self._engine.progress_updated.connect(self._on_progress_updated)
        self._image_viewer.ruler_measurement.connect(self._on_ruler_measurement)
        self._image_viewer.pixel_hovered.connect(self._info_panel.update_info)

        # Project system signals
        self._project.on_project_modified.connect(self._on_project_modified)

    def _wire_blueprint_system(self):
        """Wire BlueprintSystem to the graph and execution callbacks.

        Bridge commands (from REST API) are now handled by BlueprintSystem,
        not by MainWindow directly.
        """
        self._blueprint.wire(
            graph_getter=lambda: self._node_graph_widget.graph,
            on_execute=self._exec_ctrl.execute,
            on_stop=self._exec_ctrl.stop,
            on_clear=self._on_new_project,
            on_loop_on=self._exec_ctrl.enable_loop,
            on_loop_off=self._exec_ctrl.disable_loop,
        )

    def _wire_project_system(self):
        """Wire ProjectSystem to the graph.

        Called after UI is created to enable project save/load operations.
        """
        self._project.wire(
            graph_getter=lambda: self._node_graph_widget.graph,
        )
        logger.info("ProjectSystem wired")

    # ------------------------------------------------------------------
    # Auto-wiring and auto-building (for from_registry mode)
    # ------------------------------------------------------------------

    def _auto_wire_systems(self):
        """自动绑定所有系统"""
        graph_getter = lambda: self._node_graph_widget.graph

        # BlueprintSystem 需要特殊的 wire 参数
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
                logger.info("[MainWindow] Auto-wired system: Blueprint")
            except Exception as e:
                logger.error(f"[MainWindow] Failed to wire Blueprint: {e}")

        # 其他系统使用通用 wire
        for name, system in self._systems.items():
            if name == "Blueprint":
                continue  # 已经处理过

            reg = self._system_registrations.get(name)
            if reg and reg.auto_wire and hasattr(system, 'wire'):
                try:
                    system.wire(graph_getter=graph_getter)
                    logger.info(f"[MainWindow] Auto-wired system: {name}")
                except Exception as e:
                    logger.error(f"[MainWindow] Failed to wire {name}: {e}")

    def _auto_build_menu(self):
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

    def _auto_build_toolbar(self):
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
        self._attach_embedded_widget(node, node_id)
        logger.info(f"Node created with meta: {node.name()} ({node_id}), opening editor")
        self._open_node_editor(node, node_id)

    @Slot(list)
    def _on_node_selection_changed(self, selected_nodes):
        if not selected_nodes:
            self._statusbar.showMessage("就绪")
            return

        node = selected_nodes[-1]
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
        node_id = getattr(node, "_node_id", "")
        if node_id:
            logger.info(f"Edit node: {node.name()} ({node_id})")
            self._open_node_editor(node, node_id)
        else:
            logger.info(f"Select type for node: {node.name()}")
            self._open_node_selector(node)

    @Slot(object)
    def _on_replace_requested(self, node):
        logger.info(f"Replace requested for: {node.name()}")
        self._pending_replace_node = node
        self._open_node_selector(node, replace_mode=True)

    def _on_delete_requested(self, node):
        logger.info(f"Deleting node: {node.name()}")
        self._node_graph_widget.graph.remove_node(node)

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

    # ------------------------------------------------------------------
    # Execution control
    # ------------------------------------------------------------------

    def _on_new_project(self):
        """Create a new project, prompting to save if modified."""
        if self._project.is_modified:
            reply = QMessageBox.question(
                self,
                "保存项目",
                "当前项目已修改，是否保存？",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Save:
                if not self._on_save_project():
                    return  # Save failed, don't create new
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        self._project.new_project()
        self._statusbar.showMessage("新项目已创建")
        self.setWindowTitle("ImageTools")
        logger.info("New project created")

    def _sync_execution_ui(self):
        """Single sync point for toolbar/menu — called on every state change."""
        ctrl = self._exec_ctrl
        self._btn_loop.setText("■ 停止" if ctrl.loop_mode else "🔁 循环")
        self._action_loop.setChecked(ctrl.loop_mode)
        self._btn_single.setEnabled(not ctrl.is_running)

    def _on_engine_started(self):
        self._statusbar.showMessage("正在执行...")
        logger.info("Engine started")

    # ------------------------------------------------------------------
    # Embedded widget support
    # ------------------------------------------------------------------

    _EMBEDDED_WIDGET_MAP = {
        "processing/statistics/histogram": "_create_histogram_embedded",
    }

    def _attach_embedded_widget(self, node, node_id: str):
        factory = self._EMBEDDED_WIDGET_MAP.get(node_id)
        if not factory:
            return
        method = getattr(self, factory, None)
        if method:
            logger.info(f"[EmbeddedWidget] Attaching {factory} for {node_id}")
            method(node)

    def _create_histogram_embedded(self, node):
        from ui.widgets.node_histogram_widget import NodeHistogramWidget
        widget = NodeHistogramWidget(parent=node.view)
        node.add_embedded_widget(widget)
        logger.info(f"[EmbeddedWidget] Histogram widget added to {node.name()}, "
                     f"node_size={node.view._width:.0f}x{node.view._height:.0f}")

    def _update_embedded_widgets(self):
        from nodes.processing.statistics.histogram.node import HistogramNode
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

    def _on_progress_updated(self, current: int, total: int):
        self._statusbar.showMessage(f"执行中... {current}/{total}")

    def _reset_all_node_states(self):
        graph = self._node_graph_widget.graph
        for node in graph.all_nodes():
            if isinstance(node, GraphNode):
                node.update_state_color("idle")

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
        QMessageBox.about(
            self,
            "关于 ImageTools",
            f"ImageTools {config.get('app.version', '0.1.0')}\n\n图像处理蓝图工具",
        )

    # ------------------------------------------------------------------
    # Project operations
    # ------------------------------------------------------------------

    def _on_open_project(self):
        """Open an existing project file."""
        if self._project.is_modified:
            reply = QMessageBox.question(
                self,
                "保存项目",
                "当前项目已修改，是否保存？",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Save:
                if not self._on_save_project():
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "打开项目文件",
            "",
            "ImageTools 项目 (*.itproj);;所有文件 (*)",
        )

        if not path:
            return

        project_path = Path(path)

        # Check for auto-save
        if self._project.check_autosave(project_path):
            from ui.dialogs import AutoSaveRecoveryDialog
            dialog = AutoSaveRecoveryDialog(
                project_path,
                project_path.with_suffix(project_path.suffix + "~"),
                self,
            )
            dialog.exec()

            if dialog.should_recover:
                if self._project.recover_autosave(project_path):
                    self._statusbar.showMessage("已恢复自动保存的项目")
                    self._update_window_title()
                    return

        # Normal load
        if self._project.load_project(project_path):
            self._statusbar.showMessage(f"已加载: {project_path.name}")
            self._update_window_title()
        else:
            QMessageBox.warning(
                self,
                "加载失败",
                f"无法加载项目文件:\n{project_path}",
            )

    def _on_save_project(self) -> bool:
        """Save the current project. Returns True if saved."""
        if self._project.current_path:
            # Save to existing path
            if self._project.save_project():
                self._statusbar.showMessage("项目已保存")
                self._update_window_title()
                return True
            else:
                QMessageBox.warning(self, "保存失败", "无法保存项目文件")
                return False
        else:
            # No path yet, do Save As
            return self._on_save_project_as()

    def _on_save_project_as(self) -> bool:
        """Save the current project to a new file. Returns True if saved."""
        from ui.dialogs import SaveDialog

        # Ensure project exists (auto-create if needed, without clearing graph)
        if self._project.current_project is None:
            self._project.new_project(clear_graph=False)

        dialog = SaveDialog(
            self,
            project_name=self._project.current_project.metadata.name
            if self._project.current_project
            else "",
        )

        if dialog.exec() != SaveDialog.DialogCode.Accepted:
            return False

        # Update metadata
        if self._project.current_project:
            self._project.current_project.metadata.name = dialog.project_name
            self._project.current_project.metadata.description = dialog.description
            self._project.current_project.metadata.author = dialog.author
            self._project.current_project.metadata.tags = dialog.tags

        # Get save path
        default_name = dialog.project_name or "未命名项目"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "保存项目文件",
            f"{default_name}.itproj",
            "ImageTools 项目 (*.itproj);;所有文件 (*)",
        )

        if not path:
            return False

        # Ensure .itproj extension
        save_path = Path(path)
        if save_path.suffix != ".itproj":
            save_path = save_path.with_suffix(".itproj")

        if self._project.save_project(save_path):
            self._statusbar.showMessage(f"项目已保存: {save_path.name}")
            self._update_window_title()
            return True
        else:
            QMessageBox.warning(self, "保存失败", "无法保存项目文件")
            return False

    def _on_save_as_template(self):
        """Save current project as a template."""
        if not self._project.has_project:
            QMessageBox.information(self, "提示", "没有打开的项目")
            return

        from ui.dialogs import SaveDialog

        dialog = SaveDialog(self)
        dialog.setWindowTitle("保存为模板")

        if dialog.exec() != SaveDialog.DialogCode.Accepted:
            return

        if not dialog.project_name:
            QMessageBox.warning(self, "错误", "请输入模板名称")
            return

        template = self._project.save_as_template(
            dialog.project_name,
            dialog.description,
        )

        if template:
            QMessageBox.information(
                self,
                "模板已保存",
                f"模板 '{dialog.project_name}' 已保存",
            )
        else:
            QMessageBox.warning(self, "保存失败", "无法保存模板")

    def _update_window_title(self):
        """Update window title with project name."""
        base_title = "ImageTools"
        if self._project.has_project:
            name = self._project.current_project.metadata.name
            self.setWindowTitle(f"{name} - {base_title}")
        else:
            self.setWindowTitle(base_title)

    def closeEvent(self, event):
        """Handle window close event."""
        if self._project.is_modified:
            reply = QMessageBox.question(
                self,
                "保存项目",
                "项目已修改，是否保存？",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Save:
                if not self._on_save_project():
                    event.ignore()
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return

        # Stop auto-save
        self._project.disable_autosave()

        event.accept()
