"""ContractCheck — 接口契约检查器。

验证类是否正确实现了接口定义的方法和属性，
在运行时尽早发现接口实现缺失。
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import Any, get_type_hints

from core.logger import logger


@dataclass
class ContractViolation:
    """契约违反"""
    interface: str
    implementor: str
    violation_type: str  # "missing_method", "missing_attr", "type_mismatch"
    name: str
    message: str


class ContractChecker:
    """接口契约检查器。

    检查类是否实现了接口定义的所有抽象方法和属性。

    使用方式：
        violations = ContractChecker.check(MyClass, IMyInterface)
        if violations:
            for v in violations:
                logger.error(f"Contract violation: {v.message}")
    """

    @staticmethod
    def check(
        implementor: type,
        interface: type,
    ) -> list[ContractViolation]:
        """检查实现类是否满足接口契约。

        Args:
            implementor: 实现类
            interface: 接口类（ABC）

        Returns:
            违反列表，空表示完全满足
        """
        violations = []
        interface_name = interface.__name__
        implementor_name = implementor.__name__

        # 检查抽象方法
        for name in dir(interface):
            if name.startswith("_"):
                continue

            attr = getattr(interface, name, None)
            if attr is None:
                continue

            # 检查是否为抽象方法
            if getattr(attr, "__isabstractmethod__", False):
                impl_attr = getattr(implementor, name, None)
                if impl_attr is None:
                    violations.append(ContractViolation(
                        interface=interface_name,
                        implementor=implementor_name,
                        violation_type="missing_method",
                        name=name,
                        message=f"{implementor_name} 缺少接口方法 {interface_name}.{name}",
                    ))
                elif not callable(impl_attr):
                    violations.append(ContractViolation(
                        interface=interface_name,
                        implementor=implementor_name,
                        violation_type="type_mismatch",
                        name=name,
                        message=f"{implementor_name}.{name} 应该是可调用的",
                    ))

        return violations

    @staticmethod
    def check_instance(
        instance: object,
        interface: type,
    ) -> list[ContractViolation]:
        """检查实例是否满足接口契约。

        Args:
            instance: 实例对象
            interface: 接口类（ABC）

        Returns:
            违反列表
        """
        return ContractChecker.check(type(instance), interface)

    @staticmethod
    def check_all_systems(registry, interfaces_map: dict[str, type]) -> list[ContractViolation]:
        """检查注册表中所有系统的接口契约。

        Args:
            registry: SystemRegistry 实例
            interfaces_map: {系统名: 接口类} 映射

        Returns:
            所有违反的列表
        """
        all_violations = []

        for system_name, interface in interfaces_map.items():
            try:
                system = registry.get(system_name)
                violations = ContractChecker.check_instance(system, interface)
                all_violations.extend(violations)
            except KeyError:
                all_violations.append(ContractViolation(
                    interface=interface.__name__,
                    implementor=system_name,
                    violation_type="missing_system",
                    name=system_name,
                    message=f"系统 {system_name} 未注册",
                ))

        return all_violations


class WiringChecker:
    """系统绑定检查器。

    检查系统的关键属性是否已正确绑定（DI 完整性）。
    """

    @staticmethod
    def check_binding(
        system_name: str,
        obj: object,
        required_bindings: dict[str, str],
    ) -> list[str]:
        """检查对象的绑定状态。

        Args:
            system_name: 系统名称
            obj: 系统实例
            required_bindings: {属性名: 描述} 映射

        Returns:
            未绑定的属性描述列表
        """
        missing = []
        for attr_name, description in required_bindings.items():
            attr = getattr(obj, attr_name, None)
            if attr is None:
                missing.append(f"{system_name}.{attr_name}: {description}")
            elif callable(attr) and not callable(attr):
                # 检查是否应该是可调用的
                missing.append(f"{system_name}.{attr_name}: {description} (不可调用)")
        return missing

    @staticmethod
    def check_system_wiring(systems: dict[str, tuple[object, dict[str, str]]]) -> list[str]:
        """批量检查多个系统的绑定状态。

        Args:
            systems: {系统名: (实例, {属性名: 描述})} 映射

        Returns:
            所有未绑定的描述列表
        """
        all_missing = []
        for system_name, (obj, bindings) in systems.items():
            missing = WiringChecker.check_binding(system_name, obj, bindings)
            all_missing.extend(missing)
        return all_missing


def auto_check_interfaces(module_globals: dict) -> list[ContractViolation]:
    """自动检查模块中所有类的接口实现。

    扫描模块中所有类，检查它们是否正确实现了继承的 ABC 接口。

    Args:
        module_globals: 模块的 globals()

    Returns:
        所有违反的列表
    """
    violations = []

    for name, obj in module_globals.items():
        if not isinstance(obj, type):
            continue

        # 检查所有基类
        for base in obj.__mro__[1:]:
            if base is ABC or not getattr(base, "__abstractmethods__", None):
                continue

            base_violations = ContractChecker.check(obj, base)
            violations.extend(base_violations)

    return violations
