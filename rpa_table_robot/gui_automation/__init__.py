"""GUI Automation module for RPA Table Robot."""

from rpa_table_robot.gui_automation.config import GUIAutomationConfig
from rpa_table_robot.gui_automation.exceptions import (
    ActionError,
    GUIAutomationError,
    NavigationError,
    TimeoutError,
    ValidationError,
    WorkflowError,
)
from rpa_table_robot.gui_automation.workflow_engine import WorkflowEngine
from rpa_table_robot.gui_automation.yaml_loader import (
    Workflow,
    load_workflow_from_yaml,
)

__all__ = [
    "GUIAutomationConfig",
    "GUIAutomationError",
    "ActionError",
    "NavigationError",
    "TimeoutError",
    "ValidationError",
    "WorkflowError",
    "WorkflowEngine",
    "Workflow",
    "load_workflow_from_yaml",
]
