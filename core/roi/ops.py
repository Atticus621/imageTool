"""ROI 纯函数操作 — 合并、裁剪、掩码应用。

所有函数无副作用，不修改输入数据。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

import numpy as np

if TYPE_CHECKING:
    from .data import ROIData


def combine_rois(
    rois: list[ROIData],
    image_size: tuple[int, int],
    mode: str = "union",
) -> np.ndarray:
    """合并多个 ROI 为单个二值掩码。

    Args:
        rois: ROI 列表。
        image_size: 目标尺寸 (width, height)。
        mode: 合并模式 — "union", "intersection", "difference"。

    Returns:
        bool 类型 numpy 数组，shape=(height, width)。
    """
    from .converter import converter_registry

    if not rois:
        return np.ones((image_size[1], image_size[0]), dtype=bool)

    masks = []
    for roi in rois:
        converter = converter_registry.get(roi.roi_type)
        masks.append(converter.to_mask(roi, image_size))

    if mode == "union":
        result = masks[0]
        for m in masks[1:]:
            result = result | m
        return result

    elif mode == "intersection":
        result = masks[0]
        for m in masks[1:]:
            result = result & m
        return result

    elif mode == "difference":
        result = masks[0]
        for m in masks[1:]:
            result = result & ~m
        return result

    else:
        raise ValueError(f"Unsupported combine mode: {mode}")


def apply_roi_mask(
    image: np.ndarray,
    mask: np.ndarray,
    fill: int = 0,
) -> np.ndarray:
    """应用掩码到图像，区域外填充指定值。

    Args:
        image: 源图像。
        mask: bool 掩码，shape=(height, width)。
        fill: 区域外填充值。

    Returns:
        处理后的图像。
    """
    result = image.copy()
    if image.ndim == 3 and mask.ndim == 2:
        mask_3ch = np.stack([mask] * image.shape[2], axis=-1)
    else:
        mask_3ch = mask
    result[~mask_3ch] = fill
    return result


def apply_roi_crop(
    image: np.ndarray,
    bbox: tuple[int, int, int, int],
) -> np.ndarray:
    """裁剪图像到指定边界框。

    Args:
        image: 源图像。
        bbox: (x, y, width, height)。

    Returns:
        裁剪后的图像。
    """
    x, y, w, h = bbox
    return image[y:y + h, x:x + w]


def apply_roi_constraint(
    original: np.ndarray,
    processed: np.ndarray,
    rois: list[ROIData],
) -> np.ndarray:
    """将处理结果约束到 ROI 区域内。

    ROI 区域内的像素取 processed 的值，区域外保持 original 的值。
    无 ROI 时直接返回 processed。

    Args:
        original: 原始图像。
        processed: 处理后的图像。
        rois: ROI 列表。

    Returns:
        约束后的图像。
    """
    if not rois:
        return processed

    if processed.shape[:2] != original.shape[:2]:
        return processed

    h, w = original.shape[:2]
    mask = combine_rois(rois, (w, h))

    result = original.copy()
    if original.ndim == 3 and mask.ndim == 2:
        mask_3ch = np.stack([mask] * original.shape[2], axis=-1)
    else:
        mask_3ch = mask

    result[mask_3ch] = processed[mask_3ch]
    return result
