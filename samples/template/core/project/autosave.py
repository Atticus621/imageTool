"""Auto-save manager — periodic project saving.

Provides automatic saving of project state at regular intervals
to prevent data loss. Saves to the same directory as the main
project file with a ~ suffix.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QTimer, QObject

from core.logger import logger
from .errors import AutoSaveError
from .models import ProjectData
from .serializer import ProjectSerializer


class AutoSaveManager(QObject):
    """Manages automatic project saving.

    Saves project data at regular intervals to prevent data loss.
    Auto-save files are stored alongside the main project file
    with a ~ suffix (e.g., project.itproj~).
    """

    DEFAULT_INTERVAL_MS = 60000  # 1 minute

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timer)
        self._interval_ms = self.DEFAULT_INTERVAL_MS
        self._project_path: Path | None = None
        self._data_provider: Callable[[], ProjectData] | None = None
        self._enabled = True
        self._last_save_path: Path | None = None

    @property
    def interval_ms(self) -> int:
        """Auto-save interval in milliseconds."""
        return self._interval_ms

    @property
    def is_running(self) -> bool:
        """Whether auto-save timer is running."""
        return self._timer.isActive()

    @property
    def last_save_path(self) -> Path | None:
        """Path of the last auto-save file."""
        return self._last_save_path

    def set_interval(self, seconds: int) -> None:
        """Set the auto-save interval.

        Args:
            seconds: Interval in seconds (minimum 10).
        """
        self._interval_ms = max(10, seconds) * 1000
        if self._timer.isActive():
            self._timer.setInterval(self._interval_ms)
        logger.info(f"[AutoSave] Interval set to {seconds}s")

    def set_project_path(self, path: Path | None) -> None:
        """Set the current project file path.

        Args:
            path: Path to the project file, or None to clear.
        """
        self._project_path = path

    def set_data_provider(self, provider: Callable[[], ProjectData]) -> None:
        """Set the function that provides current project data.

        Args:
            provider: Callable that returns current ProjectData.
        """
        self._data_provider = provider

    def start(self) -> None:
        """Start the auto-save timer."""
        if not self._enabled:
            return

        if self._data_provider is None:
            logger.warning("[AutoSave] No data provider set, cannot start")
            return

        self._timer.start(self._interval_ms)
        logger.info(f"[AutoSave] Started (interval: {self._interval_ms // 1000}s)")

    def stop(self) -> None:
        """Stop the auto-save timer."""
        self._timer.stop()
        logger.info("[AutoSave] Stopped")

    def save_now(self) -> Path | None:
        """Perform an immediate auto-save.

        Returns:
            Path to the saved file, or None if save was skipped.
        """
        return self._do_save()

    def enable(self) -> None:
        """Enable auto-save."""
        self._enabled = True
        if self._project_path and self._data_provider:
            self.start()

    def disable(self) -> None:
        """Disable auto-save."""
        self._enabled = False
        self.stop()

    def _on_timer(self) -> None:
        """Timer callback."""
        self._do_save()

    def _do_save(self) -> Path | None:
        """Perform the actual save operation."""
        if self._project_path is None:
            logger.debug("[AutoSave] No project path, skipping")
            return None

        if self._data_provider is None:
            logger.debug("[AutoSave] No data provider, skipping")
            return None

        try:
            data = self._data_provider()
            autosave_path = self._get_autosave_path()

            ProjectSerializer.save(data, autosave_path, update_modified=False)
            self._last_save_path = autosave_path
            logger.debug(f"[AutoSave] Saved to {autosave_path}")
            return autosave_path

        except Exception as e:
            logger.error(f"[AutoSave] Save failed: {e}")
            return None

    def _get_autosave_path(self) -> Path:
        """Get the auto-save file path."""
        if self._project_path is None:
            raise AutoSaveError("No project path set")

        return self._project_path.with_suffix(self._project_path.suffix + "~")

    @staticmethod
    def has_autosave(project_path: Path) -> bool:
        """Check if an auto-save file exists for the given project.

        Args:
            project_path: Path to the main project file.

        Returns:
            True if auto-save file exists and is newer than main file.
        """
        autosave_path = project_path.with_suffix(project_path.suffix + "~")

        if not autosave_path.exists():
            return False

        # Check if auto-save is newer than main file
        if project_path.exists():
            return autosave_path.stat().st_mtime > project_path.stat().st_mtime

        return True

    @staticmethod
    def load_autosave(project_path: Path) -> ProjectData | None:
        """Load project data from auto-save file.

        Args:
            project_path: Path to the main project file.

        Returns:
            ProjectData from auto-save, or None if not available.
        """
        autosave_path = project_path.with_suffix(project_path.suffix + "~")

        if not autosave_path.exists():
            return None

        try:
            return ProjectSerializer.load(autosave_path)
        except Exception as e:
            logger.error(f"[AutoSave] Failed to load auto-save: {e}")
            return None

    @staticmethod
    def remove_autosave(project_path: Path) -> None:
        """Remove the auto-save file for the given project.

        Args:
            project_path: Path to the main project file.
        """
        autosave_path = project_path.with_suffix(project_path.suffix + "~")

        if autosave_path.exists():
            try:
                autosave_path.unlink()
                logger.info(f"[AutoSave] Removed: {autosave_path}")
            except Exception as e:
                logger.error(f"[AutoSave] Failed to remove: {e}")
