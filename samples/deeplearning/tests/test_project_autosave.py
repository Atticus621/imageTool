"""Tests for project auto-save manager."""

import time
from pathlib import Path

import pytest

from core.project import ProjectData, ProjectMetadata, ProjectSerializer
from core.project.autosave import AutoSaveManager


class TestAutoSaveManager:
    """Test AutoSaveManager class."""

    def setup_method(self):
        self.manager = AutoSaveManager()

    def test_initial_state(self):
        """Test initial manager state."""
        assert not self.manager.is_running
        assert self.manager.interval_ms == 60000
        assert self.manager.last_save_path is None

    def test_set_interval(self):
        """Test setting interval."""
        self.manager.set_interval(30)
        assert self.manager.interval_ms == 30000

    def test_set_interval_minimum(self):
        """Test that interval has a minimum value."""
        self.manager.set_interval(5)  # Below minimum
        assert self.manager.interval_ms == 10000  # Should be clamped to 10s

    def test_set_project_path(self, tmp_path):
        """Test setting project path."""
        path = tmp_path / "test.itproj"
        self.manager.set_project_path(path)
        # No assertion needed, just checking it doesn't raise

    def test_save_now_no_path(self):
        """Test save_now with no path set."""
        result = self.manager.save_now()
        assert result is None

    def test_save_now_no_provider(self, tmp_path):
        """Test save_now with no data provider."""
        path = tmp_path / "test.itproj"
        self.manager.set_project_path(path)

        result = self.manager.save_now()
        assert result is None

    def test_save_now_success(self, tmp_path):
        """Test successful save_now."""
        project = ProjectData(metadata=ProjectMetadata(name="Auto-save Test"))
        path = tmp_path / "test.itproj"

        self.manager.set_project_path(path)
        self.manager.set_data_provider(lambda: project)

        result = self.manager.save_now()

        assert result is not None
        assert result.exists()
        assert result.name == "test.itproj~"

    def test_has_autosave(self, tmp_path):
        """Test has_autosave check."""
        project = ProjectData(metadata=ProjectMetadata(name="Test"))
        path = tmp_path / "test.itproj"
        autosave_path = tmp_path / "test.itproj~"

        # No autosave file
        assert AutoSaveManager.has_autosave(path) is False

        # Create autosave file
        ProjectSerializer.save(project, autosave_path)

        # Autosave exists, main doesn't
        assert AutoSaveManager.has_autosave(path) is True

        # Create main file (newer)
        time.sleep(0.1)
        ProjectSerializer.save(project, path)

        # Main is newer than autosave
        assert AutoSaveManager.has_autosave(path) is False

        # Make autosave newer
        time.sleep(0.1)
        ProjectSerializer.save(project, autosave_path)

        # Autosave is newer
        assert AutoSaveManager.has_autosave(path) is True

    def test_load_autosave(self, tmp_path):
        """Test loading autosave file."""
        project = ProjectData(metadata=ProjectMetadata(name="Loaded"))
        path = tmp_path / "test.itproj"
        autosave_path = tmp_path / "test.itproj~"

        # No autosave file
        result = AutoSaveManager.load_autosave(path)
        assert result is None

        # Create autosave file
        ProjectSerializer.save(project, autosave_path)

        # Load autosave
        result = AutoSaveManager.load_autosave(path)
        assert result is not None
        assert result.metadata.name == "Loaded"

    def test_remove_autosave(self, tmp_path):
        """Test removing autosave file."""
        project = ProjectData(metadata=ProjectMetadata(name="Test"))
        path = tmp_path / "test.itproj"
        autosave_path = tmp_path / "test.itproj~"

        # Create autosave file
        ProjectSerializer.save(project, autosave_path)
        assert autosave_path.exists()

        # Remove autosave
        AutoSaveManager.remove_autosave(path)
        assert not autosave_path.exists()

    def test_remove_autosave_nonexistent(self, tmp_path):
        """Test removing nonexistent autosave file."""
        path = tmp_path / "nonexistent.itproj"

        # Should not raise
        AutoSaveManager.remove_autosave(path)

    def test_enable_disable(self):
        """Test enable/disable functionality."""
        self.manager.disable()
        assert not self.manager.is_running

        self.manager.enable()
        # Still not running because no path/provider set
        assert not self.manager.is_running
