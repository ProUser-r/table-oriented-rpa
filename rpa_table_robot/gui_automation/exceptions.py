"""Custom exceptions for GUI automation module."""


class GUIAutomationError(Exception):
    """Base exception for GUI automation errors."""

    pass


class WorkflowError(GUIAutomationError):
    """Raised when workflow loading or validation fails."""

    def __init__(self, message: str, workflow_file: str | None = None):
        self.workflow_file = workflow_file
        super().__init__(message)


class ActionError(GUIAutomationError):
    """Raised when action execution fails."""

    def __init__(
        self,
        message: str,
        step_id: str | None = None,
        step_name: str | None = None,
        action: str | None = None,
    ):
        self.step_id = step_id
        self.step_name = step_name
        self.action = action
        super().__init__(message)


class NavigationError(ActionError):
    """Raised when UI element cannot be found."""

    pass


class TimeoutError(ActionError):
    """Raised when action times out."""

    pass


class ValidationError(WorkflowError):
    """Raised when workflow validation fails."""

    pass
