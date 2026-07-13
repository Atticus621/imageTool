"""Project validator — validates project data structure and content.

Provides strict validation of project data before loading,
ensuring all required fields are present and values are valid.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.logger import logger
from .errors import ValidationError


@dataclass
class ValidationIssue:
    """A single validation issue."""

    level: str = "error"  # "error", "warning", "info"
    field: str = ""
    message: str = ""

    def __str__(self) -> str:
        prefix = self.level.upper()
        if self.field:
            return f"[{prefix}] {self.field}: {self.message}"
        return f"[{prefix}] {self.message}"


@dataclass
class ValidationResult:
    """Result of project validation."""

    is_valid: bool = True
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == "warning"]

    def add_error(self, field: str, message: str) -> None:
        self.issues.append(ValidationIssue("error", field, message))
        self.is_valid = False

    def add_warning(self, field: str, message: str) -> None:
        self.issues.append(ValidationIssue("warning", field, message))

    def add_info(self, field: str, message: str) -> None:
        self.issues.append(ValidationIssue("info", field, message))

    def __str__(self) -> str:
        if self.is_valid:
            return f"Validation passed ({len(self.warnings)} warnings)"
        return f"Validation failed ({len(self.errors)} errors, {len(self.warnings)} warnings)"


class ProjectValidator:
    """Validates project data structure and content."""

    REQUIRED_TOP_LEVEL = ["version", "metadata", "nodes", "connections"]
    REQUIRED_METADATA = ["name", "created_at", "modified_at"]
    VALID_NODE_FIELDS = [
        "id", "instance_id", "name", "position",
        "param_values", "optional_port_states", "is_placeholder",
    ]
    VALID_CONNECTION_FIELDS = ["from_node", "from_port", "to_node", "to_port"]

    def validate(self, data: dict) -> ValidationResult:
        """Validate project data dict.

        Args:
            data: Project data dict to validate.

        Returns:
            ValidationResult with any issues found.
        """
        result = ValidationResult()

        if not isinstance(data, dict):
            result.add_error("root", "Project data must be a dictionary")
            return result

        self._validate_top_level(data, result)
        self._validate_metadata(data.get("metadata"), result)
        self._validate_nodes(data.get("nodes", []), result)
        self._validate_connections(data.get("connections", []), result)
        self._validate_rois(data.get("rois", []), result)
        self._validate_execution_config(data.get("execution_config"), result)
        self._validate_node_references(data, result)

        logger.debug(f"[ProjectValidator] {result}")
        return result

    def _validate_top_level(self, data: dict, result: ValidationResult) -> None:
        """Validate top-level required fields."""
        for field in self.REQUIRED_TOP_LEVEL:
            if field not in data:
                result.add_error(field, f"Required field missing: {field}")

        version = data.get("version")
        if version and not isinstance(version, str):
            result.add_error("version", "Version must be a string")

    def _validate_metadata(
        self, metadata: Any, result: ValidationResult
    ) -> None:
        """Validate metadata section."""
        if metadata is None:
            result.add_error("metadata", "Metadata section is missing")
            return

        if not isinstance(metadata, dict):
            result.add_error("metadata", "Metadata must be a dictionary")
            return

        for field in self.REQUIRED_METADATA:
            if field not in metadata:
                result.add_warning(f"metadata.{field}", f"Recommended field missing: {field}")

        name = metadata.get("name")
        if name is not None and not isinstance(name, str):
            result.add_error("metadata.name", "Name must be a string")

        tags = metadata.get("tags")
        if tags is not None:
            if not isinstance(tags, list):
                result.add_error("metadata.tags", "Tags must be a list")
            elif not all(isinstance(t, str) for t in tags):
                result.add_error("metadata.tags", "All tags must be strings")

    def _validate_nodes(self, nodes: Any, result: ValidationResult) -> None:
        """Validate nodes array."""
        if not isinstance(nodes, list):
            result.add_error("nodes", "Nodes must be an array")
            return

        instance_ids = set()
        for i, node in enumerate(nodes):
            prefix = f"nodes[{i}]"

            if not isinstance(node, dict):
                result.add_error(prefix, "Node must be a dictionary")
                continue

            # Required fields
            if "id" not in node:
                result.add_error(f"{prefix}.id", "Node ID is required")
            elif not isinstance(node["id"], str):
                result.add_error(f"{prefix}.id", "Node ID must be a string")

            if "instance_id" not in node:
                result.add_error(f"{prefix}.instance_id", "Instance ID is required")
            elif not isinstance(node["instance_id"], str):
                result.add_error(f"{prefix}.instance_id", "Instance ID must be a string")
            elif node["instance_id"] in instance_ids:
                result.add_error(
                    f"{prefix}.instance_id",
                    f"Duplicate instance ID: {node['instance_id']}"
                )
            else:
                instance_ids.add(node["instance_id"])

            # Validate position
            position = node.get("position")
            if position is not None:
                if not isinstance(position, dict):
                    result.add_error(f"{prefix}.position", "Position must be a dictionary")
                else:
                    for coord in ["x", "y"]:
                        val = position.get(coord)
                        if val is not None and not isinstance(val, (int, float)):
                            result.add_error(
                                f"{prefix}.position.{coord}",
                                f"Position {coord} must be a number"
                            )

            # Validate param_values
            params = node.get("param_values")
            if params is not None and not isinstance(params, dict):
                result.add_error(f"{prefix}.param_values", "Param values must be a dictionary")

    def _validate_connections(
        self, connections: Any, result: ValidationResult
    ) -> None:
        """Validate connections array."""
        if not isinstance(connections, list):
            result.add_error("connections", "Connections must be an array")
            return

        for i, conn in enumerate(connections):
            prefix = f"connections[{i}]"

            if not isinstance(conn, dict):
                result.add_error(prefix, "Connection must be a dictionary")
                continue

            for field in self.VALID_CONNECTION_FIELDS:
                if field not in conn:
                    result.add_error(f"{prefix}.{field}", f"Required field missing: {field}")
                elif not isinstance(conn[field], str):
                    result.add_error(f"{prefix}.{field}", f"{field} must be a string")

    def _validate_rois(self, rois: Any, result: ValidationResult) -> None:
        """Validate ROIs array."""
        if not isinstance(rois, list):
            result.add_error("rois", "ROIs must be an array")
            return

        for i, roi in enumerate(rois):
            prefix = f"rois[{i}]"

            if not isinstance(roi, dict):
                result.add_error(prefix, "ROI must be a dictionary")
                continue

            if "node_id" not in roi:
                result.add_error(f"{prefix}.node_id", "ROI node_id is required")

            if "roi_type" not in roi:
                result.add_error(f"{prefix}.roi_type", "ROI type is required")

    def _validate_execution_config(
        self, config: Any, result: ValidationResult
    ) -> None:
        """Validate execution config section."""
        if config is None:
            result.add_info("execution_config", "Execution config not specified, using defaults")
            return

        if not isinstance(config, dict):
            result.add_error("execution_config", "Execution config must be a dictionary")
            return

        loop_mode = config.get("loop_mode")
        if loop_mode is not None and not isinstance(loop_mode, bool):
            result.add_error("execution_config.loop_mode", "loop_mode must be a boolean")

        auto_execute = config.get("auto_execute")
        if auto_execute is not None and not isinstance(auto_execute, bool):
            result.add_error("execution_config.auto_execute", "auto_execute must be a boolean")

    def _validate_node_references(self, data: dict, result: ValidationResult) -> None:
        """Validate that connections reference existing nodes."""
        nodes = data.get("nodes", [])
        connections = data.get("connections", [])

        instance_ids = {n.get("instance_id") for n in nodes if isinstance(n, dict)}

        for i, conn in enumerate(connections):
            if not isinstance(conn, dict):
                continue

            from_node = conn.get("from_node")
            to_node = conn.get("to_node")

            if from_node and from_node not in instance_ids:
                result.add_warning(
                    f"connections[{i}].from_node",
                    f"Referenced node not found: {from_node}"
                )

            if to_node and to_node not in instance_ids:
                result.add_warning(
                    f"connections[{i}].to_node",
                    f"Referenced node not found: {to_node}"
                )


# Singleton instance
project_validator = ProjectValidator()
