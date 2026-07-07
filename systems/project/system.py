"""ProjectSystem — manages project file lifecycle.

Handles project save/load operations, auto-save integration,
and provides a clean API for UI components to interact with
the project file system.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, TYPE_CHECKING

from PySide6.QtWidgets import QWidget

from core.config import config
from core.events import EventEmitter
from core.logger import logger
from core.project import (
    AutoSaveManager,
    ConnectionData,
    NodeData,
    ProjectData,
    ProjectMetadata,
    ProjectSerializer,
    project_migrator,
    project_validator,
    TemplateManager,
)
from core.system.auto_register import register_system
from systems.base import ISystem

if TYPE_CHECKING:
    from NodeGraphQt import NodeGraph


@register_system(
    name="Project",
    depends_on=["Blueprint"],
    auto_wire=True,
    menu_items=[
        {"text": "新建项目", "method": "_on_new_project", "shortcut": "Ctrl+N"},
        {"text": "打开项目", "method": "_on_open_project", "shortcut": "Ctrl+O"},
        {"separator_before": True},
        {"text": "保存", "method": "_on_save_project", "shortcut": "Ctrl+S"},
        {"text": "另存为", "method": "_on_save_project_as", "shortcut": "Ctrl+Shift+S"},
        {"separator_before": True},
        {"text": "保存为模板", "method": "_on_save_as_template"},
    ],
    toolbar_items=[
        {"text": "💾 保存", "method": "_on_save_project"},
    ],
)
class ProjectSystem(ISystem):
    """System for managing project files.

    Provides:
    - Project save/load with version migration
    - Auto-save functionality
    - Template management
    - Project state tracking
    """

    # 项目根目录（相对于此文件的位置）
    _DEFAULT_ROOT = Path(__file__).parent.parent.parent

    def __init__(self, root_dir: Path = None):
        self._root_dir = root_dir if root_dir is not None else self._DEFAULT_ROOT
        self._current_path: Path | None = None
        self._current_project: ProjectData | None = None
        self._is_modified: bool = False

        # Sub-managers
        self._autosave = AutoSaveManager()
        self._templates = TemplateManager(self._root_dir)

        # Events
        self.on_project_loaded = EventEmitter()
        self.on_project_saved = EventEmitter()
        self.on_project_modified = EventEmitter()
        self.on_project_closed = EventEmitter()

        # Graph reference (set during wire())
        self._graph_getter: Callable[[], "NodeGraph"] | None = None

    # ------------------------------------------------------------------
    # ISystem
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "Project"

    def initialize(self) -> bool:
        """Initialize the project system."""
        # Configure auto-save from app config
        interval = config.get("project.autosave_interval", 60)
        self._autosave.set_interval(interval)
        logger.info("[ProjectSystem] Initialized")
        return True

    def shutdown(self) -> None:
        """Shutdown the project system."""
        self._autosave.stop()
        logger.info("[ProjectSystem] Shutdown")

    # ------------------------------------------------------------------
    # Wiring
    # ------------------------------------------------------------------

    def wire(self, graph_getter: Callable[[], "NodeGraph"]) -> None:
        """Wire the system to the graph.

        Args:
            graph_getter: Callable that returns the current NodeGraph.
        """
        self._graph_getter = graph_getter

        # Set up auto-save data provider
        self._autosave.set_data_provider(self._collect_project_data)

        logger.info("[ProjectSystem] Wired")

    # ------------------------------------------------------------------
    # Project operations
    # ------------------------------------------------------------------

    @property
    def current_path(self) -> Path | None:
        """Current project file path."""
        return self._current_path

    @property
    def current_project(self) -> ProjectData | None:
        """Current project data."""
        return self._current_project

    @property
    def is_modified(self) -> bool:
        """Whether the project has unsaved changes."""
        return self._is_modified

    @property
    def has_project(self) -> bool:
        """Whether a project is currently open."""
        return self._current_project is not None

    def new_project(self, name: str = "未命名项目", clear_graph: bool = True) -> ProjectData:
        """Create a new empty project.

        Args:
            name: Project name.
            clear_graph: Whether to clear the graph (default True).

        Returns:
            New ProjectData instance.
        """
        # Stop auto-save for current project
        self._autosave.stop()

        # Create new project
        project = ProjectData(
            metadata=ProjectMetadata(name=name),
        )

        self._current_project = project
        self._current_path = None
        self._is_modified = False

        # Clear the graph if requested
        if clear_graph and self._graph_getter:
            self._graph_getter().clear_session()

        self.on_project_loaded.emit(project)
        logger.info(f"[ProjectSystem] New project: {name}")
        return project

    def save_project(self, path: Path | None = None) -> bool:
        """Save the current project.

        Args:
            path: Save path. If None, uses current path.

        Returns:
            True if saved successfully.
        """
        # Auto-create project if none exists (user may have created nodes directly)
        if self._current_project is None:
            logger.info("[ProjectSystem] No project exists, auto-creating from graph state")
            self._current_project = ProjectData(
                metadata=ProjectMetadata(name="未命名项目"),
            )

        save_path = path or self._current_path
        if save_path is None:
            logger.warning("[ProjectSystem] No save path specified")
            return False

        # Collect current state from graph
        self._update_project_from_graph()

        # Save
        try:
            ProjectSerializer.save(self._current_project, save_path)
            self._current_path = save_path
            self._is_modified = False

            # Update auto-save path and remove auto-save file
            self._autosave.set_project_path(save_path)
            AutoSaveManager.remove_autosave(save_path)

            self.on_project_saved.emit(self._current_project, save_path)
            logger.info(f"[ProjectSystem] Saved to {save_path}")
            return True

        except Exception as e:
            logger.error(f"[ProjectSystem] Save failed: {e}")
            return False

    def load_project(self, path: Path) -> bool:
        """Load a project from file.

        Args:
            path: Path to the project file.

        Returns:
            True if loaded successfully.
        """
        try:
            # Stop auto-save for current project
            self._autosave.stop()

            # Load and validate
            data = ProjectSerializer.load(path)
            raw_dict = data.to_dict()

            # Validate
            validation = project_validator.validate(raw_dict)
            if not validation.is_valid:
                for error in validation.errors:
                    logger.error(f"[ProjectSystem] Validation: {error}")
                # Continue loading even with errors (best effort)

            # Migrate if needed
            current_version = data.version
            target_version = project_migrator.get_latest_version()
            if project_migrator.needs_migration(raw_dict, target_version):
                raw_dict = project_migrator.migrate(raw_dict, target_version)
                data = ProjectData.from_dict(raw_dict)
                logger.info(f"[ProjectSystem] Migrated: {current_version} -> {target_version}")

            # Apply to graph
            self._apply_project_to_graph(data)

            self._current_project = data
            self._current_path = path
            self._is_modified = False

            # Start auto-save
            self._autosave.set_project_path(path)
            self._autosave.start()

            self.on_project_loaded.emit(data)
            logger.info(f"[ProjectSystem] Loaded: {path}")
            return True

        except Exception as e:
            logger.error(f"[ProjectSystem] Load failed: {e}")
            return False

    def check_autosave(self, project_path: Path) -> bool:
        """Check if auto-save recovery is available.

        Args:
            project_path: Path to the project file.

        Returns:
            True if auto-save recovery is available.
        """
        return AutoSaveManager.has_autosave(project_path)

    def recover_autosave(self, project_path: Path) -> bool:
        """Recover from auto-save file.

        Args:
            project_path: Path to the main project file.

        Returns:
            True if recovered successfully.
        """
        data = AutoSaveManager.load_autosave(project_path)
        if data is None:
            return False

        try:
            self._apply_project_to_graph(data)
            self._current_project = data
            self._current_path = project_path
            self._is_modified = True  # Mark as modified since it's from auto-save

            # Start auto-save
            self._autosave.set_project_path(project_path)
            self._autosave.start()

            self.on_project_loaded.emit(data)
            logger.info(f"[ProjectSystem] Recovered auto-save: {project_path}")
            return True

        except Exception as e:
            logger.error(f"[ProjectSystem] Auto-save recovery failed: {e}")
            return False

    def mark_modified(self) -> None:
        """Mark the project as having unsaved changes."""
        if not self._is_modified:
            self._is_modified = True
            self.on_project_modified.emit()

    # ------------------------------------------------------------------
    # Template operations
    # ------------------------------------------------------------------

    def get_templates(self):
        """Get list of available templates."""
        return self._templates.list_templates()

    def create_from_template(self, template_id: str) -> ProjectData | None:
        """Create a new project from a template.

        Args:
            template_id: Template identifier.

        Returns:
            New ProjectData or None if template not found.
        """
        data = self._templates.get_template(template_id)
        if data is None:
            return None

        # Clear instance-specific data
        data.metadata.name = "未命名项目"
        data.metadata.created_at = ""
        data.metadata.modified_at = ""

        self._current_project = data
        self._current_path = None
        self._is_modified = False

        # Apply to graph
        self._apply_project_to_graph(data)

        self.on_project_loaded.emit(data)
        logger.info(f"[ProjectSystem] Created from template: {template_id}")
        return data

    def save_as_template(self, name: str, description: str = ""):
        """Save current project as a template.

        Args:
            name: Template name.
            description: Template description.

        Returns:
            TemplateInfo if saved successfully.
        """
        if self._current_project is None:
            return None

        self._update_project_from_graph()
        return self._templates.save_as_template(
            self._current_project, name, description
        )

    # ------------------------------------------------------------------
    # Auto-save control
    # ------------------------------------------------------------------

    def enable_autosave(self) -> None:
        """Enable auto-save."""
        self._autosave.enable()

    def disable_autosave(self) -> None:
        """Disable auto-save."""
        self._autosave.disable()

    def set_autosave_interval(self, seconds: int) -> None:
        """Set auto-save interval.

        Args:
            seconds: Interval in seconds.
        """
        self._autosave.set_interval(seconds)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _collect_project_data(self) -> ProjectData:
        """Collect current project state from graph."""
        self._update_project_from_graph()
        return self._current_project

    def _update_project_from_graph(self) -> None:
        """Update project data from current graph state."""
        if self._current_project is None:
            self._current_project = ProjectData()

        if self._graph_getter is None:
            logger.warning("[ProjectSystem] No graph getter set, cannot collect nodes")
            return

        graph = self._graph_getter()

        # Collect nodes
        nodes = []
        all_graph_nodes = graph.all_nodes()
        logger.info(f"[ProjectSystem] Found {len(all_graph_nodes)} nodes in graph")

        for node in all_graph_nodes:
            node_id = getattr(node, "_node_id", "")
            node_name = node.name()
            node_data = NodeData(
                id=node_id,
                instance_id=node_name,
                name=node_name,
                position=NodePosition(x=node.x_pos(), y=node.y_pos()),
                param_values=dict(getattr(node, "_param_values", {})),
                is_placeholder=getattr(node, "_is_placeholder", False),
            )

            # Collect optional port states
            if hasattr(node, "_optional_ports"):
                for opc_name, port_label in node._optional_ports.items():
                    param_key = f"_opt_{opc_name}"
                    if param_key in node._param_values:
                        node_data.optional_port_states[opc_name] = node._param_values[param_key]

            nodes.append(node_data)
            logger.debug(f"[ProjectSystem] Collected node: {node_name} (id={node_id})")

        # Collect connections
        connections = []
        for node in all_graph_nodes:
            for port in node.output_ports():
                for connected_port in port.connected_ports():
                    # Get the parent node of the connected port
                    connected_node = connected_port.node()
                    conn = ConnectionData(
                        from_node=node.name(),
                        from_port=port.name(),
                        to_node=connected_node.name(),
                        to_port=connected_port.name(),
                    )
                    connections.append(conn)

        self._current_project.nodes = nodes
        self._current_project.connections = connections
        logger.info(f"[ProjectSystem] Collected {len(nodes)} nodes, {len(connections)} connections")

    def _apply_project_to_graph(self, project: ProjectData) -> None:
        """Apply project data to the graph.

        Args:
            project: Project data to apply.
        """
        if self._graph_getter is None:
            logger.warning("[ProjectSystem] No graph getter, cannot apply project")
            return

        from core.node_base.registry import node_registry

        graph = self._graph_getter()

        # Clear current graph
        graph.clear_session()

        # Create nodes
        node_map = {}  # instance_id -> graph_node
        for node_data in project.nodes:
            meta = node_registry.get_meta(node_data.id)

            if meta is None:
                # Create placeholder node
                logger.warning(
                    f"[ProjectSystem] Node type not found: {node_data.id}, creating placeholder"
                )
                node = graph.create_node(
                    "imagetools.GraphNode",
                    name=f"[缺失] {node_data.name}",
                    pos=(node_data.position.x, node_data.position.y),
                )
                node._node_id = node_data.id
                node._is_placeholder = True
                node.set_color(200, 100, 100)  # Red for placeholder
            else:
                # Create normal node
                node = graph.create_node(
                    "imagetools.GraphNode",
                    name=meta.name,
                    pos=(node_data.position.x, node_data.position.y),
                )
                node.set_node_meta(meta)

            # Apply parameters
            if node_data.param_values:
                node._param_values.update(node_data.param_values)
                node.sync_port_visibility()

            # Apply optional port states
            for opc_name, visible in node_data.optional_port_states.items():
                node.set_optional_port_visible(opc_name, visible)

            node_map[node_data.instance_id] = node

        # Create connections
        for conn_data in project.connections:
            from_node = node_map.get(conn_data.from_node)
            to_node = node_map.get(conn_data.to_node)

            if from_node is None or to_node is None:
                logger.warning(
                    f"[ProjectSystem] Connection node not found: "
                    f"{conn_data.from_node} -> {conn_data.to_node}"
                )
                continue

            from_port = from_node.get_output(conn_data.from_port)
            to_port = to_node.get_input(conn_data.to_port)

            if from_port is None or to_port is None:
                # Try with label mapping
                if hasattr(from_node, '_port_label_to_name'):
                    for label, name in from_node._port_label_to_name.items():
                        if name == conn_data.from_port:
                            from_port = from_node.get_output(label)
                            break

                if hasattr(to_node, '_port_label_to_name'):
                    for label, name in to_node._port_label_to_name.items():
                        if name == conn_data.to_port:
                            to_port = to_node.get_input(label)
                            break

            if from_port and to_port:
                try:
                    from_port.connect_to(to_port, push_undo=False)
                except Exception as e:
                    logger.warning(f"[ProjectSystem] Connection failed: {e}")

        logger.info(
            f"[ProjectSystem] Applied project: {len(project.nodes)} nodes, "
            f"{len(project.connections)} connections"
        )


# Import NodePosition here to avoid circular imports
from core.project.models import NodePosition
