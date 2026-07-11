"""Mask operations node — logical operations on binary mask images."""

from __future__ import annotations

import numpy as np

from core.image_data import ImageData, ColorSpace
from core.logger import logger
from core.node_base.node import NodeBase, NodeState


class MaskOperationsNode(NodeBase):
    """Performs logical operations (AND/OR/XOR/NOT/NAND/NOR) on binary masks.

    Supports variable input count (1-6) via the ``input_count`` parameter.
    All input masks are first normalised to boolean (value > 0 → True).
    The output is a single-channel uint8 mask (0 or 255).
    """

    # ── Node metadata (no meta.json needed) ─────────────────────────
    NODE_ID = "processing/arithmetic/mask_ops"
    NODE_NAME = "掩码操作"
    NODE_CATEGORY = "图像处理"
    NODE_SUBCATEGORY = "运算"
    NODE_DESCRIPTION = "对多个掩码图像进行逻辑运算（与/或/非/异或/与非/或非），支持动态输入个数"
    NODE_INPUTS = [
        {"name": "mask_a", "type": "image", "label": "掩码 A", "count_param": "input_count"},
        {"name": "mask_b", "type": "image", "label": "掩码 B", "count_param": "input_count"},
        {"name": "mask_c", "type": "image", "label": "掩码 C", "count_param": "input_count"},
        {"name": "mask_d", "type": "image", "label": "掩码 D", "count_param": "input_count"},
        {"name": "mask_e", "type": "image", "label": "掩码 E", "count_param": "input_count"},
        {"name": "mask_f", "type": "image", "label": "掩码 F", "count_param": "input_count"},
    ]
    NODE_OUTPUTS = [
        {"name": "mask", "type": "image", "label": "运算结果"},
    ]
    NODE_OPTIONAL_PORTS = [
        {"name": "roi", "label": "ROI 输入", "port_type": "roi", "direction": "input", "default": False, "group": "input"},
    ]
    NODE_PARAMS = [
        {
            "name": "operation", "type": "combo", "label": "逻辑运算", "default": "and", "pinned": True,
            "options": [
                {"value": "and",  "label": "AND (与)"},
                {"value": "or",   "label": "OR (或)"},
                {"value": "xor",  "label": "XOR (异或)"},
                {"value": "not",  "label": "NOT (非)"},
                {"value": "nand", "label": "NAND (与非)"},
                {"value": "nor",  "label": "NOR (或非)"},
            ],
        },
        {
            "name": "input_count", "type": "int_slider", "label": "输入个数",
            "default": 2, "min": 1, "max": 6, "step": 1,
        },
    ]

    OPERATIONS = {
        "and":  lambda masks: _all_reduce(masks, np.logical_and),
        "or":   lambda masks: _all_reduce(masks, np.logical_or),
        "xor":  lambda masks: _all_reduce(masks, np.logical_xor),
        "nand": lambda masks: ~_all_reduce(masks, np.logical_and),
        "nor":  lambda masks: ~_all_reduce(masks, np.logical_or),
        "not":  lambda masks: ~_all_reduce(masks, np.logical_and),
    }

    def execute(self) -> bool:
        operation = self.params.get("operation", "and")
        input_count = int(self.params.get("input_count", 2))

        # Collect input masks
        input_names = ["mask_a", "mask_b", "mask_c", "mask_d", "mask_e", "mask_f"]
        active_inputs = input_names[:input_count]

        # Gather all connected input data
        masks: list[np.ndarray] = []
        for port_name in active_inputs:
            items = self._get_input_images(port_name)
            if items:
                masks.append(items[0])

        if not masks:
            logger.warning(f"[{self.meta.name}] No input masks")
            self.set_state(NodeState.ERROR)
            return False

        # Validate: all masks must be the same shape
        ref_shape = masks[0].shape[:2]
        normalized: list[np.ndarray] = []
        for i, m in enumerate(masks):
            if m.shape[:2] != ref_shape:
                logger.error(
                    f"[{self.meta.name}] Shape mismatch: mask[0]={ref_shape}, "
                    f"mask[{i}]={m.shape[:2]}"
                )
                self.set_state(NodeState.ERROR)
                return False
            # Normalise to boolean
            normalized.append(m.astype(bool) if m.dtype != bool else m)

        # Execute operation
        op_fn = self.OPERATIONS.get(operation)
        if op_fn is None:
            logger.error(f"[{self.meta.name}] Unknown operation: {operation}")
            self.set_state(NodeState.ERROR)
            return False

        result_bool = op_fn(normalized)

        # Convert back to uint8 mask (0 or 255)
        result = (result_bool.astype(np.uint8)) * 255

        # Apply ROI constraint if connected
        rois = self._get_input_rois("roi")
        if rois:
            from core.roi import ROIManager
            roi_mgr = ROIManager.instance()
            original = (normalized[0].astype(np.uint8)) * 255
            result = roi_mgr.apply_constraint(original, result, rois)

        self._set_output_images("mask", [ImageData(array=result, color_space=ColorSpace.GRAY.value)])

        count_str = f"{len(normalized)} inputs"
        logger.info(
            f"[{self.meta.name}] {operation.upper()} on {count_str} → "
            f"mask {result.shape}"
        )
        self.set_state(NodeState.SUCCESS)
        return True


def _all_reduce(masks: list[np.ndarray], op) -> np.ndarray:
    """Apply a binary logical op cumulatively across all masks."""
    result = masks[0].copy()
    for m in masks[1:]:
        result = op(result, m)
    return result
