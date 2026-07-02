"""ROI — Region of Interest data model and utilities.

Provides a unified way to represent and combine regions of interest
produced by shape detection nodes and mask operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np


class ROIType(Enum):
    """Supported ROI representations."""

    MASK = "mask"           # binary mask array
    CIRCLE = "circle"       # (center_x, center_y, radius)
    POLYGON = "polygon"     # Nx2 array of vertices
    RECTANGLE = "rectangle"  # (x, y, width, height)


@dataclass(frozen=True)
class ROI:
    """Immutable region of interest.

    Attributes:
        roi_type: The kind of ROI.
        data: Type-specific data (see ROIType).
        image_size: Optional reference image size (width, height) used when
            the ROI itself does not carry size information (e.g. circles).
    """

    roi_type: ROIType
    data: Any
    image_size: tuple[int, int] | None = None

    def __post_init__(self):
        # Normalize numpy data to arrays for polygon/mask.
        if self.roi_type == ROIType.POLYGON and not isinstance(self.data, np.ndarray):
            object.__setattr__(self, "data", np.asarray(self.data, dtype=np.int32))


def _safe_image_size(roi: ROI, fallback: tuple[int, int] | None) -> tuple[int, int]:
    """Return ROI image_size or fallback, raising if neither is available."""
    size = roi.image_size or fallback
    if size is None:
        raise ValueError(f"ROI {roi.roi_type} requires image_size")
    return size


def roi_to_mask(
    roi: ROI,
    image_size: tuple[int, int] | None = None,
) -> np.ndarray:
    """Convert any ROI to a binary mask of the given image size.

    Args:
        roi: The ROI to convert.
        image_size: Target (width, height). Required when roi.image_size is None.

    Returns:
        Boolean mask of shape (height, width).
    """
    import cv2

    w, h = _safe_image_size(roi, image_size)
    mask = np.zeros((h, w), dtype=np.uint8)

    if roi.roi_type == ROIType.MASK:
        data = np.asarray(roi.data)
        if data.shape[:2] != (h, w):
            data = cv2.resize(data, (w, h), interpolation=cv2.INTER_NEAREST)
        mask[data > 0] = 1

    elif roi.roi_type == ROIType.CIRCLE:
        cx, cy, r = roi.data
        cv2.circle(mask, (int(cx), int(cy)), int(r), 1, -1)

    elif roi.roi_type == ROIType.POLYGON:
        pts = np.asarray(roi.data, dtype=np.int32)
        if pts.size == 0:
            return mask.astype(bool)
        if pts.ndim == 2:
            pts = pts.reshape(1, -1, 2)
        cv2.fillPoly(mask, pts, 1)

    elif roi.roi_type == ROIType.RECTANGLE:
        x, y, rw, rh = roi.data
        x1, y1 = max(0, int(x)), max(0, int(y))
        x2, y2 = min(w, int(x + rw)), min(h, int(y + rh))
        if x2 > x1 and y2 > y1:
            mask[y1:y2, x1:x2] = 1

    return mask.astype(bool)


def combine_rois(
    rois: list[ROI],
    image_size: tuple[int, int],
    mode: str = "union",
) -> np.ndarray:
    """Combine multiple ROIs into a single binary mask.

    Args:
        rois: List of ROIs.
        image_size: Target (width, height).
        mode: Combination mode. Currently only "union" is supported.

    Returns:
        Boolean mask of shape (height, width).
    """
    if not rois:
        return np.ones((image_size[1], image_size[0]), dtype=bool)

    if mode != "union":
        raise ValueError(f"Unsupported ROI combine mode: {mode}")

    combined = np.zeros((image_size[1], image_size[0]), dtype=bool)
    for roi in rois:
        combined |= roi_to_mask(roi, image_size)
    return combined


def roi_to_bbox(roi: ROI) -> tuple[int, int, int, int]:
    """Compute the bounding box (x, y, width, height) of a ROI.

    Returns:
        (x, y, w, h). Returns (0, 0, 0, 0) for empty ROIs.
    """
    size = roi.image_size
    if size is None and roi.roi_type == ROIType.RECTANGLE:
        x, y, w, h = roi.data
        return (int(x), int(y), int(w), int(h))

    mask = roi_to_mask(roi, size)
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return (0, 0, 0, 0)

    x, y = int(xs.min()), int(ys.min())
    w = int(xs.max()) - x + 1
    h = int(ys.max()) - y + 1
    return (x, y, w, h)


def apply_roi_to_image(
    image: np.ndarray,
    roi: ROI,
    mode: str = "mask",
    fill: int = 0,
) -> np.ndarray:
    """Apply a ROI to an image.

    Args:
        image: Source image.
        roi: ROI to apply.
        mode: "mask" keeps image size but fills outside ROI; "crop" returns
            the bounding box region.
        fill: Fill value for outside pixels in mask mode.

    Returns:
        Processed image.
    """
    if mode == "crop":
        x, y, w, h = roi_to_bbox(roi)
        return image[y:y + h, x:x + w]

    if mode != "mask":
        raise ValueError(f"Unsupported ROI apply mode: {mode}")

    h, w = image.shape[:2]
    mask = roi_to_mask(roi, (w, h))
    result = image.copy()

    if image.ndim == 3:
        mask = np.stack([mask] * image.shape[2], axis=-1)

    result[~mask] = fill
    return result


def apply_roi_aware(
    image: np.ndarray,
    rois: list[ROI],
    processor,
) -> np.ndarray:
    """Process an image while only modifying pixels inside the given ROIs.

    The output has the same shape as the input. Pixels outside the ROI(s)
    keep their original values; pixels inside are replaced by the processor
    output.

    Args:
        image: Source image.
        rois: ROIs constraining the processing. If empty, returns processor(image).
        processor: Callable taking an image and returning a processed image
            of the same shape.

    Returns:
        ROI-aware processed image.
    """
    if not rois:
        return processor(image)

    h, w = image.shape[:2]
    mask = combine_rois(rois, (w, h))
    processed = processor(image)

    if processed.shape[:2] != image.shape[:2]:
        # Processor changed geometry; cannot composite safely.
        return processed

    result = image.copy()
    if image.ndim == 3 and mask.ndim == 2:
        mask_3ch = np.stack([mask] * image.shape[2], axis=-1)
    else:
        mask_3ch = mask

    result[mask_3ch] = processed[mask_3ch]
    return result
