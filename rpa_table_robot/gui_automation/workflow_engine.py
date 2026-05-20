"""Workflow execution engine."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from rpa_table_robot.gui_automation.builtin_actions import get_action
from rpa_table_robot.gui_automation.config import GUIAutomationConfig
from rpa_table_robot.gui_automation.exceptions import ActionError
from rpa_table_robot.gui_automation.rpa_context import WorkflowContext
from rpa_table_robot.gui_automation.yaml_loader import Workflow

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Executes workflows sequentially."""

    def __init__(self, config: GUIAutomationConfig | None = None):
        """Initialize workflow engine.

        Args:
            config: GUI automation configuration
        """
        self.config = config or GUIAutomationConfig.from_env()
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Setup structured logging."""
        log_format = (
            "[%(levelname)s] %(asctime)s - "
            "%(name)s - %(funcName)s - %(message)s"
        )
        logging.basicConfig(
            level=self.config.log_level,
            format=log_format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(Path("logs") / "workflow.log"),
            ],
        )
        logger.debug(f"Logging configured with level {self.config.log_level}")

    async def execute(self, workflow: Workflow) -> WorkflowContext:
        """Execute workflow sequentially.

        Args:
            workflow: Workflow to execute

        Returns:
            Workflow context with results

        Raises:
            ActionError: If any step fails
        """
        context = WorkflowContext(workflow_name=workflow.name)
        context.set_variable("workflow_name", workflow.name)

        logger.info(f"Starting workflow: {workflow.name}")
        logger.info(f"Description: {workflow.description}")
        logger.info(f"Total steps: {len(workflow.steps)}")

        try:
            for step in workflow.steps:
                await self._execute_step(step, context, workflow)

            logger.info(f"Workflow completed successfully: {workflow.name}")
            return context

        except ActionError as e:
            logger.error(
                f"Workflow failed at step {context.current_step_id}: {e.step_name}"
            )
            logger.error(f"Action: {e.action}, Error: {str(e)}")
            raise

    async def _execute_step(
        self, step, context: WorkflowContext, workflow: Workflow
    ) -> None:
        """Execute a single step.

        Args:
            step: Workflow step
            context: Execution context
            workflow: Full workflow (for error context)

        Raises:
            ActionError: If step execution fails
        """
        context.current_step_id = step.id
        context.current_step_name = step.name

        logger.info(f"[{step.id}] Executing: {step.name}")
        logger.debug(f"[{step.id}] Action: {step.action}")
        logger.debug(f"[{step.id}] Parameters: {step.params}")

        try:
            action_class = get_action(step.action)
            action = action_class()

            result = await action.execute(step.params, context)

            context.set_step_result(step.id, result)

            logger.info(f"[{step.id}] ✓ Step completed successfully")

        except ActionError as e:
            e.step_id = step.id
            e.step_name = step.name
            e.action = step.action

            logger.error(f"[{step.id}] ✗ Step failed: {str(e)}")

            await self._handle_step_error(step, context, e)
            raise

    async def _handle_step_error(
        self, step, context: WorkflowContext, error: ActionError
    ) -> None:
        """Handle step execution error.

        Args:
            step: Failed step
            context: Execution context
            error: Exception that occurred
        """
        error_dir = Path("logs") / context.workflow_name / "errors"
        error_dir.mkdir(parents=True, exist_ok=True)

        screenshot_path = error_dir / f"step_{step.id}_error.png"
        logger.info(f"Attempting to capture error screenshot: {screenshot_path}")

        try:
            from RPA.Desktop import Desktop

            desktop = Desktop()
            desktop.screenshot(str(screenshot_path))
            logger.info(f"Error screenshot saved to {screenshot_path}")
            context.add_screenshot(screenshot_path)

        except Exception as e:
            logger.warning(f"Failed to capture error screenshot: {e}")

        error_log_path = error_dir / f"step_{step.id}_error.log"
        with open(error_log_path, "w") as f:
            f.write(f"Step ID: {step.id}\n")
            f.write(f"Step Name: {step.name}\n")
            f.write(f"Action: {step.action}\n")
            f.write(f"Parameters: {step.params}\n")
            f.write(f"Error: {str(error)}\n")
            f.write(f"\nContext Variables: {context.variables}\n")
            f.write(f"Step Results: {context.step_results}\n")

        logger.info(f"Error details logged to {error_log_path}")

    def execute_sync(self, workflow: Workflow) -> WorkflowContext:
        """Execute workflow synchronously (wrapper for async).

        Args:
            workflow: Workflow to execute

        Returns:
            Workflow context with results
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.execute(workflow))
        finally:
            loop.close()
