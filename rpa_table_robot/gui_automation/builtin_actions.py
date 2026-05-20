"""Built-in actions for workflow execution."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from rpa_table_robot.gui_automation.exceptions import ActionError, NavigationError
from rpa_table_robot.gui_automation.rpa_context import WorkflowContext
from rpa_table_robot.models import RobotResult
from rpa_table_robot.robot import TableRobot

logger = logging.getLogger(__name__)


class Action(ABC):
    """Base class for all actions."""

    @abstractmethod
    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> Any:
        """Execute the action.

        Args:
            params: Action parameters from workflow
            context: Workflow execution context

        Returns:
            Action result

        Raises:
            ActionError: If action fails
        """
        pass


class ProcessWithRobotAction(Action):
    """Process images with TableRobot to recognize tables."""

    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> RobotResult:
        """Process images with TableRobot.

        Parameters:
            image_dir: Directory containing table images
            output_dir: Directory for output artifacts
            store_result: Variable name to store result in context
        """
        try:
            image_dir = Path(params.get("image_dir", "."))
            output_dir = Path(params.get("output_dir", "./output"))
            store_result_var = params.get("store_result", "robot_result")

            if not image_dir.exists():
                raise ActionError(
                    f"Image directory not found: {image_dir}",
                    context.current_step_id,
                    context.current_step_name,
                    "process_with_robot",
                )

            image_dir.mkdir(parents=True, exist_ok=True)
            output_dir.mkdir(parents=True, exist_ok=True)

            image_paths = list(image_dir.glob("*.png")) + list(image_dir.glob("*.jpg"))

            if not image_paths:
                logger.warning(f"No images found in {image_dir}")
                return None

            logger.info(
                f"Processing {len(image_paths)} images with TableRobot from {image_dir}"
            )

            robot = TableRobot.from_env()
            result = robot.process_images(image_paths, output_dir=output_dir)

            context.robot_result = result
            context.set_variable(store_result_var, result)

            logger.info(
                f"TableRobot completed: {len(result.tables)} tables recognized"
            )

            return result

        except ActionError:
            raise
        except Exception as e:
            raise ActionError(
                f"Failed to process with TableRobot: {e}",
                context.current_step_id,
                context.current_step_name,
                "process_with_robot",
            ) from e


class WaitAction(Action):
    """Wait for specified seconds."""

    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> None:
        """Wait for specified duration.

        Parameters:
            seconds: Seconds to wait
        """
        import asyncio

        try:
            seconds = float(params.get("seconds", 1))
            if seconds < 0:
                raise ValueError("Seconds must be non-negative")

            logger.info(f"Waiting for {seconds} seconds")
            await asyncio.sleep(seconds)

        except Exception as e:
            raise ActionError(
                f"Wait action failed: {e}",
                context.current_step_id,
                context.current_step_name,
                "wait",
            ) from e


class ScreenshotAction(Action):
    """Take a screenshot for debugging."""

    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> Path:
        """Take screenshot and save to file.

        Parameters:
            name: Screenshot name/identifier
        """
        try:
            from RPA.Desktop import Desktop

            name = params.get("name", "screenshot")
            screenshot_dir = Path("./logs") / context.workflow_name
            screenshot_dir.mkdir(parents=True, exist_ok=True)

            screenshot_path = (
                screenshot_dir / f"{context.current_step_id}_{name}.png"
            )

            desktop = Desktop()
            desktop.screenshot(str(screenshot_path))

            context.add_screenshot(screenshot_path)
            logger.info(f"Screenshot saved to {screenshot_path}")

            return screenshot_path

        except Exception as e:
            logger.warning(f"Failed to take screenshot: {e}")
            return None


class ClickAction(Action):
    """Click on a UI element using RPA Framework."""

    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> None:
        """Click on element identified by locator.

        Parameters:
            locator: Element locator (image:references/button.png or text:Button Text)
        """
        try:
            from RPA.Desktop import Desktop

            locator = params.get("locator")
            if not locator:
                raise ValueError("Locator must be specified")

            logger.info(f"Clicking on element: {locator}")
            desktop = Desktop()

            if locator.startswith("image:"):
                image_path = locator[6:]
                desktop.click_element_by_image(image_path)
            elif locator.startswith("text:"):
                text = locator[5:]
                desktop.click_element_by_text(text)
            else:
                raise ValueError(
                    f"Unsupported locator type. Use 'image:' or 'text:' prefix"
                )

            logger.info("Click successful")

        except NavigationError:
            raise
        except Exception as e:
            raise NavigationError(
                f"Failed to find and click on element: {e}",
                context.current_step_id,
                context.current_step_name,
                "click",
            ) from e


class TypeAction(Action):
    """Type text into focused input field."""

    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> None:
        """Type text into focused element.

        Parameters:
            text: Text to type
        """
        try:
            from RPA.Desktop import Desktop

            text = params.get("text", "")
            logger.info(f"Typing text: {text[:50]}...")

            keyboard = Desktop()
            keyboard.type_text(text)

            logger.info("Text typing completed")

        except Exception as e:
            raise ActionError(
                f"Failed to type text: {e}",
                context.current_step_id,
                context.current_step_name,
                "type",
            ) from e


class OpenBrowserAction(Action):
    """Open a URL in browser using RPA Framework."""

    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> None:
        """Open URL in browser.

        Parameters:
            url: URL to open
            headless: Browser headless mode (optional)
        """
        try:
            from RPA.Browser.Selenium import Selenium

            url = params.get("url")
            if not url:
                raise ValueError("URL must be specified")

            headless = params.get("headless", False)

            logger.info(f"Opening browser to {url}")
            browser = Selenium()
            browser.open_browser(url, "headlesschrome" if headless else "chrome")

            logger.info(f"Browser opened successfully")

        except Exception as e:
            raise ActionError(
                f"Failed to open browser: {e}",
                context.current_step_id,
                context.current_step_name,
                "open_browser",
            ) from e


class CloseApplicationAction(Action):
    """Close currently active application."""

    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> None:
        """Close application.

        Parameters:
            app: Application name (optional)
        """
        try:
            from RPA.Desktop import Desktop

            app = params.get("app", "current")
            logger.info(f"Closing application: {app}")

            desktop = Desktop()
            if app == "current":
                desktop.close_application()
            else:
                desktop.close_application(app)

            logger.info("Application closed")

        except Exception as e:
            logger.warning(f"Failed to close application: {e}")


class DownloadAttachmentsAction(Action):
    """Download attachments from email."""

    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> list[Path]:
        """Download email attachments.

        Parameters:
            download_dir: Directory to save attachments
            pattern: File pattern to match (e.g., *.png)
            timeout: Seconds to wait for download
        """
        try:
            from RPA.Email.ImapSmtp import ImapSmtp

            download_dir = Path(params.get("download_dir", "./attachments"))
            pattern = params.get("pattern", "*")
            timeout = int(params.get("timeout", 30))

            download_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"Downloading attachments matching '{pattern}' to {download_dir}")

            mail = ImapSmtp()
            attachments = mail.save_latest_emails_by_subject(
                download_dir, prefix_folder=False, json_format=False
            )

            downloaded_files = list(download_dir.glob(pattern))

            logger.info(f"Downloaded {len(downloaded_files)} attachments")

            return downloaded_files

        except Exception as e:
            raise ActionError(
                f"Failed to download attachments: {e}",
                context.current_step_id,
                context.current_step_name,
                "download_attachments",
            ) from e


class OpenWordDocumentAction(Action):
    """Open a Word document."""

    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> None:
        """Open Word document.

        Parameters:
            path: Path to .docx file
        """
        try:
            from RPA.Desktop import Desktop

            file_path = Path(params.get("path"))
            if not file_path.exists():
                raise ValueError(f"File not found: {file_path}")

            logger.info(f"Opening Word document: {file_path}")

            desktop = Desktop()
            desktop.open_file(str(file_path))

            import asyncio
            await asyncio.sleep(2)

            logger.info("Word document opened")

        except Exception as e:
            raise ActionError(
                f"Failed to open Word document: {e}",
                context.current_step_id,
                context.current_step_name,
                "open_word",
            ) from e


class FindAndReplaceAction(Action):
    """Find text in document and replace it."""

    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> None:
        """Find and replace text in active document.

        Parameters:
            search: Text to search for (e.g., <!-- REPORT -->)
            replace: Replacement text (supports ${variable} interpolation)
        """
        try:
            from RPA.Desktop import Desktop

            search_text = params.get("search")
            replace_text = params.get("replace", "")

            if not search_text:
                raise ValueError("Search text must be specified")

            interpolated_replace = self._interpolate(replace_text, context)

            logger.info(f"Finding '{search_text}' and replacing with content")

            desktop = Desktop()
            desktop.find_element_and_type(search_text, interpolated_replace)

            logger.info("Find and replace completed")

        except Exception as e:
            raise ActionError(
                f"Failed to find and replace: {e}",
                context.current_step_id,
                context.current_step_name,
                "find_and_replace",
            ) from e

    @staticmethod
    def _interpolate(text: str, context: WorkflowContext) -> str:
        """Interpolate ${variable} in text."""
        import re

        def replace_var(match):
            var_name = match.group(1)
            value = context.get_variable(var_name)
            if value is None:
                logger.warning(f"Variable not found in context: {var_name}")
                return match.group(0)
            return str(value)

        return re.sub(r"\$\{([^}]+)\}", replace_var, text)


class InsertTextAction(Action):
    """Insert text at specific location in document."""

    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> None:
        """Insert text into document.

        Parameters:
            text: Text to insert (supports ${variable} interpolation)
            search_for: Optional text to find before insertion
        """
        try:
            from RPA.Desktop import Desktop

            text = params.get("text", "")
            search_for = params.get("search_for")

            interpolated_text = self._interpolate(text, context)

            logger.info("Inserting text into document")

            desktop = Desktop()

            if search_for:
                desktop.find_element_and_type(search_for, interpolated_text)
            else:
                desktop.type_text(interpolated_text)

            logger.info("Text insertion completed")

        except Exception as e:
            raise ActionError(
                f"Failed to insert text: {e}",
                context.current_step_id,
                context.current_step_name,
                "insert_text",
            ) from e

    @staticmethod
    def _interpolate(text: str, context: WorkflowContext) -> str:
        """Interpolate ${variable} in text."""
        import re

        def replace_var(match):
            var_path = match.group(1)

            parts = var_path.split(".")
            value = context.get_variable(parts[0])

            for part in parts[1:]:
                if isinstance(value, dict):
                    value = value.get(part)
                elif hasattr(value, part):
                    value = getattr(value, part)
                else:
                    logger.warning(f"Cannot access {var_path}")
                    return match.group(0)

            if value is None:
                logger.warning(f"Variable not found: {var_path}")
                return match.group(0)

            return str(value)

        return re.sub(r"\$\{([^}]+)\}", replace_var, text)


class SaveDocumentAction(Action):
    """Save active document."""

    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> None:
        """Save document.

        Parameters:
            wait_before_save: Seconds to wait before saving
        """
        try:
            from RPA.Desktop import Desktop

            wait_before = float(params.get("wait_before_save", 1))

            if wait_before > 0:
                import asyncio
                await asyncio.sleep(wait_before)

            logger.info("Saving document")

            desktop = Desktop()
            desktop.press_keys("ctrl", "s")

            import asyncio
            await asyncio.sleep(1)

            logger.info("Document saved")

        except Exception as e:
            raise ActionError(
                f"Failed to save document: {e}",
                context.current_step_id,
                context.current_step_name,
                "save_document",
            ) from e


class ClickEmailAction(Action):
    """Click on specific email in inbox."""

    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> None:
        """Click on email by sender or subject.

        Parameters:
            from_sender: Sender email or name to find
            subject: Email subject to find
            locator: Alternative - direct locator (image: or text:)
        """
        try:
            from RPA.Desktop import Desktop

            from_sender = params.get("from_sender")
            subject = params.get("subject")
            locator = params.get("locator")

            logger.info(f"Clicking on email from {from_sender} with subject '{subject}'")

            desktop = Desktop()

            if locator:
                if locator.startswith("image:"):
                    image_path = locator[6:]
                    desktop.click_element_by_image(image_path)
                elif locator.startswith("text:"):
                    text = locator[5:]
                    desktop.click_element_by_text(text)
            elif subject:
                desktop.click_element_by_text(subject)
            elif from_sender:
                desktop.click_element_by_text(from_sender)
            else:
                raise ValueError("Must specify from_sender, subject, or locator")

            import asyncio
            await asyncio.sleep(1)

            logger.info("Email clicked successfully")

        except Exception as e:
            raise NavigationError(
                f"Failed to click on email: {e}",
                context.current_step_id,
                context.current_step_name,
                "click_email",
            ) from e


ACTION_REGISTRY: dict[str, type[Action]] = {
    "process_with_robot": ProcessWithRobotAction,
    "wait": WaitAction,
    "screenshot": ScreenshotAction,
    "click": ClickAction,
    "click_email": ClickEmailAction,
    "type": TypeAction,
    "open_browser": OpenBrowserAction,
    "close_application": CloseApplicationAction,
    "download_attachments": DownloadAttachmentsAction,
    "open_word": OpenWordDocumentAction,
    "find_and_replace": FindAndReplaceAction,
    "insert_text": InsertTextAction,
    "save_document": SaveDocumentAction,
}


def get_action(action_name: str) -> type[Action]:
    """Get action class by name.

    Args:
        action_name: Name of the action

    Returns:
        Action class

    Raises:
        ActionError: If action not found
    """
    if action_name not in ACTION_REGISTRY:
        available = ", ".join(ACTION_REGISTRY.keys())
        raise ActionError(
            f"Unknown action: {action_name}. Available actions: {available}"
        )

    return ACTION_REGISTRY[action_name]
