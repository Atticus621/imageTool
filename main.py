import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

os.environ["QT_API"] = "pyside6"

from core.logger import logger
from core.config import config
from core.plugin.scanner import PluginScanner
from core.node_base.registry import node_registry
from core.system.manager import SystemManager
from systems.registry import SystemRegistry
from systems.image_display.system import ImageDisplaySystem
from systems.blueprint.system import BlueprintSystem


def apply_theme(app):
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
        import re
        css = custom_css_path.read_text(encoding="utf-8")
        env_vars = {k: v for k, v in os.environ.items() if k.startswith("QTMATERIAL_")}
        for key, val in env_vars.items():
            css = css.replace("{" + key + "}", val)
        app.setStyleSheet(app.styleSheet() + css)
        logger.info(f"Applied custom CSS: {custom_css_path}")


def main():
    from PySide6.QtWidgets import QApplication
    from ui.widgets.splash import SplashScreen

    app = QApplication(sys.argv)
    app.setApplicationName("ImageTools")
    app.setApplicationVersion("0.1.0")

    splash = SplashScreen()
    splash.show()

    manager = SystemManager()
    manager.add_task("加载配置", lambda: _load_config())
    manager.add_task("加载节点树", lambda: _load_node_tree())
    manager.add_task("扫描插件", lambda: _scan_plugins())

    # Create system registry and register domain systems
    registry = SystemRegistry()
    registry.register(ImageDisplaySystem(), depends_on=[])
    registry.register(BlueprintSystem(), depends_on=[])

    manager.add_task("初始化系统", lambda: registry.initialize_all())
    manager.add_task("应用主题", lambda: apply_theme(app))
    manager.add_task("创建界面", lambda: _create_window(app, splash, registry))
    manager.add_task("启动网络服务", lambda: _start_network())
    manager.run(splash)

    logger.info("Application started")
    exit_code = app.exec()

    # Shutdown systems in reverse order
    registry.shutdown_all()
    logger.info(f"Application exited with code {exit_code}")
    sys.exit(exit_code)


def _load_config():
    config_path = ROOT_DIR / "config" / "app.yaml"
    config.load(config_path)
    config.load_dir(ROOT_DIR / "config" / "ui")


def _scan_plugins():
    scanner = PluginScanner(ROOT_DIR / "nodes")
    scanner.scan()


def _load_node_tree():
    node_registry.load_tree_config(ROOT_DIR / "config" / "nodes.yaml")


_window = None


def _create_window(app, splash, registry: SystemRegistry):
    global _window
    from ui.main_window import MainWindow

    _window = MainWindow(
        image_display=registry.get("ImageDisplay"),
        blueprint=registry.get("Blueprint"),
    )
    _window.show()
    splash.finish(_window)


def _start_network():
    from core.network.server import NetworkServer
    server = NetworkServer(
        host=config.get("network.host", "127.0.0.1"),
        port=config.get("network.port", 8765),
    )
    server.start()


if __name__ == "__main__":
    main()
