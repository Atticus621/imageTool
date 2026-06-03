# -*- coding: utf-8 -*-
"""PySide6 图像查看器入口 (模块模式)。

用法:
    python -m imageTools.qt_app.main [图片路径]
    或直接运行项目根目录的 run_qt.py
"""
import sys
import os

# 支持直接运行：将项目根目录加入 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from imageTools.logger import setup_logging, get_logger
from imageTools.image_viewer import ImageViewer

logger = get_logger(__name__)


def main():
    setup_logging()
    logger.info("=== 图像查看器启动 ===")
    logger.info("Python: %s / PySide6", sys.version.split()[0])
    logger.debug("命令行参数: %s", sys.argv[1:])

    app = QApplication(sys.argv)
    app.setApplicationName("图像查看器")
    logger.debug("QApplication 创建完成")

    viewer = ImageViewer()
    logger.info("ImageViewer 初始化完成")

    if len(sys.argv) > 1:
        logger.info("从命令行加载图片: %s", sys.argv[1])
        viewer.run(sys.argv[1])
    else:
        viewer.run()

    logger.info("进入事件循环")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
