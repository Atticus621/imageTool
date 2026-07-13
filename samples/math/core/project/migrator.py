"""Project migrator — handles version migration.

Provides automatic migration from older project file versions
to the current version. Supports chain migration through
intermediate versions.
"""

from __future__ import annotations

from typing import Callable

from core.logger import logger
from .errors import MigrationError, VersionError


# Type for migration functions
MigrationFunc = Callable[[dict], dict]


class ProjectMigrator:
    """Manages project file version migrations.

    Migration functions transform project data dicts in-place.
    Each function should:
    1. Update any changed field names or structures
    2. Add new fields with defaults
    3. Remove deprecated fields
    4. Update the version field to the target version
    """

    def __init__(self):
        self._migrations: dict[str, MigrationFunc] = {}
        self._versions: list[str] = []
        self._register_builtin_migrations()

    def _register_builtin_migrations(self) -> None:
        """Register built-in migration functions."""
        # 1.0.0 is the initial version, no migration needed yet
        # Register future migrations here:
        # self.register("1.0.0", "1.1.0", self._migrate_1_0_0_to_1_1_0)
        # self.register("1.1.0", "2.0.0", self._migrate_1_1_0_to_2_0_0)
        pass

    def register(
        self, from_version: str, to_version: str, func: MigrationFunc
    ) -> None:
        """Register a migration function.

        Args:
            from_version: Source version.
            to_version: Target version.
            func: Migration function that transforms data dict.
        """
        key = f"{from_version}->{to_version}"
        self._migrations[key] = func

        if from_version not in self._versions:
            self._versions.append(from_version)
        if to_version not in self._versions:
            self._versions.append(to_version)

        logger.info(f"[ProjectMigrator] Registered migration: {key}")

    def migrate(self, data: dict, target_version: str) -> dict:
        """Migrate project data to the target version.

        Finds the shortest migration path and applies migrations
        in sequence.

        Args:
            data: Project data dict.
            target_version: Target version to migrate to.

        Returns:
            Migrated project data dict.

        Raises:
            MigrationError: If migration fails.
            VersionError: If no migration path exists.
        """
        current_version = data.get("version", "1.0.0")

        if current_version == target_version:
            return data

        path = self._find_migration_path(current_version, target_version)
        if not path:
            raise VersionError(
                f"No migration path from {current_version} to {target_version}"
            )

        for from_ver, to_ver in path:
            key = f"{from_ver}->{to_ver}"
            func = self._migrations.get(key)
            if func is None:
                raise MigrationError(f"Migration function not found: {key}")

            try:
                logger.info(f"[ProjectMigrator] Migrating: {key}")
                data = func(data)
                data["version"] = to_ver
            except Exception as e:
                raise MigrationError(
                    f"Migration {key} failed: {e}"
                ) from e

        logger.info(
            f"[ProjectMigrator] Migration complete: {current_version} -> {target_version}"
        )
        return data

    def _find_migration_path(
        self, from_version: str, to_version: str
    ) -> list[tuple[str, str]] | None:
        """Find migration path using BFS.

        Returns:
            List of (from, to) version pairs, or None if no path exists.
        """
        from packaging.version import Version

        # Build graph of available migrations
        graph: dict[str, list[str]] = {}
        for key in self._migrations:
            src, dst = key.split("->")
            graph.setdefault(src, []).append(dst)

        # BFS to find shortest path
        queue = [(from_version, [])]
        visited = {from_version}

        while queue:
            current, path = queue.pop(0)

            if current == to_version:
                return path

            for next_ver in graph.get(current, []):
                if next_ver not in visited:
                    visited.add(next_ver)
                    new_path = path + [(current, next_ver)]
                    queue.append((next_ver, new_path))

        return None

    def get_latest_version(self) -> str:
        """Get the latest known version."""
        if not self._versions:
            return "1.0.0"

        from packaging.version import Version

        return max(self._versions, key=lambda v: Version(v))

    def needs_migration(self, data: dict, target_version: str) -> bool:
        """Check if project data needs migration.

        Args:
            data: Project data dict.
            target_version: Target version.

        Returns:
            True if migration is needed.
        """
        current_version = data.get("version", "1.0.0")
        return current_version != target_version


# Singleton instance
project_migrator = ProjectMigrator()
