"""NodeGraphQt NodeBaseWidget wrapper for the interactive histogram preview."""

from __future__ import annotations

from NodeGraphQt.widgets.node_widgets import NodeBaseWidget


class NodeHistogramWidget(NodeBaseWidget):
    """Embedded interactive histogram widget for NodeGraphQt nodes."""

    def __init__(self, parent=None, name="histogram_display", label=" "):
        super().__init__(parent, name=name, label=label)
        from ui.widgets.histogram_canvas import HistogramPreview
        self._preview = HistogramPreview()
        self.set_custom_widget(self._preview)

    def get_value(self):
        return None

    def set_value(self, value):
        pass

    def set_hist_data(self, hist_data, chan_names, channel_colors, color_space):
        self._preview.set_hist_data(hist_data, chan_names, channel_colors, color_space)

    def set_channel_visible(self, index: int, visible: bool):
        self._preview.set_channel_visible(index, visible)

    def get_visible_channels(self) -> list[bool]:
        return self._preview.get_visible_channels()

    def clear(self):
        self._preview.clear()
