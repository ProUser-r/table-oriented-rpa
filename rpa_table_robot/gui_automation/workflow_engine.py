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
        self.config = config or GUIAutomationConfig.from_env()
        self._setup_logging()

    def _setup_logging(self) -> None:
        log_format = (
            "[%(levelname)s] %(asctime)s - "
            "%(name)s - %(funcName)s - %(message)s"
        )
        Path("logs").mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            level=self.config.log_level,
            format=log_format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(Path("logs") / "workflow.log"),
            ],
        )

    async def execute(self, workflow: Workflow) -> WorkflowContext:
        context = WorkflowContext(workflow_name=workflow.name, config=self.config)
        context.set_variable("workflow_name", workflow.name)

        logger.info("Starting workflow: %s", workflow.name)

        try:
            for step in workflow.steps:
                await self._execute_step(step, context)
            logger.info("Workflow completed successfully: %s", workflow.name)
            return context
        except ActionError as e:
            logger.error("Workflow failed at step %s: %s", context.current_step_id, e.step_name)
            logger.error("Action: %s, Error: %s", e.action, str(e))
            raise
        finally:
            try:
                runtime = context.playwright_runtime
                if runtime is not None:
                    await runtime.close()
                    context.playwright_runtime = None
            except Exception as close_err:
                logger.warning("Failed to close Playwright runtime on workflow exit: %s", close_err)

    async def _execute_step(self, step, context: WorkflowContext) -> None:
        context.current_step_id = step.id
        context.current_step_name = step.name

        logger.info("[%s] Executing: %s", step.id, step.name)

        try:
            action_class = get_action(step.action)
            action = action_class()
            result = await action.execute(step.params, context)
            context.set_step_result(step.id, result)
            logger.info("[%s] Step completed successfully", step.id)
        except ActionError as e:
            e.step_id = step.id
            e.step_name = step.name
            e.action = step.action
            logger.error("[%s] Step failed: %s", step.id, str(e))
            await self._handle_step_error(step, context, e)
            raise

    async def _handle_step_error(self, step, context: WorkflowContext, error: ActionError) -> None:
        error_dir = Path("logs") / context.workflow_name / "errors"
        error_dir.mkdir(parents=True, exist_ok=True)

        screenshot_path = error_dir / f"step_{step.id}_error.png"
        try:
            runtime = context.playwright_runtime
            if runtime is not None:
                await runtime.page.screenshot(path=str(screenshot_path), full_page=True)
                context.add_screenshot(screenshot_path)
        except Exception as e:
            logger.warning("Failed to capture error screenshot: %s", e)

        error_log_path = error_dir / f"step_{step.id}_error.log"
        with open(error_log_path, "w", encoding="utf-8") as f:
            f.write(f"Step ID: {step.id}\n")
            f.write(f"Step Name: {step.name}\n")
            f.write(f"Action: {step.action}\n")
            f.write(f"Parameters: {step.params}\n")
            f.write(f"Error: {str(error)}\n")
            f.write(f"\nContext Variables: {context.variables}\n")
            f.write(f"Step Results: {context.step_results}\n")

    def execute_sync(self, workflow: Workflow) -> WorkflowContext:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.execute(workflow))
        finally:
            loop.close()
