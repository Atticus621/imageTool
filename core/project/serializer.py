"""Project serializer — handles JSON serialization and file I/O.

Provides save/load functionality for project files with proper
error handling and encoding support.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from core.logger import logger
from .errors import SerializationError
from .models import ProjectData, ProjectMetadata


class ProjectSerializer:
    """Handles project file serialization and deserialization."""

    CURRENT_VERSION = "1.0.0"

    @staticmethod
    def save(
        project_data: ProjectData,
        path: str | Path,
        update_modified: bool = True,
    ) -> None:
        """Save project data to a JSON file.

        Args:
            project_data: The project data to save.
            path: Target file path.
            update_modified: Whether to update modified_at timestamp.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if update_modified:
            project_data.metadata.modified_at = datetime.now().isoformat()

        data = project_data.to_dict()

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"[ProjectSerializer] Saved project to {path}")
        except Exception as e:
            raise SerializationError(f"Failed to save project: {e}") from e

    @staticmethod
    def load(path: str | Path) -> ProjectData:
        """Load project data from a JSON file.

        Args:
            path: Source file path.

        Returns:
            ProjectData instance.

        Raises:
            SerializationError: If file cannot be read or parsed.
        """
        path = Path(path)
        if not path.exists():
            raise SerializationError(f"Project file not found: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise SerializationError(f"Invalid JSON in project file: {e}") from e
        except Exception as e:
            raise SerializationError(f"Failed to read project file: {e}") from e

        try:
            return ProjectData.from_dict(data)
        except Exception as e:
            raise SerializationError(f"Failed to parse project data: {e}") from e

    @staticmethod
    def to_json_string(project_data: ProjectData) -> str:
        """Serialize project data to a JSON string.

        Args:
            project_data: The project data to serialize.

        Returns:
            JSON string representation.
        """
        data = project_data.to_dict()
        return json.dumps(data, indent=2, ensure_ascii=False)

    @staticmethod
    def from_json_string(json_str: str) -> ProjectData:
        """Deserialize project data from a JSON string.

        Args:
            json_str: JSON string to parse.

        Returns:
            ProjectData instance.
        """
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise SerializationError(f"Invalid JSON string: {e}") from e

        try:
            return ProjectData.from_dict(data)
        except Exception as e:
            raise SerializationError(f"Failed to parse project data: {e}") from e

    @staticmethod
    def get_version(path: str | Path) -> str | None:
        """Get the version from a project file without fully parsing it.

        Args:
            path: Path to the project file.

        Returns:
            Version string or None if file cannot be read.
        """
        path = Path(path)
        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("version")
        except Exception:
            return None
