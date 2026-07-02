"""YOLO 检测节点 — 使用 ultralytics YOLOv8+ 模型进行目标检测。

功能：
- 加载 .pt 模型文件
- 读取模型支持的检测类别
- 对输入图像执行检测
- 输出标注后的图像和类别列表
"""

import numpy as np

from core.logger import logger
from core.node_base.node import NodeBase, NodeState


class YoloDetectNode(NodeBase):
    """YOLO 目标检测节点。"""

    def execute(self) -> bool:
        # 1. 读取参数
        model_path_param = self.params.get("model_path", [])
        # file_list 类型返回列表，取第一个文件
        if isinstance(model_path_param, list):
            model_path = model_path_param[0] if model_path_param else ""
        else:
            model_path = str(model_path_param).strip()

        conf_threshold = self.params.get("conf_threshold", 0.25)
        iou_threshold = self.params.get("iou_threshold", 0.45)

        if not model_path:
            logger.error(f"[{self.meta.name}] 未指定模型文件路径，请在参数中选择 .pt 文件")
            self.set_state(NodeState.ERROR)
            return False

        # 2. 加载模型
        try:
            from ultralytics import YOLO
            model = YOLO(model_path)
        except Exception as e:
            logger.error(f"[{self.meta.name}] 加载模型失败: {e}")
            self.set_state(NodeState.ERROR)
            return False

        # 3. 读取类别名称（仅日志记录）
        class_names = model.names  # {0: 'person', 1: 'bicycle', ...}
        logger.info(f"[{self.meta.name}] 模型类别 ({len(class_names)}): {', '.join(class_names.values())}")

        # 4. 获取输入图像
        input_images = self._get_input_images("images")
        if not input_images:
            logger.warning(f"[{self.meta.name}] 无输入图像")
            self.set_state(NodeState.ERROR)
            return False

        # 5. 执行检测
        results = []
        total_detections = 0
        for img in input_images:
            try:
                # ultralytics 接受 numpy 数组（BGR 格式）
                det_results = model(
                    img,
                    conf=conf_threshold,
                    iou=iou_threshold,
                    verbose=False,
                )
                # 获取标注后的图像
                annotated = det_results[0].plot()
                results.append(annotated)

                # 统计检测数量
                num_det = len(det_results[0].boxes)
                total_detections += num_det
                logger.debug(
                    f"[{self.meta.name}] 检测到 {num_det} 个目标"
                )
            except Exception as e:
                logger.error(f"[{self.meta.name}] 检测失败: {e}")
                # 检测失败时输出原图
                results.append(img.copy())

        # 6. 设置输出
        self._set_output_images("images", results)

        logger.info(
            f"[{self.meta.name}] 处理完成: {len(results)} 张图像, "
            f"共 {total_detections} 个检测结果"
        )
        self.set_state(NodeState.SUCCESS)
        return True
