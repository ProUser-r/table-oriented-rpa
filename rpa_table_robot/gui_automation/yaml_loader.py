"""YAML workflow loading and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

from rpa_table_robot.gui_automation.exceptions import ValidationError, WorkflowError


class WorkflowStepParams(BaseModel):
    """Parameters for a workflow step."""

    extra: Any = Field(default_factory=dict)

    class Config:
        extra = "allow"


class WorkflowStep(BaseModel):
    """Single workflow step definition."""

    id: str = Field(..., description="Unique step identifier")
    name: str = Field(..., description="Step display name")
    action: str = Field(..., description="Action type to execute")
    params: dict[str, Any] = Field(default_factory=dict, description="Action parameters")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not v or not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Step ID must be alphanumeric with underscores/dashes")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or len(v) < 1:
            raise ValueError("Step name cannot be empty")
        return v

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if not v or not v.replace("_", "").isalnum():
            raise ValueError("Action must be alphanumeric with underscores")
        return v


class WorkflowConfig(BaseModel):
    """Global workflow configuration."""

    timeout: float = Field(default=30.0, description="Step timeout in seconds")
    browser_headless: bool = Field(default=False, description="Browser headless mode")


class Workflow(BaseModel):
    """Complete workflow definition."""

    name: str = Field(..., description="Workflow name")
    description: str = Field(default="", description="Workflow description")
    config: WorkflowConfig = Field(default_factory=WorkflowConfig)
    steps: list[WorkflowStep] = Field(..., description="Workflow steps")

    @field_validator("steps")
    @classmethod
    def validate_steps_not_empty(cls, v: list[WorkflowStep]) -> list[WorkflowStep]:
        if not v:
            raise ValueError("Workflow must contain at least one step")
        return v

    @field_validator("steps")
    @classmethod
    def validate_step_ids_unique(cls, v: list[WorkflowStep]) -> list[WorkflowStep]:
        step_ids = [step.id for step in v]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("Step IDs must be unique")
        return v


def load_workflow_from_yaml(workflow_path: Path) -> Workflow:
    """Load and validate workflow from YAML file.

    Args:
        workflow_path: Path to YAML workflow file

    Returns:
        Validated Workflow object

    Raises:
        WorkflowError: If file cannot be read
        ValidationError: If workflow structure is invalid
    """
    if not workflow_path.exists():
        raise WorkflowError(f"Workflow file not found: {workflow_path}")

    try:
        with open(workflow_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise WorkflowError(f"Failed to parse YAML: {e}", str(workflow_path))
    except IOError as e:
        raise WorkflowError(f"Failed to read workflow file: {e}", str(workflow_path))

    if not isinstance(data, dict):
        raise WorkflowError("Workflow must be a YAML object", str(workflow_path))

    try:
        workflow = Workflow(**data)
    except Exception as e:
        raise ValidationError(f"Workflow validation failed: {e}", str(workflow_path))

    return workflow
