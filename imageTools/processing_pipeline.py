# -*- coding: utf-8 -*-
"""图像处理流水线模块 —— 管理多个处理步骤的有序执行，支持文件夹分组。"""
import copy
import json
import numpy as np


class ProcessingStep:
    """单个处理步骤。"""

    def __init__(self, func_name: str, params: dict, enabled: bool = True):
        self.func_name = func_name
        self.params = params.copy()
        self.enabled = enabled

    def clone(self) -> 'ProcessingStep':
        """深拷贝自身。"""
        return ProcessingStep(self.func_name, self.params.copy(), self.enabled)

    def __repr__(self):
        status = "✓" if self.enabled else "✗"
        return f"[{status}] {self.func_name} {self.params}"

    def get_display_name(self) -> str:
        """获取显示名称。"""
        param_str = ", ".join(f"{k}={v}" for k, v in self.params.items() if v != 0)
        if param_str:
            return f"{self.func_name} ({param_str})"
        return self.func_name


class PipelineItem:
    """流水线项目 —— 可以是处理步骤或文件夹。"""

    def __init__(self, item_type: str, step: ProcessingStep = None, folder_name: str = ""):
        self.type = item_type          # "step" 或 "folder"
        self.step = step               # ProcessingStep (仅 step 类型)
        self.folder_name = folder_name # 文件夹名称 (仅 folder 类型)
        self.enabled = True            # 文件夹启用状态 (folder 类型用)
        self.expanded = True           # 文件夹展开状态 (folder 类型用)
        self.folder_depth = 0          # 嵌套深度 (0=顶级)

    @staticmethod
    def from_step(step: ProcessingStep) -> 'PipelineItem':
        return PipelineItem("step", step=step)

    @staticmethod
    def from_folder(name: str) -> 'PipelineItem':
        return PipelineItem("folder", folder_name=name)

    def toggle_expanded(self):
        """切换文件夹展开/折叠状态。"""
        if self.type == "folder":
            self.expanded = not self.expanded


class ProcessingPipeline:
    """图像处理流水线 —— 管理多个处理步骤的有序执行，支持文件夹分组。"""

    def __init__(self):
        self._items = []         # PipelineItem 列表 (混合步骤和文件夹)
        self._original_img = None  # 原始图像

    # ── 内部辅助 ──
    def _get_item(self, idx: int):
        """根据 _items 索引获取项目。"""
        if 0 <= idx < len(self._items):
            return self._items[idx]
        return None

    # ── 属性 ──
    @property
    def step_count(self) -> int:
        """步骤数量（不含原图和文件夹）。"""
        return sum(1 for item in self._items if item.type == "step")

    @property
    def item_count(self) -> int:
        """项目总数（含文件夹）。"""
        return len(self._items)

    # ── 原始图像 ──
    def set_original_image(self, img: np.ndarray):
        """设置原始图像。"""
        self._original_img = img.copy() if img is not None else None

    def get_original_image(self) -> np.ndarray:
        """获取原始图像。"""
        return self._original_img

    # ── 步骤操作 (全部使用 _items 索引) ──
    def add_step(self, func_name: str, params: dict) -> int:
        """添加处理步骤到末尾（确保在顶级位置，不在文件夹内）。返回 _items 索引。"""
        step = ProcessingStep(func_name, params)
        item = PipelineItem.from_step(step)
        # 找到最后一个顶级项目的后面插入
        insert_pos = self._find_top_level_end()
        self._items.insert(insert_pos, item)
        return insert_pos

    def _find_top_level_end(self) -> int:
        """找到顶级步骤的插入位置（列表末尾）。"""
        return len(self._items)

    def insert_step(self, index: int, func_name: str, params: dict, depth: int = 0):
        """在 _items 指定位置插入处理步骤。"""
        step = ProcessingStep(func_name, params)
        item = PipelineItem.from_step(step)
        item.folder_depth = depth
        self._items.insert(index, item)

    def insert_folder_at(self, index: int, name: str, depth: int = 0):
        """在指定位置插入文件夹（支持嵌套）。"""
        item = PipelineItem.from_folder(name)
        item.folder_depth = depth
        self._items.insert(index, item)

    def add_step_inside_folder(self, folder_index: int, func_name: str, params: dict):
        """在文件夹内部末尾添加步骤（作为该文件夹的最后一个子项）。"""
        folder = self._get_item(folder_index)
        if not folder or folder.type != "folder":
            return self.add_step(func_name, params)
        target_depth = folder.folder_depth + 1
        insert_pos = self._find_folder_end(folder_index)
        self.insert_step(insert_pos, func_name, params, depth=target_depth)
        return insert_pos

    def add_folder_inside_folder(self, folder_index: int, name: str):
        """在文件夹内部末尾添加子文件夹。"""
        folder = self._get_item(folder_index)
        if not folder or folder.type != "folder":
            return self.add_folder(name)
        target_depth = folder.folder_depth + 1
        insert_pos = self._find_folder_end(folder_index)
        self.insert_folder_at(insert_pos, name, depth=target_depth)
        return insert_pos

    def _find_folder_end(self, folder_index: int) -> int:
        """找到文件夹所有子项之后的位置。"""
        folder = self._get_item(folder_index)
        if not folder:
            return len(self._items)
        base_depth = folder.folder_depth
        pos = folder_index + 1
        while pos < len(self._items):
            if self._items[pos].folder_depth <= base_depth:
                break
            pos += 1
        return pos

    def _compute_depth_at(self, index: int) -> int:
        """计算插入位置的文件夹深度（用于拖拽等场景）。"""
        if index <= 0:
            return 0
        if index > len(self._items):
            return self._items[-1].folder_depth if self._items else 0
        # 看目标位置当前项的深度
        return self._items[index].folder_depth

    def remove_step(self, index: int) -> bool:
        """删除 _items 指定位置的项目。"""
        if 0 <= index < len(self._items):
            self._items.pop(index)
            return True
        return False

    def move_step(self, from_index: int, to_index: int) -> bool:
        """移动 _items 中的项目位置。"""
        if (0 <= from_index < len(self._items) and
                0 <= to_index < len(self._items)):
            item = self._items.pop(from_index)
            self._items.insert(to_index, item)
            return True
        return False

    def move_up(self, index: int) -> bool:
        if index > 0 and index < len(self._items):
            return self.move_step(index, index - 1)
        return False

    def move_down(self, index: int) -> bool:
        if index >= 0 and index < len(self._items) - 1:
            return self.move_step(index, index + 1)
        return False

    def update_step(self, index: int, func_name: str = None, params: dict = None) -> bool:
        """更新 _items 指定位置的步骤参数。"""
        item = self._get_item(index)
        if item and item.type == "step" and item.step:
            if func_name is not None:
                item.step.func_name = func_name
            if params is not None:
                item.step.params = params.copy()
            return True
        return False

    def toggle_step(self, index: int) -> bool:
        """切换 _items 指定位置项目的启用/禁用状态。"""
        item = self._get_item(index)
        if item:
            if item.type == "step" and item.step:
                item.step.enabled = not item.step.enabled
                return item.step.enabled
            elif item.type == "folder":
                item.enabled = not item.enabled
                return item.enabled
        return False

    def get_steps(self) -> list:
        """获取所有步骤的副本（不含文件夹）。"""
        return copy.deepcopy([item.step for item in self._items if item.type == "step"])

    def get_step(self, index: int):
        """根据 _items 索引获取项目。"""
        return self._get_item(index)

    # ── 文件夹操作 ──
    def add_folder(self, name: str) -> int:
        """添加文件夹到末尾。返回 _items 索引。"""
        item = PipelineItem.from_folder(name)
        self._items.append(item)
        return len(self._items) - 1

    def rename_folder(self, index: int, new_name: str) -> bool:
        """重命名文件夹。"""
        item = self._get_item(index)
        if item and item.type == "folder":
            item.folder_name = new_name
            return True
        return False

    def delete_folder(self, index: int) -> bool:
        """删除文件夹及其包含的所有子项（步骤和子文件夹）。"""
        item = self._get_item(index)
        if item and item.type == "folder":
            target_depth = item.folder_depth
            # 删除文件夹头
            self._items.pop(index)
            # 删除后续深度大于目标的所有子项
            while index < len(self._items):
                if self._items[index].folder_depth <= target_depth:
                    break
                self._items.pop(index)
            return True
        return False

    # ── 执行 ──
    def apply_all(self, processor) -> np.ndarray:
        """执行整个流水线，返回最终结果。跳过文件夹。"""
        if self._original_img is None:
            return None

        current_img = self._original_img.copy()

        for item in self._items:
            if item.type != "step" or not item.step:
                continue
            step = item.step
            if not step.enabled:
                continue
            func = getattr(processor, step.func_name, None)
            if func is not None:
                try:
                    clean_params = {k: v for k, v in step.params.items()
                                    if not k.startswith("_")}
                    result = func(current_img, **clean_params)
                    if result is not None:
                        current_img = result
                except Exception as e:
                    print(f"处理步骤 {step.func_name} 失败: {e}")

        return current_img

    def apply_to_step(self, processor, target_index: int) -> np.ndarray:
        """执行流水线到 _items 指定位置（包含该位置），返回中间结果。"""
        if self._original_img is None:
            return None

        current_img = self._original_img.copy()

        for i, item in enumerate(self._items):
            if i > target_index:
                break
            if item.type != "step" or not item.step:
                continue
            step = item.step
            if not step.enabled:
                continue
            func = getattr(processor, step.func_name, None)
            if func is not None:
                try:
                    clean_params = {k: v for k, v in step.params.items()
                                    if not k.startswith("_")}
                    result = func(current_img, **clean_params)
                    if result is not None:
                        current_img = result
                except Exception as e:
                    print(f"处理步骤 {step.func_name} 失败: {e}")

        return current_img

    def clear(self):
        """清空流水线。"""
        self._items.clear()

    # ── 显示 ──
    def get_display_list(self) -> list:
        """获取用于显示的步骤列表，支持文件夹嵌套和折叠。

        显示格式:
            0: 原图
            1: 📁 文件夹名          (QTreeWidget 原生箭头表示展开/折叠)
               1: [✓] func_name
               2: [✗] func_name
            2: 📁 子文件夹
            3: [✓] 顶级步骤
        """
        display = ["0: 原图"]

        top_num = 0           # 顶级编号
        child_num = 0         # 文件夹内子项编号
        last_folder_depth = -1  # 最近的文件夹深度，用于子项编号重置
        folder_enabled = True

        # 折叠跟踪
        collapsed_depth = -1

        for item in self._items:
            depth = item.folder_depth

            # 折叠区域内跳过
            if collapsed_depth >= 0 and depth > collapsed_depth:
                continue
            collapsed_depth = -1

            if depth == 0:
                # ── 顶级项目 ──
                folder_enabled = True
                child_num = 0
                last_folder_depth = -1
                top_num += 1

                if item.type == "folder":
                    if not item.expanded:
                        collapsed_depth = depth
                    folder_enabled = item.enabled
                    display.append(f"{top_num}: 📁 {item.folder_name}")
                elif item.type == "step" and item.step:
                    status = "✓" if item.step.enabled else "✗"
                    display.append(
                        f"{top_num}: [{status}] {item.step.get_display_name()}")
            else:
                # ── 文件夹内项目 ──
                # 进入新的文件夹子层级时重置编号
                if depth > last_folder_depth:
                    child_num = 0
                    last_folder_depth = depth

                if item.type == "folder":
                    child_num += 1
                    if not item.expanded:
                        collapsed_depth = depth
                    display.append(f"{child_num}: 📁 {item.folder_name}")
                elif item.type == "step" and item.step:
                    child_num += 1
                    status = "✓" if item.step.enabled else "✗"
                    display.append(
                        f"{child_num}: [{status}] {item.step.get_display_name()}")

        return display

    # ── 导入导出 ──
    def export_to_dict(self) -> dict:
        """导出流水线配置为字典。"""
        items = []
        for item in self._items:
            if item.type == "step" and item.step:
                items.append({
                    "type": "step",
                    "func_name": item.step.func_name,
                    "params": item.step.params,
                    "enabled": item.step.enabled
                })
            elif item.type == "folder":
                items.append({
                    "type": "folder",
                    "name": item.folder_name
                })
        return {"items": items}

    def export_to_json(self, file_path: str) -> bool:
        try:
            data = self.export_to_dict()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"导出流水线失败: {e}")
            return False

    def import_from_dict(self, data: dict):
        """从字典导入流水线配置。"""
        self._items.clear()
        # 兼容旧格式
        if "steps" in data and "items" not in data:
            for step_data in data.get("steps", []):
                step = ProcessingStep(
                    func_name=step_data["func_name"],
                    params=step_data["params"],
                    enabled=step_data.get("enabled", True)
                )
                self._items.append(PipelineItem.from_step(step))
            return
        # 新格式
        for item_data in data.get("items", []):
            if item_data.get("type") == "folder":
                self._items.append(PipelineItem.from_folder(item_data["name"]))
            else:
                step = ProcessingStep(
                    func_name=item_data["func_name"],
                    params=item_data["params"],
                    enabled=item_data.get("enabled", True)
                )
                self._items.append(PipelineItem.from_step(step))

    def import_from_json(self, file_path: str) -> bool:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.import_from_dict(data)
            return True
        except Exception as e:
            print(f"导入流水线失败: {e}")
            return False
