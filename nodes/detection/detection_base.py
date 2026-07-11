"""DetectionBase — 检测节点基类。

封装所有检测节点的共性逻辑：
- 可选端口管理（ROI 输入、禁止区域、标注图像输出）
- 标注图像输出控制（通过 _opt_annotated 参数）
- ROI 输出

子类只需实现 _detect() 方法。
"""

from __future__ import annotations

from abc import abstractmethod

import numpy as np

from core.image_data import ImageData
from core.logger import logger
from core.node_base.node import NodeBase, NodeState


class DetectionBase(NodeBase):
    """检测节点基类。

    子类必须实现：
        _detect(img, color_space, **params) -> (annotated_image, rois)
    """

    def execute(self) -> bool:
        items = self._get_input_images_raw("images")
        if not items:
            logger.warning(f"[{self.meta.name}] No input images")
            self.set_state(NodeState.ERROR)
            return False

        # 读取参数
        params = self._get_detection_params()
        output_annotated = self.params.get("_opt_annotated", False)

        results: list[ImageData] = []
        all_rois = []
        for item in items:
            if isinstance(item, ImageData):
                img = item.array
                color_space = item.color_space
            elif isinstance(item, np.ndarray):
                img = item
                color_space = "bgr"
            else:
                continue

            annotated, rois = self._detect(img, color_space, **params)
            if output_annotated and annotated is not None:
                results.append(ImageData(array=annotated, color_space=color_space))
            all_rois.extend(rois)

        if output_annotated and results:
            self._set_output_images("annotated", results)
        self._set_output_rois("rois", all_rois)

        # Output optional statistics
        count = len(all_rois)
        if self._opt_enabled("count"):
            self._set_output_port("count", count)
        if self._opt_enabled("stats"):
            if count > 0:
                stats_text = f"检测到 {count} 个目标"
            else:
                stats_text = "未检测到目标"
            self._set_output_port("stats", stats_text)

        logger.info(
            f"[{self.meta.name}] Processed {len(items)} images, "
            f"output {count} ROIs"
        )
        self.set_state(NodeState.SUCCESS)
        return True

    @abstractmethod
    def _get_detection_params(self) -> dict:
        """返回检测参数字典。子类必须实现。"""
        ...

    @abstractmethod
    def _detect(
        self, img: np.ndarray, color_space: str, **params
    ) -> tuple[np.ndarray | None, list]:
        """执行检测，返回 (标注图像, ROI列表)。

        如果不需要标注图像，返回 (None, rois)。
        """
        ...
