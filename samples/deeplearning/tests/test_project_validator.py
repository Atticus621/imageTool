"""Tests for project validator."""

import pytest

from core.project import ProjectData, ProjectMetadata, NodeData, ConnectionData
from core.project.validator import ProjectValidator, ValidationResult


class TestProjectValidator:
    """Test ProjectValidator class."""

    def setup_method(self):
        self.validator = ProjectValidator()

    def test_valid_project(self):
        """Test validation of a valid project."""
        data = {
            "version": "1.0.0",
            "metadata": {
                "name": "Test Project",
                "created_at": "2026-07-04T12:00:00",
                "modified_at": "2026-07-04T13:00:00",
            },
            "nodes": [
                {
                    "id": "test/node",
                    "instance_id": "node_001",
                    "name": "Test Node",
                    "position": {"x": 100, "y": 200},
                    "param_values": {},
                },
            ],
            "connections": [
                {
                    "from_node": "node_001",
                    "from_port": "output",
                    "to_node": "node_002",
                    "to_port": "input",
                },
            ],
        }

        result = self.validator.validate(data)
        assert result.is_valid

    def test_missing_version(self):
        """Test validation with missing version."""
        data = {
            "metadata": {"name": "Test"},
            "nodes": [],
            "connections": [],
        }

        result = self.validator.validate(data)
        assert not result.is_valid
        assert any("version" in e.field for e in result.errors)

    def test_missing_metadata(self):
        """Test validation with missing metadata."""
        data = {
            "version": "1.0.0",
            "nodes": [],
            "connections": [],
        }

        result = self.validator.validate(data)
        assert not result.is_valid
        assert any("metadata" in e.field for e in result.errors)

    def test_missing_nodes(self):
        """Test validation with missing nodes array."""
        data = {
            "version": "1.0.0",
            "metadata": {"name": "Test"},
            "connections": [],
        }

        result = self.validator.validate(data)
        assert not result.is_valid
        assert any("nodes" in e.field for e in result.errors)

    def test_duplicate_instance_ids(self):
        """Test validation with duplicate instance IDs."""
        data = {
            "version": "1.0.0",
            "metadata": {"name": "Test"},
            "nodes": [
                {
                    "id": "test/node",
                    "instance_id": "same_id",
                    "name": "Node 1",
                },
                {
                    "id": "test/node",
                    "instance_id": "same_id",
                    "name": "Node 2",
                },
            ],
            "connections": [],
        }

        result = self.validator.validate(data)
        assert not result.is_valid
        assert any("Duplicate" in e.message for e in result.errors)

    def test_invalid_node_position(self):
        """Test validation with invalid node position."""
        data = {
            "version": "1.0.0",
            "metadata": {"name": "Test"},
            "nodes": [
                {
                    "id": "test/node",
                    "instance_id": "node_001",
                    "name": "Test",
                    "position": {"x": "not_a_number", "y": 200},
                },
            ],
            "connections": [],
        }

        result = self.validator.validate(data)
        assert not result.is_valid

    def test_connection_referencing_missing_node(self):
        """Test validation with connection referencing missing node."""
        data = {
            "version": "1.0.0",
            "metadata": {"name": "Test"},
            "nodes": [
                {
                    "id": "test/node",
                    "instance_id": "node_001",
                    "name": "Test",
                },
            ],
            "connections": [
                {
                    "from_node": "node_001",
                    "from_port": "output",
                    "to_node": "nonexistent_node",
                    "to_port": "input",
                },
            ],
        }

        result = self.validator.validate(data)
        # Should have a warning about missing node reference
        assert any("not found" in w.message for w in result.warnings)

    def test_invalid_connection_missing_field(self):
        """Test validation with invalid connection missing fields."""
        data = {
            "version": "1.0.0",
            "metadata": {"name": "Test"},
            "nodes": [],
            "connections": [
                {
                    "from_node": "node_001",
                    # Missing from_port, to_node, to_port
                },
            ],
        }

        result = self.validator.validate(data)
        assert not result.is_valid

    def test_empty_project(self):
        """Test validation of an empty but valid project."""
        data = {
            "version": "1.0.0",
            "metadata": {"name": "Empty Project"},
            "nodes": [],
            "connections": [],
        }

        result = self.validator.validate(data)
        assert result.is_valid

    def test_not_a_dict(self):
        """Test validation with non-dict input."""
        result = self.validator.validate("not a dict")
        assert not result.is_valid


class TestValidationResult:
    """Test ValidationResult class."""

    def test_initial_state(self):
        """Test initial validation result state."""
        result = ValidationResult()
        assert result.is_valid
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_add_error(self):
        """Test adding an error."""
        result = ValidationResult()
        result.add_error("field", "error message")

        assert not result.is_valid
        assert len(result.errors) == 1
        assert result.errors[0].field == "field"
        assert result.errors[0].message == "error message"

    def test_add_warning(self):
        """Test adding a warning."""
        result = ValidationResult()
        result.add_warning("field", "warning message")

        assert result.is_valid  # Warnings don't make it invalid
        assert len(result.warnings) == 1

    def test_str_valid(self):
        """Test string representation of valid result."""
        result = ValidationResult()
        result.add_warning("field", "warning")

        assert "passed" in str(result)
        assert "1 warnings" in str(result)

    def test_str_invalid(self):
        """Test string representation of invalid result."""
        result = ValidationResult()
        result.add_error("field", "error")
        result.add_warning("field", "warning")

        assert "failed" in str(result)
        assert "1 errors" in str(result)
        assert "1 warnings" in str(result)
