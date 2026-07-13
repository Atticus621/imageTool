"""Tests for project serializer."""

import json
import tempfile
from pathlib import Path

import pytest

from core.project import (
    ConnectionData,
    ExecutionConfig,
    NodeData,
    NodePosition,
    ProjectData,
    ProjectMetadata,
    ProjectSerializer,
    ROISerializedData,
)


class TestProjectSerializer:
    """Test ProjectSerializer class."""

    def test_serialize_deserialize_roundtrip(self):
        """Test that serialization and deserialization are inverse operations."""
        project = ProjectData(
            version="1.0.0",
            metadata=ProjectMetadata(
                name="Test Project",
                description="A test project",
                author="Test Author",
                tags=["test", "example"],
            ),
            nodes=[
                NodeData(
                    id="image_source/input_image_set",
                    instance_id="node_001",
                    name="图集",
                    position=NodePosition(x=100.0, y=200.0),
                    param_values={"file_list": ["/path/to/image.jpg"]},
                ),
                NodeData(
                    id="detection/yolo/yolo_detect",
                    instance_id="node_002",
                    name="YOLO检测",
                    position=NodePosition(x=400.0, y=200.0),
                    param_values={"confidence": 0.5},
                ),
            ],
            connections=[
                ConnectionData(
                    from_node="node_001",
                    from_port="images",
                    to_node="node_002",
                    to_port="images",
                ),
            ],
            execution_config=ExecutionConfig(loop_mode=False, auto_execute=False),
        )

        # Serialize
        data = project.to_dict()

        # Deserialize
        restored = ProjectData.from_dict(data)

        # Verify
        assert restored.version == project.version
        assert restored.metadata.name == project.metadata.name
        assert restored.metadata.description == project.metadata.description
        assert restored.metadata.author == project.metadata.author
        assert restored.metadata.tags == project.metadata.tags
        assert len(restored.nodes) == len(project.nodes)
        assert len(restored.connections) == len(project.connections)

    def test_save_load_roundtrip(self, tmp_path):
        """Test save and load roundtrip with file I/O."""
        project = ProjectData(
            metadata=ProjectMetadata(name="File Test"),
            nodes=[
                NodeData(
                    id="test/node",
                    instance_id="test_001",
                    name="Test Node",
                ),
            ],
        )

        file_path = tmp_path / "test.itproj"

        # Save
        ProjectSerializer.save(project, file_path)
        assert file_path.exists()

        # Load
        loaded = ProjectSerializer.load(file_path)

        # Verify
        assert loaded.metadata.name == "File Test"
        assert len(loaded.nodes) == 1
        assert loaded.nodes[0].id == "test/node"

    def test_to_json_string(self):
        """Test JSON string serialization."""
        project = ProjectData(
            metadata=ProjectMetadata(name="JSON Test"),
        )

        json_str = ProjectSerializer.to_json_string(project)

        # Should be valid JSON
        data = json.loads(json_str)
        assert data["metadata"]["name"] == "JSON Test"

    def test_from_json_string(self):
        """Test JSON string deserialization."""
        json_str = json.dumps({
            "version": "1.0.0",
            "metadata": {"name": "From JSON"},
            "nodes": [],
            "connections": [],
        })

        project = ProjectSerializer.from_json_string(json_str)

        assert project.metadata.name == "From JSON"
        assert len(project.nodes) == 0

    def test_get_version(self, tmp_path):
        """Test getting version without full parse."""
        project = ProjectData(version="1.2.3")
        file_path = tmp_path / "version_test.itproj"

        ProjectSerializer.save(project, file_path)

        version = ProjectSerializer.get_version(file_path)
        assert version == "1.2.3"

    def test_get_version_nonexistent(self, tmp_path):
        """Test getting version from nonexistent file."""
        file_path = tmp_path / "nonexistent.itproj"
        version = ProjectSerializer.get_version(file_path)
        assert version is None

    def test_save_creates_parent_dirs(self, tmp_path):
        """Test that save creates parent directories."""
        project = ProjectData(metadata=ProjectMetadata(name="Dir Test"))
        file_path = tmp_path / "subdir" / "nested" / "test.itproj"

        ProjectSerializer.save(project, file_path)
        assert file_path.exists()

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading nonexistent file raises error."""
        from core.project.errors import SerializationError

        file_path = tmp_path / "nonexistent.itproj"
        with pytest.raises(SerializationError):
            ProjectSerializer.load(file_path)

    def test_load_invalid_json(self, tmp_path):
        """Test loading invalid JSON raises error."""
        from core.project.errors import SerializationError

        file_path = tmp_path / "invalid.itproj"
        file_path.write_text("not valid json {{{")

        with pytest.raises(SerializationError):
            ProjectSerializer.load(file_path)


class TestProjectMetadata:
    """Test ProjectMetadata model."""

    def test_default_values(self):
        """Test default metadata values."""
        meta = ProjectMetadata()
        assert meta.name == "未命名项目"
        assert meta.description == ""
        assert meta.author == ""
        assert meta.tags == []
        assert meta.created_at != ""  # Should be set
        assert meta.modified_at != ""  # Should be set

    def test_to_dict(self):
        """Test metadata to dict conversion."""
        meta = ProjectMetadata(name="Test", tags=["a", "b"])
        d = meta.to_dict()

        assert d["name"] == "Test"
        assert d["tags"] == ["a", "b"]

    def test_from_dict(self):
        """Test metadata from dict creation."""
        d = {
            "name": "From Dict",
            "description": "Test description",
            "author": "Author",
            "tags": ["tag1"],
        }
        meta = ProjectMetadata.from_dict(d)

        assert meta.name == "From Dict"
        assert meta.description == "Test description"
        assert meta.author == "Author"
        assert meta.tags == ["tag1"]


class TestNodeData:
    """Test NodeData model."""

    def test_to_dict(self):
        """Test node to dict conversion."""
        node = NodeData(
            id="test/node",
            instance_id="node_001",
            name="Test",
            position=NodePosition(x=10.0, y=20.0),
            param_values={"key": "value"},
        )
        d = node.to_dict()

        assert d["id"] == "test/node"
        assert d["instance_id"] == "node_001"
        assert d["position"]["x"] == 10.0
        assert d["param_values"]["key"] == "value"

    def test_from_dict(self):
        """Test node from dict creation."""
        d = {
            "id": "test/node",
            "instance_id": "node_001",
            "name": "Test",
            "position": {"x": 10.0, "y": 20.0},
            "param_values": {"key": "value"},
        }
        node = NodeData.from_dict(d)

        assert node.id == "test/node"
        assert node.position.x == 10.0
        assert node.param_values["key"] == "value"


class TestConnectionData:
    """Test ConnectionData model."""

    def test_roundtrip(self):
        """Test connection serialization roundtrip."""
        conn = ConnectionData(
            from_node="node_001",
            from_port="output",
            to_node="node_002",
            to_port="input",
        )

        d = conn.to_dict()
        restored = ConnectionData.from_dict(d)

        assert restored.from_node == "node_001"
        assert restored.from_port == "output"
        assert restored.to_node == "node_002"
        assert restored.to_port == "input"
