"""HealthCheck — 系统健康检查框架。

启动时验证所有系统已正确初始化和绑定，尽早发现配置错误。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from core.logger import logger


class CheckStatus(str, Enum):
    """检查状态"""
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class CheckResult:
    """单项检查结果"""
    name: str
    status: CheckStatus
    message: str = ""
    details: dict = field(default_factory=dict)

    @property
    def is_ok(self) -> bool:
        return self.status in (CheckStatus.PASS, CheckStatus.WARN, CheckStatus.SKIP)


@dataclass
class HealthReport:
    """健康检查报告"""
    checks: list[CheckResult] = field(default_factory=list)
    timestamp: float = 0.0

    @property
    def is_healthy(self) -> bool:
        return all(c.is_ok for c in self.checks)

    @property
    def pass_count(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.PASS)

    @property
    def warn_count(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.WARN)

    @property
    def fail_count(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.FAIL)

    @property
    def failures(self) -> list[CheckResult]:
        return [c for c in self.checks if c.status == CheckStatus.FAIL]

    def summary(self) -> str:
        """返回可读的摘要"""
        if self.is_healthy:
            return f"健康检查通过 ({self.pass_count} 项)"
        fails = self.failures
        fail_names = ", ".join(c.name for c in fails)
        return f"健康检查失败: {fail_names}"

    def to_dict(self) -> dict:
        return {
            "healthy": self.is_healthy,
            "pass": self.pass_count,
            "warn": self.warn_count,
            "fail": self.fail_count,
            "checks": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "details": c.details,
                }
                for c in self.checks
            ],
        }


class HealthChecker:
    """健康检查器。

    注册检查项，运行时执行检查并生成报告。

    使用方式：
        checker = HealthChecker()
        checker.add("ProjectSystem.wired", lambda: (
            CheckResult("ProjectSystem.wired", CheckStatus.PASS)
            if project_system._graph_getter
            else CheckResult("ProjectSystem.wired", CheckStatus.FAIL, "graph_getter 未绑定")
        ))
        report = checker.run()
    """

    def __init__(self):
        self._checks: list[tuple[str, Callable[[], CheckResult]]] = []

    def add(self, name: str, check_fn: Callable[[], CheckResult]) -> None:
        """注册检查项。

        Args:
            name: 检查名称
            check_fn: 返回 CheckResult 的函数
        """
        self._checks.append((name, check_fn))

    def add_assertion(
        self, name: str, condition: bool, fail_msg: str, warn_msg: str = ""
    ) -> None:
        """注册简单断言检查。

        Args:
            name: 检查名称
            condition: 为 True 时通过
            fail_msg: 失败时的消息
            warn_msg: 警告时的消息（可选）
        """
        def check():
            if condition:
                return CheckResult(name, CheckStatus.PASS)
            elif warn_msg:
                return CheckResult(name, CheckStatus.WARN, warn_msg)
            else:
                return CheckResult(name, CheckStatus.FAIL, fail_msg)
        self._checks.append((name, check))

    def run(self) -> HealthReport:
        """执行所有检查。

        Returns:
            HealthReport 包含所有检查结果
        """
        import time
        report = HealthReport(timestamp=time.time())

        for name, check_fn in self._checks:
            try:
                result = check_fn()
                report.checks.append(result)

                if result.status == CheckStatus.PASS:
                    logger.debug(f"[HealthCheck] ✓ {name}")
                elif result.status == CheckStatus.WARN:
                    logger.warning(f"[HealthCheck] ⚠ {name}: {result.message}")
                elif result.status == CheckStatus.FAIL:
                    logger.error(f"[HealthCheck] ✗ {name}: {result.message}")
                else:
                    logger.debug(f"[HealthCheck] ○ {name}: skipped")

            except Exception as e:
                report.checks.append(CheckResult(
                    name, CheckStatus.FAIL, f"检查异常: {e}"
                ))
                logger.error(f"[HealthCheck] ✗ {name}: exception - {e}")

        # 输出摘要
        if report.is_healthy:
            logger.info(f"[HealthCheck] {report.summary()}")
        else:
            logger.error(f"[HealthCheck] {report.summary()}")

        return report

    def clear(self) -> None:
        """清除所有检查项"""
        self._checks.clear()


# ── 内置检查函数 ─────────────────────────────────────────────────────

def check_system_bound(system_name: str, attr_name: str, obj: object) -> CheckResult:
    """检查系统属性是否已绑定"""
    attr = getattr(obj, attr_name, None)
    if attr is not None:
        return CheckResult(
            f"{system_name}.{attr_name}",
            CheckStatus.PASS,
        )
    return CheckResult(
        f"{system_name}.{attr_name}",
        CheckStatus.FAIL,
        f"{system_name}.{attr_name} 未绑定",
    )


def check_callable_bound(system_name: str, attr_name: str, obj: object) -> CheckResult:
    """检查系统可调用属性是否已绑定"""
    attr = getattr(obj, attr_name, None)
    if callable(attr):
        return CheckResult(
            f"{system_name}.{attr_name}",
            CheckStatus.PASS,
        )
    return CheckResult(
        f"{system_name}.{attr_name}",
        CheckStatus.FAIL,
        f"{system_name}.{attr_name} 未绑定或不可调用",
    )


def check_graph_nodes(graph, expected_min: int = 0) -> CheckResult:
    """检查图中节点数量"""
    nodes = graph.all_nodes()
    count = len(nodes)
    if count >= expected_min:
        return CheckResult(
            "graph.nodes",
            CheckStatus.PASS,
            f"图中有 {count} 个节点",
            {"count": count},
        )
    return CheckResult(
        "graph.nodes",
        CheckStatus.WARN,
        f"图中节点数 ({count}) 小于预期 ({expected_min})",
        {"count": count, "expected": expected_min},
    )


def check_project_system_wired(project_system) -> CheckResult:
    """检查 ProjectSystem 是否已正确绑定"""
    if project_system._graph_getter is None:
        return CheckResult(
            "ProjectSystem.wired",
            CheckStatus.FAIL,
            "ProjectSystem._graph_getter 未绑定，调用 _wire_project_system()",
        )
    return CheckResult(
        "ProjectSystem.wired",
        CheckStatus.PASS,
    )
