"""Color conversion node — converts images between color spaces."""

from __future__ import annotations

import cv2
import numpy as np

from core.image_data import ImageData
from core.logger import logger
from core.node_base.node import NodeBase, NodeState


# Mapping from (source, target) color space pair to cv2.COLOR_* code.
# Built lazily using cv2 constant naming convention.
def _build_conversion_map():
    """Build the (src, tgt) → cv2 code mapping."""
    pairs = {}
    spaces = ["BGR", "RGB", "HSV", "HLS", "LAB", "LUV", "GRAY", "XYZ", "YCrCb"]

    for src in spaces:
        for tgt in spaces:
            if src == tgt:
                continue
            code_name = f"COLOR_{src}2{tgt}"
            code = getattr(cv2, code_name, None)
            if code is not None:
                pairs[(src.lower(), tgt.lower())] = code

    return pairs


_CONVERSION_MAP = _build_conversion_map()


class ColorConversionNode(NodeBase):
    """Converts input images from their current color space to a target."""

    def execute(self) -> bool:
        target_type = self.params.get("target_type", "bgr")

        # Get raw items (may include ImageData wrappers with color space info)
        raw_items = self._get_input_images_raw("images")
        if not raw_items:
            logger.warning(f"[{self.meta.name}] No input images")
            self.set_state(NodeState.ERROR)
            return False

        results = []
        for item in raw_items:
            if isinstance(item, ImageData):
                src_cs = item.color_space
                img = item.array
            else:
                # Raw ndarray defaults to BGR
                src_cs = "bgr"
                img = item

            converted = self._convert(img, src_cs, target_type)
            results.append(ImageData(array=converted, color_space=target_type))

        self._set_output_images("images", results)
        logger.info(
            f"[{self.meta.name}] Converted {len(results)} images to {target_type}"
        )
        self.set_state(NodeState.SUCCESS)
        return True

    def _convert(
        self, img: np.ndarray, src_cs: str, tgt_cs: str
    ) -> np.ndarray:
        """Convert an image from src_cs to tgt_cs color space."""
        if src_cs == tgt_cs:
            return img.copy()

        code = _CONVERSION_MAP.get((src_cs, tgt_cs))
        if code is not None:
            return cv2.cvtColor(img, code)

        # Fallback: try two-step conversion via BGR
        logger.info(
            f"[{self.meta.name}] No direct {src_cs}→{tgt_cs} conversion, "
            f"trying via BGR"
        )
        code1 = _CONVERSION_MAP.get((src_cs, "bgr"))
        code2 = _CONVERSION_MAP.get(("bgr", tgt_cs))
        if code1 is not None and code2 is not None:
            intermediate = cv2.cvtColor(img, code1)
            return cv2.cvtColor(intermediate, code2)

        logger.error(
            f"[{self.meta.name}] Cannot convert {src_cs} → {tgt_cs}"
        )
        return img.copy()
