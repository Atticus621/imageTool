"""ROI 转换器包。

导入此包时自动注册所有内置转换器。
新增转换器只需在本文件中添加 import。
"""

from . import circle, mask, polygon, rectangle

__all__ = ["circle", "polygon", "rectangle", "mask"]
