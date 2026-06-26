import os

os.environ["QT_API"] = "pyside6"

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QSplitter,
    QMenuBar, QStatusBar, QMenu, QMessageBox,
)

from core.logger import logger
from core.config import config
from core.node_base.registry import node_registry
from core.engine.executor import ExecutionEngine
from core.engine.result import ExecutionResult
from systems.blueprint.system import BlueprintSystem
from systems.image_display.system import ImageDisplaySystem
from ui.node_graph_widget import NodeGraphWidget, GraphNode
from ui.node_selector import NodeSelectorWindow


class MainWindow(QMainWindow):
    def __init__(
        self,
        image_display: ImageDisplaySystem | None = None,
        blueprint: BlueprintSystem | None = None,
    ):
        super().__init__()
        self.setWindowTitle(config.get("ui.window_title", "ImageTools"))
        self.resize(
            config.get("ui.window_width", 1600),
            config.get("ui.window_height", 900),
        )

        # Injected systems (with defaults for backward compat)
        self._image_display = image_display or ImageDisplaySystem()
        self._blueprint = blueprint or BlueprintSystem()

        self._node_graph_widget = None
        self._node_selector = None
        self._engine = ExecutionEngine(self)
        self._loop_mode = False
        self._init_ui()
        self._init_menu()
        self._init_toolbar()
        self._init_statusbar()
        self._wire_blueprint_system()
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
        return ImageViewerWidget(self._image_display)

    def _init_menu(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("文件(&F)")
        file_menu.addAction("新建项目", self._on_new_project)
        file_menu.addSeparator()
        file_menu.addAction("退出", self.close)

        run_menu = menu_bar.addMenu("运行(&R)")
        run_menu.addAction("开始执行", self._on_execute)
        run_menu.addAction("停止执行", self._on_stop)
        run_menu.addSeparator()
        self._action_loop = QAction("循环运行", self)
        self._action_loop.setCheckable(True)
        self._action_loop.triggered.connect(self._on_toggle_loop)
        run_menu.addAction(self._action_loop)

        view_menu = menu_bar.addMenu("视图(&V)")
        view_menu.addAction("重置缩放", self._on_reset_zoom)
        view_menu.addAction("适应选中", self._on_fit_selection)
        view_menu.addSeparator()
        self._action_ruler = QAction("尺子工具", self)
        self._action_ruler.setCheckable(True)
        self._action_ruler.triggered.connect(self._on_toggle_ruler)
        view_menu.addAction(self._action_ruler)

        help_menu = menu_bar.addMenu("帮助(&H)")
        help_menu.addAction("关于", self._on_about)

    def _init_statusbar(self):
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._statusbar.showMessage("就绪")

    def _init_toolbar(self):
        toolbar = self.addToolBar("执行")
        toolbar.setMovable(False)

        self._btn_execute = QAction("▶ 开始", self)
        self._btn_execute.triggered.connect(self._on_execute)
        toolbar.addAction(self._btn_execute)

        self._btn_stop = QAction("■ 停止", self)
        self._btn_stop.triggered.connect(self._on_stop)
        toolbar.addAction(self._btn_stop)

        toolbar.addSeparator()

        self._btn_loop = QAction("🔁 循环", self)
        self._btn_loop.setCheckable(True)
        self._btn_loop.triggered.connect(self._on_toggle_loop)
        toolbar.addAction(self._btn_loop)

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
        self._node_graph_widget.node_created_with_meta.connect(self._on_node_created_with_meta)

        self._engine.execution_started.connect(self._on_engine_started)
        self._engine.execution_finished.connect(self._on_engine_finished)
        self._engine.node_state_changed.connect(self._on_node_state_changed)
        self._engine.progress_updated.connect(self._on_progress_updated)
        self._right_panel.ruler_measurement.connect(self._on_ruler_measurement)

    def _wire_blueprint_system(self):
        """Wire BlueprintSystem to the graph and execution callbacks.

        Bridge commands (from REST API) are now handled by BlueprintSystem,
        not by MainWindow directly.
        """
        self._blueprint.wire(
            graph_getter=lambda: self._node_graph_widget.graph,
            on_execute=self._on_execute,
            on_stop=self._on_stop,
            on_clear=self._on_new_project,
            on_loop_on=self._on_toggle_loop,
            on_loop_off=self._on_toggle_loop,
        )

    # ------------------------------------------------------------------
    # Node / graph event handlers
    # ------------------------------------------------------------------

    @Slot(object)
    def _on_node_created(self, node):
        logger.info(f"Node created in graph: {node.name()}")

    @Slot(object, str)
    def _on_node_created_with_meta(self, node, node_id: str):
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

    @Slot(str)
    def _on_node_type_selected(self, node_id: str):
        if hasattr(self, '_pending_replace_node') and self._pending_replace_node:
            self._node_graph_widget.replace_node(self._pending_replace_node, node_id)
            self._pending_replace_node = None
        elif self._node_selector and self._node_selector._edit_mode:
            target = self._node_selector._target_node
            if target:
                param_values = self._node_selector.get_param_values()
                target._param_values = param_values
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
    # Execution control
    # ------------------------------------------------------------------

    def _on_new_project(self):
        self._node_graph_widget.graph.clear_session()
        self._statusbar.showMessage("新项目已创建")
        logger.info("New project created")

    def _on_toggle_loop(self):
        self._loop_mode = not self._loop_mode
        self._action_loop.setChecked(self._loop_mode)
        self._btn_loop.setChecked(self._loop_mode)
        if self._loop_mode:
            logger.info("Loop mode enabled")
            self._statusbar.showMessage("循环模式已启用")
        else:
            logger.info("Loop mode disabled")
            self._statusbar.showMessage("循环模式已关闭")

    def _on_execute(self):
        graph = self._node_graph_widget.graph
        self._reset_all_node_states()
        self._engine.execute(graph)

    def _on_stop(self):
        self._loop_mode = False
        self._action_loop.setChecked(False)
        self._btn_loop.setChecked(False)
        self._engine.cancel()
        logger.info("Execution stop requested")
        self._statusbar.showMessage("正在停止...")

    def _on_engine_started(self):
        self._statusbar.showMessage("正在执行...")
        logger.info("Engine started")

    @Slot(object)
    def _on_engine_finished(self, result: ExecutionResult):
        self._right_panel.set_execution_results(result)

        if self._loop_mode:
            logger.info(f"Loop: execution finished (success={result.success}), re-executing...")
            self._statusbar.showMessage(f"循环执行中... (上次: {'成功' if result.success else '失败'})")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, self._on_execute)
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

    def _on_fit_selection(self):
        self._node_graph_widget.graph.fit_to_selection()

    def _on_toggle_ruler(self):
        enabled = self._right_panel.toggle_ruler()
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
