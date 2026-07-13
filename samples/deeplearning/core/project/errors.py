"""Project file system error definitions."""


class ProjectError(Exception):
    """Base exception for project file operations."""
    pass


class ValidationError(ProjectError):
    """Raised when project data validation fails."""
    pass


class MigrationError(ProjectError):
    """Raised when project migration fails."""
    pass


class VersionError(ProjectError):
    """Raised when version is incompatible or unknown."""
    pass


class SerializationError(ProjectError):
    """Raised when serialization/deserialization fails."""
    pass


class AutoSaveError(ProjectError):
    """Raised when auto-save operations fail."""
    pass


class TemplateError(ProjectError):
    """Raised when template operations fail."""
    pass
