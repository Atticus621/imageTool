"""Project template manager — handles built-in and user templates.

Provides functionality to save projects as templates and create
new projects from templates. Templates are stored as .itproj files
with additional metadata.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from core.logger import logger
from .errors import TemplateError
from .models import ProjectData
from .serializer import ProjectSerializer


@dataclass
class TemplateInfo:
    """Information about a project template."""

    id: str = ""
    name: str = ""
    description: str = ""
    author: str = ""
    created_at: str = ""
    is_builtin: bool = False
    file_path: Path = field(default_factory=Path)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "created_at": self.created_at,
            "is_builtin": self.is_builtin,
        }


class TemplateManager:
    """Manages project templates.

    Templates are stored in two locations:
    - Built-in: config/templates/
    - User: ~/.imagetools/templates/
    """

    BUILTIN_DIR = "config/templates"
    USER_DIR_NAME = ".imagetools/templates"

    def __init__(self, root_dir: Path):
        """Initialize template manager.

        Args:
            root_dir: Application root directory.
        """
        self._root_dir = root_dir
        self._builtin_dir = root_dir / self.BUILTIN_DIR
        self._user_dir = Path.home() / self.USER_DIR_NAME

        # Ensure directories exist
        self._builtin_dir.mkdir(parents=True, exist_ok=True)
        self._user_dir.mkdir(parents=True, exist_ok=True)

    def list_templates(self) -> list[TemplateInfo]:
        """List all available templates.

        Returns:
            List of TemplateInfo for all templates.
        """
        templates = []

        # Built-in templates
        templates.extend(self._scan_directory(self._builtin_dir, is_builtin=True))

        # User templates
        templates.extend(self._scan_directory(self._user_dir, is_builtin=False))

        return templates

    def get_template(self, template_id: str) -> ProjectData | None:
        """Load a template by ID.

        Args:
            template_id: Template identifier.

        Returns:
            ProjectData or None if not found.
        """
        templates = self.list_templates()
        for info in templates:
            if info.id == template_id:
                return self._load_template_file(info.file_path)
        return None

    def save_as_template(
        self,
        project_data: ProjectData,
        name: str,
        description: str = "",
        author: str = "",
    ) -> TemplateInfo:
        """Save project data as a new template.

        Args:
            project_data: Project data to save as template.
            name: Template name.
            description: Template description.
            author: Template author.

        Returns:
            TemplateInfo for the created template.
        """
        # Generate template ID from name
        template_id = self._generate_id(name)
        file_path = self._user_dir / f"{template_id}.itproj"

        # Update metadata
        project_data.metadata.name = name
        project_data.metadata.description = description
        project_data.metadata.author = author
        project_data.metadata.modified_at = datetime.now().isoformat()

        # Save template file
        try:
            ProjectSerializer.save(project_data, file_path)
            logger.info(f"[TemplateManager] Saved template: {name}")
        except Exception as e:
            raise TemplateError(f"Failed to save template: {e}") from e

        return TemplateInfo(
            id=template_id,
            name=name,
            description=description,
            author=author,
            created_at=datetime.now().isoformat(),
            is_builtin=False,
            file_path=file_path,
        )

    def delete_template(self, template_id: str) -> bool:
        """Delete a user template.

        Args:
            template_id: Template identifier.

        Returns:
            True if deleted, False if not found or is built-in.
        """
        # Only allow deleting user templates
        file_path = self._user_dir / f"{template_id}.itproj"
        if not file_path.exists():
            return False

        try:
            file_path.unlink()
            logger.info(f"[TemplateManager] Deleted template: {template_id}")
            return True
        except Exception as e:
            logger.error(f"[TemplateManager] Failed to delete template: {e}")
            return False

    def _scan_directory(
        self, directory: Path, is_builtin: bool
    ) -> list[TemplateInfo]:
        """Scan a directory for template files."""
        templates = []

        if not directory.exists():
            return templates

        for file_path in directory.glob("*.itproj"):
            try:
                info = self._read_template_info(file_path, is_builtin)
                if info:
                    templates.append(info)
            except Exception as e:
                logger.warning(f"[TemplateManager] Failed to read {file_path}: {e}")

        return templates

    def _read_template_info(
        self, file_path: Path, is_builtin: bool
    ) -> TemplateInfo | None:
        """Read template info from a file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            metadata = data.get("metadata", {})
            template_id = file_path.stem

            return TemplateInfo(
                id=template_id,
                name=metadata.get("name", template_id),
                description=metadata.get("description", ""),
                author=metadata.get("author", ""),
                created_at=metadata.get("created_at", ""),
                is_builtin=is_builtin,
                file_path=file_path,
            )
        except Exception:
            return None

    def _load_template_file(self, file_path: Path) -> ProjectData | None:
        """Load project data from a template file."""
        try:
            return ProjectSerializer.load(file_path)
        except Exception as e:
            logger.error(f"[TemplateManager] Failed to load template: {e}")
            return None

    def _generate_id(self, name: str) -> str:
        """Generate a template ID from a name."""
        # Simple ID generation: lowercase, replace spaces with underscores
        template_id = name.lower().replace(" ", "_")
        # Add timestamp to ensure uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{template_id}_{timestamp}"
