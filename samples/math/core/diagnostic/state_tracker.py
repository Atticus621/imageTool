"""StateTracker — 组件状态快照系统。

组件注册自己的状态提供函数，诊断 API 可以随时查询所有组件的当前状态。

使用方式：
    # 注册状态提供者
    StateTracker.register("ruler", lambda: {
        "enabled": True,
        "measurements": len(self._image_measurements),
        "drawing": self._guard.is_drawing,
    })

    # 查询状态
    state = StateTracker.snapshot()  # 所有组件
    state = StateTracker.get("ruler")  # 单个组件
"""

from __future__ import annotations

import time
from typing import Callable

from core.logger import logger


class StateTracker:
    """组件状态快照系统。"""

    _providers: dict[str, Callable[[], dict]] = {}

    @classmethod
    def register(cls, name: str, state_fn: Callable[[], dict]) -> None:
        """注册状态提供者。

        Args:
            name: 组件名称（如 "ruler", "coordinate_mapper"）
            state_fn: 返回状态字典的函数
        """
        cls._providers[name] = state_fn
        logger.debug(f"[StateTracker] Registered: {name}")

    @classmethod
    def unregister(cls, name: str) -> None:
        """取消注册状态提供者。"""
        cls._providers.pop(name, None)

    @classmethod
    def snapshot(cls) -> dict:
        """获取所有组件的状态快照。

        Returns:
            {component_name: state_dict, ...}
        """
        result = {"timestamp": time.time()}
        for name, fn in cls._providers.items():
            try:
                result[name] = fn()
            except Exception as e:
                result[name] = {"error": str(e)}
        return result

    @classmethod
    def get(cls, name: str) -> dict | None:
        """获取单个组件的状态。

        Args:
            name: 组件名称

        Returns:
            状态字典，或 None（未注册时）
        """
        fn = cls._providers.get(name)
        if fn:
            try:
                return fn()
            except Exception as e:
                return {"error": str(e)}
        return None

    @classmethod
    def list_components(cls) -> list[str]:
        """列出所有已注册的组件名。"""
        return list(cls._providers.keys())
