from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplashScreen, QLabel, QVBoxLayout, QWidget, QProgressBar
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont

from ui.theme import (BG_BASE, ACCENT, TEXT_PRIMARY, TEXT_SECONDARY, BORDER_DEFAULT,
                      RADIUS_MD, RADIUS_SM, FONT_SIZE_TITLE, FONT_SIZE_SUBTITLE, FONT_SIZE_LOADING)


class SplashScreen(QSplashScreen):
    def __init__(self, app_name="ImageTools", subtitle="蓝图工具"):
        pixmap = QPixmap(400, 250)
        pixmap.fill(QColor(BG_BASE))
        super().__init__(pixmap)
        self.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint)

        self._label = QLabel("正在启动...", self)
        self._label.setGeometry(20, 160, 360, 30)
        self._label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: {FONT_SIZE_LOADING};")

        self._progress = QProgressBar(self)
        self._progress.setGeometry(20, 200, 360, 8)
        self._progress.setMaximum(100)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {BG_BASE};
                border: 1px solid {BORDER_DEFAULT};
                border-radius: {RADIUS_MD};
            }}
            QProgressBar::chunk {{
                background-color: {ACCENT};
                border-radius: {RADIUS_SM};
            }}
        """)

        title = QLabel(app_name, self)
        title.setGeometry(20, 40, 360, 50)
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: {FONT_SIZE_TITLE}; font-weight: bold;")

        subtitle_label = QLabel(subtitle, self)
        subtitle_label.setGeometry(20, 90, 360, 30)
        subtitle_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: {FONT_SIZE_SUBTITLE};")

    def set_progress(self, task_name: str, current: int, total: int):
        self._label.setText(task_name)
        if total > 0:
            self._progress.setValue(int((current + 1) / total * 100))
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()
