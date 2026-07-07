import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

os.environ["QT_API"] = "pyside6"

# ── QApplication + SplashScreen FIRST — before even the logger ──────
# This ensures the user sees the splash window immediately on launch,
# before any module loading or logging setup.
from PySide6.QtWidgets import QApplication

_app = QApplication(sys.argv)
_app.setApplicationName("ImageTools")
_app.setApplicationVersion("0.1.0")

from ui.widgets.splash import SplashScreen

_splash = SplashScreen()
_splash.show()
_app.processEvents()  # force splash to render before heavy imports

# ── Now initialize logger (splash is already visible) ───────────────
from core.logger import logger


def _run_health_check(registry, window, logger):
    """启动后运行健康检查，验证系统绑定完整性。"""
    from core.diagnostic.health_check import (
        HealthChecker,
        CheckResult,
        CheckStatus,
        check_project_system_wired,
    )

    checker = HealthChecker()

    # 检查 ProjectSystem 绑定
    try:
        project_system = registry.get("Project")
        checker.add(
            "ProjectSystem.wired",
            lambda: check_project_system_wired(project_system),
        )
    except KeyError:
        checker.add("ProjectSystem.registered", lambda: CheckResult(
            "ProjectSystem.registered", CheckStatus.FAIL, "ProjectSystem 未注册"
        ))

    # 检查 BlueprintSystem 绑定
    try:
        blueprint_system = registry.get("Blueprint")
        checker.add("BlueprintSystem.graph_getter", lambda: CheckResult(
            "BlueprintSystem.graph_getter",
            CheckStatus.PASS if blueprint_system._graph_getter else CheckStatus.FAIL,
            "" if blueprint_system._graph_getter else "graph_getter 未绑定",
        ))
    except KeyError:
        checker.add("BlueprintSystem.registered", lambda: CheckResult(
            "BlueprintSystem.registered", CheckStatus.FAIL, "BlueprintSystem 未注册"
        ))

    # 检查 MainWindow 存在
    checker.add("MainWindow.created", lambda: CheckResult(
        "MainWindow.created",
        CheckStatus.PASS if window is not None else CheckStatus.FAIL,
        "" if window is not None else "MainWindow 未创建",
    ))

    # 运行检查
    report = checker.run()

    if not report.is_healthy:
        logger.warning(f"[Startup] 健康检查发现问题: {report.summary()}")
        for failure in report.failures:
            logger.error(f"[Startup] ✗ {failure.name}: {failure.message}")
    else:
        logger.info(f"[Startup] 健康检查通过 ({report.pass_count} 项)")


def _apply_theme(app, config):
    """应用主题"""
    from qt_material import apply_stylesheet
    theme = config.get("ui.theme", "dark_teal.xml")
    extra = {
        'danger': config.get("ui.extra.danger", "#dc3545"),
        'warning': config.get("ui.extra.warning", "#f7ff07"),
        'success': config.get("ui.extra.success", "#28a745"),
        'font_family': config.get("ui.extra.font_family", "Segoe UI"),
        'font_size': config.get("ui.extra.font_size", "13px"),
        'density_scale': config.get("ui.extra.density_scale", "0"),
    }
    apply_stylesheet(app, theme=theme, extra=extra)
    logger.info(f"Applied theme: {theme}")
    custom_css_path = ROOT_DIR / "config" / "ui" / "custom.css"
    if custom_css_path.exists():
        css = custom_css_path.read_text(encoding="utf-8")
        env_vars = {k: v for k, v in os.environ.items() if k.startswith("QTMATERIAL_")}
        for key, val in env_vars.items():
            css = css.replace("{" + key + "}", val)
        app.setStyleSheet(app.styleSheet() + css)
        logger.info(f"Applied custom CSS: {custom_css_path}")


def main():
    """主入口 - 使用自动发现和注册"""
    # ── Heavy imports (while splash is visible) ───────────────────────
    from core.config import config
    from core.plugin.scanner import PluginScanner
    from core.node_base.registry import node_registry
    from core.system.manager import SystemManager
    from core.system.scanner import scan_systems
    from core.system.auto_register import get_sorted_by_dependencies, get_registration
    from systems.registry import SystemRegistry

    # ── Task closures ─────────────────────────────────────────────────
    def _load_config():
        config_path = ROOT_DIR / "config" / "app.yaml"
        config.load(config_path)
        config.load_dir(ROOT_DIR / "config" / "ui")

    def _scan_plugins():
        scanner = PluginScanner(ROOT_DIR / "nodes")
        scanner.scan()

    def _scan_systems():
        """扫描并注册所有系统"""
        scan_systems(ROOT_DIR)

    def _load_node_tree():
        node_registry.load_tree_config(ROOT_DIR / "config" / "nodes.yaml")

    _window = None

    def _create_window(splash, registry):
        nonlocal _window
        from ui.main_window import MainWindow
        # 使用 from_registry 创建窗口（自动模式）
        _window = MainWindow.from_registry(registry)
        _window.show()
        splash.finish(_window)

    def _start_network():
        from core.network.server import NetworkServer
        server = NetworkServer(
            host=config.get("network.host", "127.0.0.1"),
            port=config.get("network.port", 8765),
        )
        server.start()

    def _register_systems():
        """从自动注册表注册系统到 SystemRegistry"""
        from pathlib import Path
        for name in get_sorted_by_dependencies():
            reg = get_registration(name)
            if reg:
                # 创建系统实例
                system = reg.factory()
                registry.register(system, depends_on=reg.depends_on)
                logger.info(f"[Main] Registered system: {name}")

    # ── Run startup tasks ─────────────────────────────────────────────
    manager = SystemManager()
    manager.add_task("加载配置", lambda: _load_config())
    manager.add_task("加载节点树", lambda: _load_node_tree())
    manager.add_task("扫描插件", lambda: _scan_plugins())
    manager.add_task("扫描系统", lambda: _scan_systems())

    registry = SystemRegistry()

    manager.add_task("注册系统", lambda: _register_systems())
    manager.add_task("初始化系统", lambda: registry.initialize_all())
    manager.add_task("应用主题", lambda: _apply_theme(_app, config))
    manager.add_task("创建界面", lambda: _create_window(_splash, registry))
    manager.add_task("启动网络服务", lambda: _start_network())
    manager.run(_splash)

    # ── Health check after startup ──────────────────────────────────
    _run_health_check(registry, _window, logger)

    logger.info("Application started")
    exit_code = _app.exec()

    # Shutdown systems in reverse order
    registry.shutdown_all()
    logger.info(f"Application exited with code {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
