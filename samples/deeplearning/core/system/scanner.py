"""SystemScanner — 系统自动发现和加载。

扫描 systems/ 目录，自动导入所有 system.py 文件，
触发装饰器注册。
"""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path

from core.logger import logger


class SystemScanner:
    """系统自动发现扫描器。

    扫描指定目录下的 system.py 文件，自动导入并触发注册。
    """

    def __init__(self, systems_dir: Path):
        """初始化扫描器。

        Args:
            systems_dir: systems/ 目录路径
        """
        self._systems_dir = systems_dir
        self._loaded_modules: dict[str, any] = {}

    def scan(self) -> dict[str, str]:
        """扫描并加载所有系统模块。

        Returns:
            {系统名: 模块路径} 映射
        """
        loaded = {}

        if not self._systems_dir.exists():
            logger.warning(f"[SystemScanner] Systems directory not found: {self._systems_dir}")
            return loaded

        # 扫描所有子目录中的 system.py
        for system_dir in self._systems_dir.iterdir():
            if not system_dir.is_dir():
                continue

            system_file = system_dir / "system.py"
            if not system_file.exists():
                continue

            # 跳过 __pycache__
            if system_dir.name.startswith("_"):
                continue

            module_name = f"systems.{system_dir.name}.system"

            try:
                # 检查是否已加载
                if module_name in self._loaded_modules:
                    logger.debug(f"[SystemScanner] Module already loaded: {module_name}")
                    continue

                # 导入模块
                module = importlib.import_module(module_name)
                self._loaded_modules[module_name] = module
                loaded[system_dir.name] = module_name

                logger.info(f"[SystemScanner] Loaded system module: {module_name}")

            except Exception as e:
                # 记录错误但不阻止启动
                logger.error(f"[SystemScanner] Failed to load {module_name}: {e}")

        logger.info(f"[SystemScanner] Scan complete: {len(loaded)} systems loaded")
        return loaded

    def get_loaded_modules(self) -> dict[str, any]:
        """获取已加载的模块"""
        return dict(self._loaded_modules)


def scan_systems(root_dir: Path) -> dict[str, str]:
    """便捷函数：扫描并加载所有系统。

    Args:
        root_dir: 项目根目录

    Returns:
        {系统名: 模块路径} 映射
    """
    systems_dir = root_dir / "systems"
    scanner = SystemScanner(systems_dir)
    return scanner.scan()
