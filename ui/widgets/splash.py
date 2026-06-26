from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplashScreen, QLabel, QVBoxLayout, QWidget, QProgressBar
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont


class SplashScreen(QSplashScreen):
    def __init__(self):
        pixmap = QPixmap(400, 250)
        pixmap.fill(QColor(30, 30, 46))
        super().__init__(pixmap)
        self.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint)

        self._label = QLabel("正在启动...", self)
        self._label.setGeometry(20, 160, 360, 30)
        self._label.setStyleSheet("color: #a0a0c0; font-size: 13px;")

        self._progress = QProgressBar(self)
        self._progress.setGeometry(20, 200, 360, 8)
        self._progress.setMaximum(100)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet("""
            QProgressBar {
                background-color: #1e1e2e;
                border: 1px solid #333;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #00b4d8;
                border-radius: 3px;
            }
        """)

        title = QLabel("ImageTools", self)
        title.setGeometry(20, 40, 360, 50)
        title.setStyleSheet("color: #e0e0ff; font-size: 28px; font-weight: bold;")

        subtitle = QLabel("图像处理蓝图工具", self)
        subtitle.setGeometry(20, 90, 360, 30)
        subtitle.setStyleSheet("color: #8080a0; font-size: 14px;")

    def set_progress(self, task_name: str, current: int, total: int):
        self._label.setText(task_name)
        if total > 0:
            self._progress.setValue(int((current + 1) / total * 100))
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()
