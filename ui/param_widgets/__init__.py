"""ParamWidget package — modular parameter widget handlers.

Importing this package auto-registers all ParamWidget subclasses via
their __init_subclass__ hook. Use ``create_param_widget(param)`` as
the single entry point for building parameter widgets.
"""

from .base import ParamWidget, create_param_widget, get_widget_class
from .combo import ComboParamWidget
from .int_slider import IntSliderParamWidget
from .float_slider import FloatSliderParamWidget
from .text import TextParamWidget
from .checkbox import CheckboxParamWidget
from .file_list import FileListParamWidget
from .channel_range import ChannelRangeParamWidget

__all__ = [
    "ParamWidget",
    "create_param_widget",
    "get_widget_class",
    "ComboParamWidget",
    "IntSliderParamWidget",
    "FloatSliderParamWidget",
    "TextParamWidget",
    "CheckboxParamWidget",
    "FileListParamWidget",
    "ChannelRangeParamWidget",
]
