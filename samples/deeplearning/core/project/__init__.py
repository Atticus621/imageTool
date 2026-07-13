"""Core project file system module.

Provides project file serialization, deserialization, version migration,
validation, auto-save, and template management.
"""

from .autosave import AutoSaveManager
from .errors import (
    AutoSaveError,
    MigrationError,
    ProjectError,
    SerializationError,
    TemplateError,
    ValidationError,
    VersionError,
)
from .models import (
    ConnectionData,
    ExecutionConfig,
    NodeData,
    NodePosition,
    ProjectData,
    ProjectMetadata,
    ROISerializedData,
)
from .migrator import ProjectMigrator, project_migrator
from .serializer import ProjectSerializer
from .templates import TemplateInfo, TemplateManager
from .validator import ProjectValidator, ValidationResult, project_validator

__all__ = [
    # Errors
    "ProjectError",
    "ValidationError",
    "MigrationError",
    "VersionError",
    "SerializationError",
    "AutoSaveError",
    "TemplateError",
    # Models
    "ProjectData",
    "ProjectMetadata",
    "NodeData",
    "NodePosition",
    "ConnectionData",
    "ROISerializedData",
    "ExecutionConfig",
    # Core classes
    "ProjectSerializer",
    "ProjectMigrator",
    "ProjectValidator",
    "AutoSaveManager",
    "TemplateManager",
    "TemplateInfo",
    "ValidationResult",
    # Singletons
    "project_migrator",
    "project_validator",
]
