"""AutoRegister — 系统自动注册和绑定框架。

系统通过装饰器声明自己的依赖和绑定需求，
框架自动完成注册、依赖排序、绑定和健康检查。

目标：添加新系统只需修改系统本身，无需修改 main.py 或 MainWindow。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Any

from core.logger import logger


@dataclass
class MenuItem:
    """菜单项定义"""
    text: str
    method: str  # 系统方法名
    shortcut: str = ""
    separator_before: bool = False
    separator_after: bool = False


@dataclass
class ToolbarItem:
    """工具栏项定义"""
    text: str
    method: str  # 系统方法名
    separator_before: bool = False
    separator_after: bool = False


@dataclass
class SystemRegistration:
    """系统注册信息"""
    name: str
    system_class: type
    factory: Callable[[], Any]  # 创建系统实例的工厂函数
    depends_on: list[str] = field(default_factory=list)
    bindings: dict[str, str] = field(default_factory=dict)  # {属性名: 依赖系统名}
    menu_items: list[MenuItem] = field(default_factory=list)
    toolbar_items: list[ToolbarItem] = field(default_factory=list)
    auto_wire: bool = True  # 是否自动绑定
    wire_after: list[str] = field(default_factory=list)  # 在哪些系统之后绑定


# 全局注册表
_system_registry: dict[str, SystemRegistration] = {}


def register_system(
    name: str,
    depends_on: list[str] = None,
    bindings: dict[str, str] = None,
    menu_items: list[dict] = None,
    toolbar_items: list[dict] = None,
    auto_wire: bool = True,
    wire_after: list[str] = None,
    factory_args: tuple = None,
    factory_kwargs: dict = None,
):
    """系统注册装饰器。

    使用方式：
        @register_system(
            name="Project",
            depends_on=["Blueprint"],
            bindings={"_graph_getter": "Blueprint"},
            menu_items=[
                {"text": "保存", "shortcut": "Ctrl+S", "method": "_on_save"},
            ],
            toolbar_items=[
                {"text": "💾 保存", "method": "_on_save"},
            ],
            factory_kwargs={"root_dir": ROOT_DIR},
        )
        class ProjectSystem(ISystem):
            ...

    Args:
        name: 系统名称
        depends_on: 依赖的系统列表
        bindings: 需要从其他系统获取的属性 {本地属性: 依赖系统名}
        menu_items: 要添加到菜单的项
        toolbar_items: 要添加到工具栏的项
        auto_wire: 是否在 MainWindow 中自动绑定
        wire_after: 在哪些系统绑定之后再绑定此系统
        factory_args: 传递给工厂函数的位置参数
        factory_kwargs: 传递给工厂函数的关键字参数
    """
    def decorator(cls):
        # 创建工厂函数
        _args = factory_args or ()
        _kwargs = factory_kwargs or {}

        def factory():
            return cls(*_args, **_kwargs)

        # 解析菜单项
        parsed_menu = []
        for item in (menu_items or []):
            parsed_menu.append(MenuItem(
                text=item.get("text", ""),
                method=item.get("method", ""),
                shortcut=item.get("shortcut", ""),
                separator_before=item.get("separator_before", False),
                separator_after=item.get("separator_after", False),
            ))

        # 解析工具栏项
        parsed_toolbar = []
        for item in (toolbar_items or []):
            parsed_toolbar.append(ToolbarItem(
                text=item.get("text", ""),
                method=item.get("method", ""),
                separator_before=item.get("separator_before", False),
                separator_after=item.get("separator_after", False),
            ))

        registration = SystemRegistration(
            name=name,
            system_class=cls,
            factory=factory,
            depends_on=depends_on or [],
            bindings=bindings or {},
            menu_items=parsed_menu,
            toolbar_items=parsed_toolbar,
            auto_wire=auto_wire,
            wire_after=wire_after or [],
        )

        _system_registry[name] = registration
        logger.info(f"[AutoRegister] Registered system: {name}")

        # 保存注册信息到类（便于调试）
        cls._system_registration = registration

        return cls
    return decorator


def get_all_registrations() -> dict[str, SystemRegistration]:
    """获取所有注册的系统"""
    return dict(_system_registry)


def get_registration(name: str) -> SystemRegistration | None:
    """获取指定系统的注册信息"""
    return _system_registry.get(name)


def get_system_names() -> list[str]:
    """获取所有注册的系统名称"""
    return list(_system_registry.keys())


def get_sorted_by_dependencies() -> list[str]:
    """按依赖顺序返回系统名称（拓扑排序）"""
    # Kahn's algorithm
    in_degree = {name: 0 for name in _system_registry}
    graph: dict[str, list[str]] = {}

    for name, reg in _system_registry.items():
        graph.setdefault(name, [])
        for dep in reg.depends_on:
            graph.setdefault(dep, []).append(name)
            in_degree[name] += 1

    queue = [n for n, d in in_degree.items() if d == 0]
    result = []

    while queue:
        node = queue.pop(0)
        result.append(node)
        for neighbor in graph.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(result) != len(_system_registry):
        remaining = set(_system_registry) - set(result)
        raise RuntimeError(f"Circular dependency among systems: {remaining}")

    return result


def get_wire_order() -> list[str]:
    """获取绑定顺序（考虑 wire_after 依赖）"""
    # 先按依赖排序
    base_order = get_sorted_by_dependencies()

    # 然后考虑 wire_after
    # 这是一个简化的实现，确保 wire_after 的系统在后面
    wire_after_map: dict[str, set[str]] = {}
    for name, reg in _system_registry.items():
        if reg.wire_after:
            wire_after_map[name] = set(reg.wire_after)

    if not wire_after_map:
        return base_order

    # 拓扑排序考虑 wire_after
    in_degree = {name: 0 for name in base_order}
    graph: dict[str, list[str]] = {name: [] for name in base_order}

    for name, deps in wire_after_map.items():
        for dep in deps:
            if dep in graph:
                graph[dep].append(name)
                in_degree[name] += 1

    queue = [n for n, d in in_degree.items() if d == 0]
    result = []

    while queue:
        node = queue.pop(0)
        result.append(node)
        for neighbor in graph.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return result


def clear_registry():
    """清空注册表（用于测试）"""
    _system_registry.clear()
