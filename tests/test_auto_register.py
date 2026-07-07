"""测试自动注册和发现系统"""

import pytest
from pathlib import Path

from core.system.auto_register import (
    register_system,
    get_all_registrations,
    get_registration,
    get_system_names,
    get_sorted_by_dependencies,
    get_wire_order,
    clear_registry,
    MenuItem,
    ToolbarItem,
    SystemRegistration,
)
from systems.base import ISystem


class TestAutoRegister:
    """测试自动注册装饰器"""

    def setup_method(self):
        """每个测试前清空注册表"""
        clear_registry()

    def test_register_system_decorator(self):
        """测试装饰器注册系统"""

        @register_system(name="TestSystem", depends_on=[])
        class TestSystem(ISystem):
            @property
            def name(self):
                return "TestSystem"

            def initialize(self):
                return True

            def shutdown(self):
                pass

        # 验证注册
        assert "TestSystem" in get_system_names()
        reg = get_registration("TestSystem")
        assert reg is not None
        assert reg.name == "TestSystem"
        assert reg.system_class == TestSystem

    def test_register_with_dependencies(self):
        """测试带依赖的注册"""

        @register_system(name="Base", depends_on=[])
        class BaseSystem(ISystem):
            @property
            def name(self):
                return "Base"

            def initialize(self):
                return True

            def shutdown(self):
                pass

        @register_system(name="Dependent", depends_on=["Base"])
        class DependentSystem(ISystem):
            @property
            def name(self):
                return "Dependent"

            def initialize(self):
                return True

            def shutdown(self):
                pass

        # 验证依赖
        reg = get_registration("Dependent")
        assert "Base" in reg.depends_on

    def test_register_with_menu_items(self):
        """测试带菜单项的注册"""

        @register_system(
            name="MenuSystem",
            depends_on=[],
            menu_items=[
                {"text": "保存", "method": "_on_save", "shortcut": "Ctrl+S"},
                {"text": "打开", "method": "_on_open"},
            ],
        )
        class MenuSystem(ISystem):
            @property
            def name(self):
                return "MenuSystem"

            def initialize(self):
                return True

            def shutdown(self):
                pass

        # 验证菜单项
        reg = get_registration("MenuSystem")
        assert len(reg.menu_items) == 2
        assert reg.menu_items[0].text == "保存"
        assert reg.menu_items[0].shortcut == "Ctrl+S"

    def test_register_with_toolbar_items(self):
        """测试带工具栏项的注册"""

        @register_system(
            name="ToolbarSystem",
            depends_on=[],
            toolbar_items=[
                {"text": "💾 保存", "method": "_on_save"},
            ],
        )
        class ToolbarSystem(ISystem):
            @property
            def name(self):
                return "ToolbarSystem"

            def initialize(self):
                return True

            def shutdown(self):
                pass

        # 验证工具栏项
        reg = get_registration("ToolbarSystem")
        assert len(reg.toolbar_items) == 1
        assert reg.toolbar_items[0].text == "💾 保存"

    def test_sorted_by_dependencies(self):
        """测试依赖排序"""

        @register_system(name="C", depends_on=["B"])
        class CSystem(ISystem):
            @property
            def name(self):
                return "C"

            def initialize(self):
                return True

            def shutdown(self):
                pass

        @register_system(name="A", depends_on=[])
        class ASystem(ISystem):
            @property
            def name(self):
                return "A"

            def initialize(self):
                return True

            def shutdown(self):
                pass

        @register_system(name="B", depends_on=["A"])
        class BSystem(ISystem):
            @property
            def name(self):
                return "B"

            def initialize(self):
                return True

            def shutdown(self):
                pass

        # 验证排序
        order = get_sorted_by_dependencies()
        assert order.index("A") < order.index("B")
        assert order.index("B") < order.index("C")

    def test_factory_creates_instance(self):
        """测试工厂函数创建实例"""

        @register_system(name="FactoryTest", depends_on=[])
        class FactoryTestSystem(ISystem):
            @property
            def name(self):
                return "FactoryTest"

            def initialize(self):
                return True

            def shutdown(self):
                pass

        # 创建实例
        reg = get_registration("FactoryTest")
        instance = reg.factory()
        assert isinstance(instance, FactoryTestSystem)

    def test_clear_registry(self):
        """测试清空注册表"""

        @register_system(name="Temp", depends_on=[])
        class TempSystem(ISystem):
            @property
            def name(self):
                return "Temp"

            def initialize(self):
                return True

            def shutdown(self):
                pass

        assert "Temp" in get_system_names()
        clear_registry()
        assert "Temp" not in get_system_names()

    def test_circular_dependency_detection(self):
        """测试循环依赖检测"""

        @register_system(name="X", depends_on=["Y"])
        class XSystem(ISystem):
            @property
            def name(self):
                return "X"

            def initialize(self):
                return True

            def shutdown(self):
                pass

        @register_system(name="Y", depends_on=["X"])
        class YSystem(ISystem):
            @property
            def name(self):
                return "Y"

            def initialize(self):
                return True

            def shutdown(self):
                pass

        # 应该抛出异常
        with pytest.raises(RuntimeError, match="Circular dependency"):
            get_sorted_by_dependencies()


class TestMenuItem:
    """测试 MenuItem 数据类"""

    def test_create_menu_item(self):
        """测试创建菜单项"""
        item = MenuItem(text="保存", method="_on_save", shortcut="Ctrl+S")
        assert item.text == "保存"
        assert item.method == "_on_save"
        assert item.shortcut == "Ctrl+S"
        assert item.separator_before is False

    def test_create_with_separator(self):
        """测试带分隔符的菜单项"""
        item = MenuItem(text="打开", method="_on_open", separator_before=True)
        assert item.separator_before is True


class TestToolbarItem:
    """测试 ToolbarItem 数据类"""

    def test_create_toolbar_item(self):
        """测试创建工具栏项"""
        item = ToolbarItem(text="💾 保存", method="_on_save")
        assert item.text == "💾 保存"
        assert item.method == "_on_save"
        assert item.separator_before is False


class TestSystemRegistration:
    """测试 SystemRegistration 数据类"""

    def test_create_registration(self):
        """测试创建注册信息"""

        class TestSystem(ISystem):
            @property
            def name(self):
                return "Test"

            def initialize(self):
                return True

            def shutdown(self):
                pass

        reg = SystemRegistration(
            name="Test",
            system_class=TestSystem,
            factory=lambda: TestSystem(),
            depends_on=["Base"],
        )

        assert reg.name == "Test"
        assert reg.system_class == TestSystem
        assert "Base" in reg.depends_on
        assert reg.auto_wire is True  # 默认值

    def test_default_values(self):
        """测试默认值"""
        reg = SystemRegistration(
            name="Test",
            system_class=type,
            factory=lambda: None,
        )

        assert reg.depends_on == []
        assert reg.bindings == {}
        assert reg.menu_items == []
        assert reg.toolbar_items == []
        assert reg.auto_wire is True
        assert reg.wire_after == []
