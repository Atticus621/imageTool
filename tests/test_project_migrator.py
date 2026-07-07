"""Tests for project migrator."""

import pytest

from core.project.migrator import ProjectMigrator
from core.project.errors import MigrationError, VersionError


class TestProjectMigrator:
    """Test ProjectMigrator class."""

    def setup_method(self):
        self.migrator = ProjectMigrator()

    def test_no_migration_needed(self):
        """Test that same version returns data unchanged."""
        data = {"version": "1.0.0", "metadata": {}}
        result = self.migrator.migrate(data, "1.0.0")
        assert result is data

    def test_simple_migration(self):
        """Test simple version migration."""
        def migrate_1_0_to_1_1(data):
            data["new_field"] = "added"
            return data

        self.migrator.register("1.0.0", "1.1.0", migrate_1_0_to_1_1)

        data = {"version": "1.0.0", "metadata": {}}
        result = self.migrator.migrate(data, "1.1.0")

        assert result["version"] == "1.1.0"
        assert result["new_field"] == "added"

    def test_chain_migration(self):
        """Test chain migration through multiple versions."""
        def migrate_1_0_to_1_1(data):
            data["field_1_1"] = True
            return data

        def migrate_1_1_to_2_0(data):
            data["field_2_0"] = True
            return data

        self.migrator.register("1.0.0", "1.1.0", migrate_1_0_to_1_1)
        self.migrator.register("1.1.0", "2.0.0", migrate_1_1_to_2_0)

        data = {"version": "1.0.0", "metadata": {}}
        result = self.migrator.migrate(data, "2.0.0")

        assert result["version"] == "2.0.0"
        assert result["field_1_1"] is True
        assert result["field_2_0"] is True

    def test_no_migration_path(self):
        """Test error when no migration path exists."""
        data = {"version": "1.0.0", "metadata": {}}

        with pytest.raises(VersionError):
            self.migrator.migrate(data, "3.0.0")

    def test_migration_failure(self):
        """Test error when migration function fails."""
        def bad_migration(data):
            raise ValueError("Migration failed")

        self.migrator.register("1.0.0", "1.1.0", bad_migration)

        data = {"version": "1.0.0", "metadata": {}}

        with pytest.raises(MigrationError):
            self.migrator.migrate(data, "1.1.0")

    def test_needs_migration(self):
        """Test needs_migration check."""
        data = {"version": "1.0.0"}

        assert self.migrator.needs_migration(data, "1.1.0") is True
        assert self.migrator.needs_migration(data, "1.0.0") is False

    def test_get_latest_version(self):
        """Test getting latest version."""
        self.migrator.register("1.0.0", "1.1.0", lambda d: d)
        self.migrator.register("1.1.0", "2.0.0", lambda d: d)

        latest = self.migrator.get_latest_version()
        assert latest == "2.0.0"

    def test_get_latest_version_no_migrations(self):
        """Test getting latest version when no migrations registered."""
        latest = self.migrator.get_latest_version()
        assert latest == "1.0.0"

    def test_register_multiple_migrations(self):
        """Test registering multiple migration paths."""
        self.migrator.register("1.0.0", "1.1.0", lambda d: d)
        self.migrator.register("1.1.0", "1.2.0", lambda d: d)
        self.migrator.register("1.2.0", "2.0.0", lambda d: d)

        data = {"version": "1.0.0"}
        result = self.migrator.migrate(data, "2.0.0")
        assert result["version"] == "2.0.0"

    def test_migration_preserves_data(self):
        """Test that migration preserves existing data."""
        def add_field(data):
            data["added"] = True
            return data

        self.migrator.register("1.0.0", "1.1.0", add_field)

        data = {
            "version": "1.0.0",
            "metadata": {"name": "Test"},
            "nodes": [{"id": "node1"}],
        }
        result = self.migrator.migrate(data, "1.1.0")

        assert result["metadata"]["name"] == "Test"
        assert len(result["nodes"]) == 1
        assert result["added"] is True
