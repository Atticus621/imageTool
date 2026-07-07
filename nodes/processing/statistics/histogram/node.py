"""Histogram statistics node — computes per-channel histograms and outputs a visualization."""

from __future__ import annotations

import threading

import cv2
import numpy as np

from core.image_data import ImageData, ColorSpace, CHANNEL_NAMES, CHANNEL_RANGES
from core.logger import logger
from core.node_base.node import NodeBase, NodeState


_HSV_COLORS = ("#e74c3c", "#2ecc71", "#3498db")
_LAB_COLORS = ("#888888", "#e67e22", "#3498db")
_BGR_COLORS = ("#3498db", "#2ecc71", "#e74c3c")
_GRAY_COLORS = ("#888888",)

_pending_lock = threading.Lock()
_pending_data: dict[str, tuple] = {}


class HistogramNode(NodeBase):
    NODE_ID = "processing/statistics/histogram"
    NODE_NAME = "直方图统计"
    NODE_CATEGORY = "图像处理"
    NODE_SUBCATEGORY = "像素统计"
    NODE_DESCRIPTION = "计算图像各通道直方图并输出可视化结果，支持 LAB/HSV 等颜色空间"
    NODE_INPUTS = [
        {"name": "images", "type": "image", "label": "图像输入"},
    ]
    NODE_OUTPUTS = []
    NODE_OPTIONAL_PORTS = [
        {
            "name": "histogram",
            "label": "直方图",
            "port_type": "image",
            "direction": "output",
            "default": True,
            "group": "output",
        },
        {
            "name": "output_image",
            "label": "输出图像",
            "port_type": "image",
            "direction": "output",
            "default": False,
            "group": "output",
        },
    ]
    NODE_PARAMS = [
        {
            "name": "bins",
            "type": "int_slider",
            "label": "分箱数",
            "default": 256,
            "min": 16,
            "max": 512,
            "step": 16,
        },
    ]

    @classmethod
    def pop_pending_data(cls, key: str) -> tuple | None:
        with _pending_lock:
            return _pending_data.pop(key, None)

    def execute(self) -> bool:
        bins = int(self.params.get("bins", 256))

        raw_items = self._get_input_images_raw("images")
        if not raw_items:
            logger.warning(f"[{self.meta.name}] No input images")
            self.set_state(NodeState.ERROR)
            return False

        item = raw_items[0]
        if isinstance(item, ImageData):
            img = item.array
            color_space = item.color_space
        else:
            img = item
            color_space = "bgr"

        try:
            cs_enum = ColorSpace(color_space)
        except ValueError:
            cs_enum = ColorSpace.BGR

        chan_names = CHANNEL_NAMES.get(cs_enum, ("Ch0", "Ch1", "Ch2"))
        cs_ranges = CHANNEL_RANGES.get(cs_enum, [(0, 255)])
        is_gray = cs_enum == ColorSpace.GRAY or img.ndim == 2

        if is_gray:
            hist_data = [self._calc_hist(img if img.ndim == 2 else img[:, :, 0], bins)]
        else:
            hist_data = []
            for ch in range(img.shape[2]):
                hist_data.append(self._calc_hist(img[:, :, ch], bins))

        channel_colors = self._get_channel_colors(cs_enum, len(hist_data))
        names = list(chan_names[:len(hist_data)])

        with _pending_lock:
            key = getattr(self, 'graph_node_name', self.instance_id)
            _pending_data[key] = (
                [h.tolist() for h in hist_data],
                names,
                list(channel_colors),
                color_space,
            )

        if self._opt_enabled("histogram"):
            hist_img = self._render_histogram(
                hist_data, names, channel_colors, cs_ranges, bins, color_space
            )
            self._set_output_images("histogram", [
                ImageData(array=hist_img, color_space="bgr")
            ])

        if self._opt_enabled("output_image"):
            self._set_output_images("output_image", [
                ImageData(array=img.copy(), color_space=color_space)
            ])

        logger.info(
            f"[{self.meta.name}] Histogram: {color_space.upper()}, "
            f"{len(hist_data)} ch, {bins} bins"
        )
        self.set_state(NodeState.SUCCESS)
        return True

    def _opt_enabled(self, name: str) -> bool:
        return self.params.get(f"_opt_{name}", False)

    @staticmethod
    def _calc_hist(channel: np.ndarray, bins: int) -> np.ndarray:
        hist = cv2.calcHist([channel], [0], None, [bins], [0, 256])
        return hist.flatten()

    @staticmethod
    def _get_channel_colors(cs_enum: ColorSpace, n: int) -> list[str]:
        if cs_enum == ColorSpace.HSV:
            return list(_HSV_COLORS[:n])
        if cs_enum == ColorSpace.LAB:
            return list(_LAB_COLORS[:n])
        if cs_enum in (ColorSpace.BGR, ColorSpace.RGB):
            return list(_BGR_COLORS[:n])
        if cs_enum == ColorSpace.GRAY:
            return list(_GRAY_COLORS[:n])
        palette = ("#e74c3c", "#2ecc71", "#3498db")
        return [palette[i % len(palette)] for i in range(n)]

    @staticmethod
    def _render_histogram(
        hist_data: list[np.ndarray],
        chan_names: list[str],
        channel_colors: list[str],
        cs_ranges: list[tuple[int, int]],
        bins: int,
        color_space: str,
    ) -> np.ndarray:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_agg import FigureCanvasAgg

        dpi = 200
        fig, ax = plt.subplots(figsize=(8, 5), dpi=dpi)
        fig.patch.set_facecolor("#2b2b3d")
        ax.set_facecolor("#1e1e2e")

        x = np.linspace(0, 255, bins)

        for i, (hist, name) in enumerate(zip(hist_data, chan_names)):
            color = channel_colors[i] if i < len(channel_colors) else "#888888"
            ax.fill_between(x, hist, alpha=0.35, color=color)
            ax.plot(x, hist, color=color, linewidth=1.5, label=name)

        ax.set_xlim(0, 255)
        ax.set_ylim(bottom=0)
        ax.set_xlabel("Pixel Value", fontsize=14, color="#cccccc")
        ax.set_ylabel("Count", fontsize=14, color="#cccccc")
        ax.set_title(f"{color_space.upper()} Histogram", fontsize=16, color="#eeeeee", pad=10)
        ax.tick_params(colors="#999999", labelsize=11)
        for spine in ax.spines.values():
            spine.set_color("#555555")
            spine.set_linewidth(1.2)
        ax.legend(fontsize=12, framealpha=0.6, facecolor="#3b3b4d",
                  edgecolor="#555555", labelcolor="#cccccc")
        fig.tight_layout(pad=0.8)

        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        buf = canvas.buffer_rgba()
        arr = np.asarray(buf)
        img = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
        plt.close(fig)
        return img
