"""集成测试 — 测试系统间的连接和端到端流程。

这些测试验证模块间的集成是否正确，而不是单独测试每个模块。
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from core.project import (
    ProjectData,
    ProjectMetadata,
    NodeData,
    ConnectionData,
    ProjectSerializer,
)
from core.project.models import NodePosition
from systems.project.system import ProjectSystem


class MockNodeGraph:
    """模拟 NodeGraph"""

    def __init__(self):
        self._nodes = []

    def all_nodes(self):
        return self._nodes

    def clear_session(self):
        self._nodes.clear()

    def create_node(self, node_type, name=None, pos=None):
        node = MockGraphNode(name or "unnamed", pos)
        self._nodes.append(node)
        return node


class MockGraphNode:
    """模拟 GraphNode"""

    def __init__(self, name, pos=None):
        self._name = name
        self._pos = pos or (0, 0)
        self._node_id = ""
        self._param_values = {}
        self._optional_ports = {}
        self._is_placeholder = False
        self._output_ports = {}
        self._input_ports = {}

    def name(self):
        return self._name

    def x_pos(self):
        return self._pos[0] if isinstance(self._pos, (tuple, list)) else self._pos.x() if hasattr(self._pos, 'x') else 0

    def y_pos(self):
        return self._pos[1] if isinstance(self._pos, (tuple, list)) else self._pos.y() if hasattr(self._pos, 'y') else 0

    def output_ports(self):
        return list(self._output_ports.values())

    def input_ports(self):
        return list(self._input_ports.values())

    def set_color(self, r, g, b):
        """模拟 set_color 方法"""
        pass

    def get_input(self, name):
        """模拟 get_input 方法"""
        return self._input_ports.get(name)

    def get_output(self, name):
        """模拟 get_output 方法"""
        return self._output_ports.get(name)

    def sync_port_visibility(self):
        """模拟 sync_port_visibility 方法"""
        pass

    def set_optional_port_visible(self, opc_name, visible):
        """模拟 set_optional_port_visible 方法"""
        pass

    def set_node_meta(self, meta):
        """模拟 set_node_meta 方法"""
        self._node_id = meta.id
        self._name = meta.name


class MockPort:
    """模拟 Port"""

    def __init__(self, name, parent_node=None):
        self._name = name
        self._connected = []
        self._parent_node = parent_node

    def name(self):
        return self._name

    def node(self):
        """返回父节点"""
        return self._parent_node

    def connected_ports(self):
        return self._connected

    def connect_to(self, other, push_undo=False):
        self._connected.append(other)


class TestProjectSystemIntegration:
    """ProjectSystem 集成测试"""

    def test_project_system_wiring(self, tmp_path):
        """测试 ProjectSystem 是否正确绑定到 graph"""
        system = ProjectSystem(tmp_path)
        graph = MockNodeGraph()

        # 初始状态：未绑定
        assert system._graph_getter is None

        # 绑定后
        system.wire(lambda: graph)
        assert system._graph_getter is not None
        assert system._graph_getter() is graph

    def test_collect_nodes_from_graph(self, tmp_path):
        """测试从 graph 收集节点数据"""
        system = ProjectSystem(tmp_path)
        graph = MockNodeGraph()

        # 创建节点
        node1 = graph.create_node("test", name="图集", pos=(100, 200))
        node1._node_id = "image_source/input_image_set"
        node1._param_values = {"source": "custom"}

        node2 = graph.create_node("test", name="圆检测", pos=(400, 200))
        node2._node_id = "detection/shape_detection/circle"
        node2._param_values = {"detection_method": "hough"}

        # 绑定
        system.wire(lambda: graph)

        # 创建项目并收集数据
        system.new_project(clear_graph=False)
        system._update_project_from_graph()

        # 验证
        project = system.current_project
        assert len(project.nodes) == 2
        assert project.nodes[0].name == "图集"
        assert project.nodes[0].id == "image_source/input_image_set"
        assert project.nodes[1].name == "圆检测"

    def test_collect_connections_from_graph(self, tmp_path):
        """测试从 graph 收集连接数据"""
        system = ProjectSystem(tmp_path)
        graph = MockNodeGraph()

        # 创建节点
        node1 = graph.create_node("test", name="图集")
        node1._node_id = "image_source/input_image_set"

        node2 = graph.create_node("test", name="圆检测")
        node2._node_id = "detection/shape_detection/circle"

        # 创建连接（设置父节点）
        out_port = MockPort("images", parent_node=node1)
        in_port = MockPort("images", parent_node=node2)

        node1._output_ports["images"] = out_port
        node2._input_ports["images"] = in_port

        # 模拟 connected_ports 返回
        out_port._connected = [in_port]

        # 绑定
        system.wire(lambda: graph)

        # 创建项目并收集数据
        system.new_project(clear_graph=False)
        system._update_project_from_graph()

        # 验证
        project = system.current_project
        assert len(project.connections) == 1
        assert project.connections[0].from_node == "图集"
        assert project.connections[0].to_node == "圆检测"

    def test_save_load_roundtrip(self, tmp_path):
        """测试保存和加载的完整流程"""
        system = ProjectSystem(tmp_path)
        graph = MockNodeGraph()

        # 创建节点
        node1 = graph.create_node("test", name="图集", pos=(100, 200))
        node1._node_id = "image_source/input_image_set"
        node1._param_values = {"source": "custom", "file_list": ["/path/to/image.jpg"]}

        # 绑定
        system.wire(lambda: graph)

        # 创建项目
        system.new_project(name="测试项目", clear_graph=False)

        # 保存
        save_path = tmp_path / "test_project.itproj"
        assert system.save_project(save_path) is True
        assert save_path.exists()

        # 创建新系统并加载
        system2 = ProjectSystem(tmp_path)
        graph2 = MockNodeGraph()
        system2.wire(lambda: graph2)

        assert system2.load_project(save_path) is True
        assert system2.current_project.metadata.name == "测试项目"

    def test_auto_create_project_on_save(self, tmp_path):
        """测试保存时自动创建项目"""
        system = ProjectSystem(tmp_path)
        graph = MockNodeGraph()

        # 创建节点
        node1 = graph.create_node("test", name="图集")
        node1._node_id = "image_source/input_image_set"

        # 绑定
        system.wire(lambda: graph)

        # 初始状态：没有项目
        assert system.current_project is None

        # 保存时应该自动创建项目
        save_path = tmp_path / "auto_created.itproj"
        system._current_project = ProjectData(
            metadata=ProjectMetadata(name="自动创建"),
        )
        assert system.save_project(save_path) is True

        # 验证项目已创建
        assert system.current_project is not None
        assert len(system.current_project.nodes) == 1

    def test_new_project_clears_graph(self, tmp_path):
        """测试新建项目清空 graph"""
        system = ProjectSystem(tmp_path)
        graph = MockNodeGraph()

        # 创建节点
        graph.create_node("test", name="图集")
        assert len(graph.all_nodes()) == 1

        # 绑定
        system.wire(lambda: graph)

        # 新建项目（清空 graph）
        system.new_project(clear_graph=True)
        assert len(graph.all_nodes()) == 0

    def test_new_project_preserves_graph(self, tmp_path):
        """测试新建项目保留 graph"""
        system = ProjectSystem(tmp_path)
        graph = MockNodeGraph()

        # 创建节点
        graph.create_node("test", name="图集")
        assert len(graph.all_nodes()) == 1

        # 绑定
        system.wire(lambda: graph)

        # 新建项目（不清空 graph）
        system.new_project(clear_graph=False)
        assert len(graph.all_nodes()) == 1

    def test_modified_tracking(self, tmp_path):
        """测试修改状态追踪"""
        system = ProjectSystem(tmp_path)
        graph = MockNodeGraph()
        system.wire(lambda: graph)

        # 初始状态
        assert system.is_modified is False

        # 标记修改
        system.mark_modified()
        assert system.is_modified is True

    def test_autosave_integration(self, tmp_path):
        """测试自动保存集成"""
        system = ProjectSystem(tmp_path)
        graph = MockNodeGraph()

        # 创建节点
        node1 = graph.create_node("test", name="图集")
        node1._node_id = "image_source/input_image_set"

        # 绑定
        system.wire(lambda: graph)

        # 创建项目并保存
        system.new_project(clear_graph=False)
        save_path = tmp_path / "autosave_test.itproj"
        system.save_project(save_path)

        # 手动触发自动保存
        autosave_path = system._autosave.save_now()
        assert autosave_path is not None
        assert autosave_path.exists()

        # 验证自动保存文件包含数据
        loaded = ProjectSerializer.load(autosave_path)
        assert len(loaded.nodes) == 1


class TestProjectSerializerIntegration:
    """ProjectSerializer 集成测试"""

    def test_serialize_full_project(self):
        """测试序列化完整项目"""
        project = ProjectData(
            version="1.0.0",
            metadata=ProjectMetadata(
                name="完整项目",
                description="测试描述",
                author="测试作者",
            ),
            nodes=[
                NodeData(
                    id="image_source/input_image_set",
                    instance_id="node_001",
                    name="图集",
                    position=NodePosition(x=100, y=200),
                    param_values={"source": "custom"},
                ),
                NodeData(
                    id="detection/shape_detection/circle",
                    instance_id="node_002",
                    name="圆检测",
                    position=NodePosition(x=400, y=200),
                    param_values={"detection_method": "hough"},
                ),
            ],
            connections=[
                ConnectionData(
                    from_node="node_001",
                    from_port="images",
                    to_node="node_002",
                    to_port="images",
                ),
            ],
        )

        # 序列化
        data = project.to_dict()

        # 验证结构
        assert "version" in data
        assert "metadata" in data
        assert "nodes" in data
        assert "connections" in data
        assert len(data["nodes"]) == 2
        assert len(data["connections"]) == 1

        # 反序列化
        restored = ProjectData.from_dict(data)
        assert restored.metadata.name == "完整项目"
        assert len(restored.nodes) == 2
        assert restored.nodes[0].id == "image_source/input_image_set"

    def test_save_load_file_integration(self, tmp_path):
        """测试文件保存和加载的完整流程"""
        project = ProjectData(
            metadata=ProjectMetadata(name="文件测试"),
            nodes=[
                NodeData(
                    id="test/node",
                    instance_id="node_001",
                    name="测试节点",
                    position=NodePosition(x=100, y=200),
                    param_values={"key": "value"},
                ),
            ],
        )

        # 保存
        file_path = tmp_path / "integration_test.itproj"
        ProjectSerializer.save(project, file_path)

        # 验证文件存在
        assert file_path.exists()

        # 加载
        loaded = ProjectSerializer.load(file_path)

        # 验证数据
        assert loaded.metadata.name == "文件测试"
        assert len(loaded.nodes) == 1
        assert loaded.nodes[0].id == "test/node"
        assert loaded.nodes[0].param_values["key"] == "value"


class TestHealthCheckIntegration:
    """健康检查集成测试"""

    def test_health_checker_detects_issues(self):
        """测试健康检查器能检测问题"""
        from core.diagnostic.health_check import HealthChecker, CheckResult, CheckStatus

        checker = HealthChecker()

        # 添加一个会通过的检查
        checker.add("test_pass", lambda: CheckResult(
            "test_pass", CheckStatus.PASS
        ))

        # 添加一个会失败的检查
        checker.add("test_fail", lambda: CheckResult(
            "test_fail", CheckStatus.FAIL, "测试失败"
        ))

        # 运行检查
        report = checker.run()

        # 验证
        assert not report.is_healthy
        assert report.pass_count == 1
        assert report.fail_count == 1
        assert len(report.failures) == 1
        assert report.failures[0].name == "test_fail"

    def test_health_checker_detects_unbound_system(self, tmp_path):
        """测试健康检查器检测未绑定的系统"""
        from core.diagnostic.health_check import (
            HealthChecker, CheckResult, CheckStatus, check_project_system_wired
        )

        system = ProjectSystem(tmp_path)

        checker = HealthChecker()
        checker.add("ProjectSystem.wired", lambda: check_project_system_wired(system))

        report = checker.run()

        # 未绑定时应该失败
        assert not report.is_healthy
        assert report.fail_count == 1

    def test_health_checker_passes_after_wiring(self, tmp_path):
        """测试绑定后健康检查通过"""
        from core.diagnostic.health_check import (
            HealthChecker, check_project_system_wired
        )

        system = ProjectSystem(tmp_path)
        graph = MockNodeGraph()
        system.wire(lambda: graph)

        checker = HealthChecker()
        checker.add("ProjectSystem.wired", lambda: check_project_system_wired(system))

        report = checker.run()

        # 绑定后应该通过
        assert report.is_healthy
        assert report.pass_count == 1


class TestContractCheckIntegration:
    """契约检查集成测试"""

    def test_contract_checker_detects_missing_methods(self):
        """测试契约检查器检测缺失的方法"""
        from abc import abstractmethod, ABC
        from core.diagnostic.contract_check import ContractChecker

        class IMyInterface(ABC):
            @abstractmethod
            def required_method(self):
                pass

        class IncompleteImpl:
            pass  # 没有实现 required_method

        violations = ContractChecker.check(IncompleteImpl, IMyInterface)
        assert len(violations) == 1
        assert violations[0].violation_type == "missing_method"
        assert violations[0].name == "required_method"

    def test_contract_checker_passes_complete_implementation(self):
        """测试契约检查器通过完整实现"""
        from abc import abstractmethod, ABC
        from core.diagnostic.contract_check import ContractChecker

        class IMyInterface(ABC):
            @abstractmethod
            def required_method(self):
                pass

        class CompleteImpl(IMyInterface):
            def required_method(self):
                return "implemented"

        violations = ContractChecker.check(CompleteImpl, IMyInterface)
        assert len(violations) == 0

    def test_contract_checker_ignores_private_methods(self):
        """测试契约检查器忽略私有方法"""
        from abc import abstractmethod, ABC
        from core.diagnostic.contract_check import ContractChecker

        class IMyInterface(ABC):
            @abstractmethod
            def public_method(self):
                pass

        class Impl:
            def public_method(self):
                pass
            # 没有 _private_method，但这是允许的

        violations = ContractChecker.check(Impl, IMyInterface)
        assert len(violations) == 0
