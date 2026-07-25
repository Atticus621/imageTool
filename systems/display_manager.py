"""DisplayWindowManager — manages custom display window definitions and node-to-display associations."""

from __future__ import annotations

import uuid

from core.logger import logger


class DisplayWindowManager:
    """管理自定义显示窗口定义和节点-显示关联。

    每个自定义显示窗口有一个唯一 ID 和用户定义的名称。
    节点通过节点名称（instance name）关联到显示窗口。

    注意：本类管理的是"显示窗口"（哪个节点输出到哪个窗口），
    而 ImageDisplaySystem 管理的是"图像渲染"（像素 → 屏幕）。
    """

    def __init__(self):
        self._displays: dict[str, str] = {}  # display_id -> display_name
        self._node_displays: dict[str, str] = {}  # node_name -> display_id

    def create_display(self, name: str, display_id: str | None = None) -> str:
        """创建新的自定义显示。

        Args:
            name: 显示名称。
            display_id: 可选的显示 ID，不提供则自动生成。

        Returns:
            新建的显示 ID。
        """
        if display_id is None:
            display_id = f"display_{uuid.uuid4().hex[:8]}"

        # 检查名称是否重复
        for did, dname in self._displays.items():
            if dname == name and did != display_id:
                logger.warning(f"Display name already exists: {name}")
                raise ValueError(f"显示名称已存在: {name}")

        self._displays[display_id] = name
        logger.info(f"Created display: {name} ({display_id})")
        return display_id

    def delete_display(self, display_id: str) -> None:
        """删除自定义显示及其所有节点关联。"""
        if display_id not in self._displays:
            return

        name = self._displays.pop(display_id)
        # 移除关联到此显示的所有节点
        to_remove = [n for n, d in self._node_displays.items() if d == display_id]
        for n in to_remove:
            del self._node_displays[n]

        logger.info(f"Deleted display: {name} ({display_id}), removed {len(to_remove)} node associations")

    def rename_display(self, display_id: str, new_name: str) -> None:
        """重命名自定义显示。"""
        if display_id not in self._displays:
            return

        # 检查名称是否重复
        for did, dname in self._displays.items():
            if dname == new_name and did != display_id:
                raise ValueError(f"显示名称已存在: {new_name}")

        old_name = self._displays[display_id]
        self._displays[display_id] = new_name
        logger.info(f"Renamed display: {old_name} -> {new_name}")

    def get_displays(self) -> dict[str, str]:
        """返回所有自定义显示 {display_id: display_name}。"""
        return dict(self._displays)

    def get_display_name(self, display_id: str) -> str | None:
        """获取显示名称。"""
        return self._displays.get(display_id)

    def add_node_to_display(self, node_name: str, display_id: str) -> None:
        """将节点关联到显示。一个节点只能关联到一个显示。"""
        if display_id not in self._displays:
            logger.warning(f"Display not found: {display_id}")
            return

        old_display = self._node_displays.get(node_name)
        if old_display:
            logger.info(f"Node {node_name} moved from display {old_display} to {display_id}")

        self._node_displays[node_name] = display_id
        logger.info(f"Added node '{node_name}' to display '{self._displays[display_id]}'")

    def remove_node_from_display(self, node_name: str) -> None:
        """取消节点的显示关联。"""
        if node_name in self._node_displays:
            display_id = self._node_displays.pop(node_name)
            logger.info(f"Removed node '{node_name}' from display '{self._displays.get(display_id, display_id)}'")

    def get_node_display(self, node_name: str) -> str | None:
        """获取节点关联的显示 ID。"""
        return self._node_displays.get(node_name)

    def get_nodes_for_display(self, display_id: str) -> list[str]:
        """获取关联到指定显示的所有节点名称。"""
        return [n for n, d in self._node_displays.items() if d == display_id]

    def to_dict(self) -> dict:
        """序列化为字典（用于项目持久化）。"""
        return {
            "displays": dict(self._displays),
            "node_displays": dict(self._node_displays),
        }

    @classmethod
    def from_dict(cls, data: dict) -> DisplayWindowManager:
        """从字典反序列化。"""
        manager = cls()
        manager._displays = dict(data.get("displays", {}))
        manager._node_displays = dict(data.get("node_displays", {}))
        return manager
