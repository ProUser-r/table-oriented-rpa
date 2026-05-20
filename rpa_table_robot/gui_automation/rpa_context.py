"""Workflow context and state management."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rpa_table_robot.models import RobotResult


@dataclass
class WorkflowContext:
    """Context for workflow execution."""

    workflow_name: str
    variables: dict[str, Any] = field(default_factory=dict)
    step_results: dict[str, Any] = field(default_factory=dict)
    robot_result: RobotResult | None = None
    screenshots: list[Path] = field(default_factory=list)
    current_step_id: str | None = None
    current_step_name: str | None = None

    def set_variable(self, key: str, value: Any) -> None:
        """Set a variable in context."""
        self.variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a variable from context."""
        return self.variables.get(key, default)

    def set_step_result(self, step_id: str, result: Any) -> None:
        """Store result of a step."""
        self.step_results[step_id] = result

    def get_step_result(self, step_id: str, default: Any = None) -> Any:
        """Get result of a previous step."""
        return self.step_results.get(step_id, default)

    def add_screenshot(self, path: Path) -> None:
        """Add screenshot to context."""
        self.screenshots.append(path)
