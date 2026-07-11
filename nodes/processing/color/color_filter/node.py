"""Color filter node — filters images by per-channel value ranges, outputs mask."""

from __future__ import annotations

import cv2
import numpy as np

from core.image_data import ImageData, CHANNEL_NAMES, CHANNEL_RANGES, ColorSpace
from core.logger import logger
from core.node_base.node import NodeBase, NodeState


# ── Conversion mapping ──────────────────────────────────────────────────

def _build_conversion_map() -> dict[tuple[str, str], int]:
    """Build (src, tgt) → cv2.COLOR_* code mapping."""
    pairs: dict[tuple[str, str], int] = {}
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


def _convert_color(img: np.ndarray, src_cs: str, tgt_cs: str) -> np.ndarray:
    """Convert image between color spaces. Returns copy if same space."""
    if src_cs == tgt_cs:
        return img.copy()

    code = _CONVERSION_MAP.get((src_cs, tgt_cs))
    if code is not None:
        return cv2.cvtColor(img, code)

    # Fallback: two-step via BGR
    code1 = _CONVERSION_MAP.get((src_cs, "bgr"))
    code2 = _CONVERSION_MAP.get(("bgr", tgt_cs))
    if code1 is not None and code2 is not None:
        intermediate = cv2.cvtColor(img, code1)
        return cv2.cvtColor(intermediate, code2)

    logger.error(f"Cannot convert {src_cs} → {tgt_cs}")
    return img.copy()


# ── Node ────────────────────────────────────────────────────────────────

class ColorFilterNode(NodeBase):
    """Filters images by per-channel value ranges.

    All channels of the selected color space are filtered simultaneously.
    The combined mask is AND-ed across all channels.  The filtered image
    keeps original colors for pixels within all channel ranges; pixels
    outside any range are set to black.

    Outputs:
        images — filtered image in the original color space.
        mask   — binary mask (0 or 255) as single-channel GRAY image.
    """

    NODE_ID = "processing/color/color_filter"
    NODE_NAME = "颜色过滤"
    NODE_CATEGORY = "图像处理"
    NODE_SUBCATEGORY = "颜色"
    NODE_DESCRIPTION = "按通道值范围滤波图像，输出滤波后图像和掩码"

    def execute(self) -> bool:
        channel_type = self.params.get("channel_type", "rgb")

        # Read per-channel ranges: each is a [lower, upper] list
        range_0 = self.params.get("channel_0", [0, 255])
        range_1 = self.params.get("channel_1", [0, 255])
        range_2 = self.params.get("channel_2", [0, 255])

        raw_items = self._get_input_images_raw("images")
        if not raw_items:
            logger.warning(f"[{self.meta.name}] No input images")
            self.set_state(NodeState.ERROR)
            return False

        # ── Resolve channel count and valid ranges ────────────────────
        try:
            cs_enum = ColorSpace(channel_type)
        except ValueError:
            logger.error(f"[{self.meta.name}] Unknown color space: {channel_type}")
            self.set_state(NodeState.ERROR)
            return False

        cs_ranges = CHANNEL_RANGES.get(cs_enum, [(0, 255)])
        chan_names = CHANNEL_NAMES.get(cs_enum, ())
        num_channels = len(cs_ranges)
        raw_ranges = [range_0, range_1, range_2][:num_channels]

        # ── Clamp ranges to valid channel limits ──────────────────────
        clamped: list[tuple[int, int]] = []
        for i, (lo, hi) in enumerate(raw_ranges):
            chan_min, chan_max = cs_ranges[i]
            lo = int(max(chan_min, min(chan_max, lo)))
            hi = int(max(chan_min, min(chan_max, hi)))
            if lo > hi:
                lo, hi = hi, lo
            clamped.append((lo, hi))

        # ── Log ───────────────────────────────────────────────────────
        range_strs = []
        for i, (lo, hi) in enumerate(clamped):
            name = chan_names[i] if i < len(chan_names) else f"Ch{i}"
            range_strs.append(f"{name}=[{lo},{hi}]")
        logger.info(
            f"[{self.meta.name}] Filtering {len(raw_items)} image(s): "
            f"{channel_type.upper()} " + ", ".join(range_strs)
        )

        # ── Process ───────────────────────────────────────────────────
        rois = self._get_input_rois("roi")
        roi_mgr = None
        if rois:
            from core.roi import ROIManager
            roi_mgr = ROIManager.instance()

        results: list[ImageData] = []
        masks: list[ImageData] = []
        for item in raw_items:
            if isinstance(item, ImageData):
                original_space = item.color_space
                img = item.array
            else:
                original_space = "bgr"
                img = item

            filtered, mask_arr = self._filter_image_multi(
                img, original_space, channel_type, clamped,
            )

            # Apply ROI constraint if connected
            if roi_mgr and rois:
                filtered = roi_mgr.apply_constraint(img, filtered, rois)

            results.append(ImageData(array=filtered, color_space=original_space))
            masks.append(ImageData(array=mask_arr, color_space=ColorSpace.GRAY.value))

        self._set_output_images("images", results)
        self._set_output_images("mask", masks)
        self.set_state(NodeState.SUCCESS)
        return True

    # ── Core filter logic ────────────────────────────────────────────

    def _filter_image_multi(
        self,
        img: np.ndarray,
        src_space: str,
        filter_space: str,
        channel_ranges: list[tuple[int, int]],
    ) -> tuple[np.ndarray, np.ndarray]:
        """Filter a single image by multiple channel ranges.

        Args:
            img: Source image array.
            src_space: Original color space.
            filter_space: Color space to perform filtering in.
            channel_ranges: (lower, upper) tuples, one per channel.

        Returns:
            (filtered_image_in_original_space, mask_uint8_0_or_255)
        """
        # Step 1: Convert to filter space if needed
        if src_space != filter_space:
            filter_img = _convert_color(img, src_space, filter_space)
        else:
            filter_img = img.copy()

        # Step 2: Build combined mask (AND across all channels)
        combined_mask: np.ndarray = np.ones(filter_img.shape[:2], dtype=bool)

        is_grayscale = len(filter_img.shape) == 2
        for ch_idx, (lower, upper) in enumerate(channel_ranges):
            if is_grayscale:
                if ch_idx == 0:
                    channel_data = filter_img
                else:
                    break  # GRAY has only 1 channel
            else:
                if ch_idx >= filter_img.shape[2]:
                    break
                channel_data = filter_img[:, :, ch_idx]

            ch_mask = (channel_data >= lower) & (channel_data <= upper)
            combined_mask &= ch_mask

        # Step 3: Apply combined mask to filter image
        if is_grayscale:
            filter_img[~combined_mask] = 0
        else:
            mask_3ch = np.stack([combined_mask] * filter_img.shape[2], axis=-1)
            filter_img[~mask_3ch] = 0

        # Step 4: Convert back to original color space
        if src_space != filter_space:
            result = _convert_color(filter_img, filter_space, src_space)
        else:
            result = filter_img

        # Step 5: Build output mask (uint8, 0 or 255)
        mask_out = (combined_mask.astype(np.uint8)) * 255

        return result, mask_out
