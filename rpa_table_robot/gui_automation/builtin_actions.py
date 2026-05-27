"""Built-in actions for workflow execution."""

from __future__ import annotations

import asyncio
import fnmatch
import logging
import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from rpa_table_robot.gui_automation.exceptions import ActionError, NavigationError
from rpa_table_robot.gui_automation.rpa_context import WorkflowContext
from rpa_table_robot.models import RobotResult
from rpa_table_robot.robot import TableRobot
from rpa_table_robot.classifier import RubertTopicClassifier
from rpa_table_robot.topic_routing import (
    DispatchResult,
    classify_topic,
    extract_messages_from_tables,
    resolve_recipients,
)

logger = logging.getLogger(__name__)


class PlaywrightRuntime:
    """Thin runtime wrapper around Playwright async API."""

    def __init__(self, playwright: Any, browser_context: Any, page: Any):
        self.playwright = playwright
        self.browser_context = browser_context
        self.page = page

    async def close(self) -> None:
        try:
            await self.browser_context.close()
        finally:
            await self.playwright.stop()


class Action(ABC):
    """Base class for all actions."""

    @abstractmethod
    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> Any:
        pass


def _runtime(context: WorkflowContext) -> PlaywrightRuntime:
    if context.playwright_runtime is None:
        raise ActionError(
            "Playwright browser is not initialized. Run open_browser first.",
            context.current_step_id,
            context.current_step_name,
            "playwright_runtime",
        )
    return context.playwright_runtime


def _gmail_search_query(from_sender: str | None, subject: str | None, unread_only: bool) -> str:
    parts: list[str] = []
    if from_sender:
        parts.append(f"from:{from_sender}")
    if unread_only:
        parts.append("is:unread")
    if subject:
        parts.append(f'subject:"{subject}"')
    return " ".join(parts).strip()


async def _fill_best_effort(page: Any, selectors: list[str], value: str) -> bool:
    for selector in selectors:
        locator = page.locator(selector).first
        if await locator.count() > 0:
            await locator.fill(value)
            return True
    return False


class ProcessWithRobotAction(Action):
    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> RobotResult:
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

            image_paths = (
                list(image_dir.glob("*.png"))
                + list(image_dir.glob("*.jpg"))
                + list(image_dir.glob("*.jpeg"))
            )

            if not image_paths:
                logger.warning("No images found in %s", image_dir)
                return None

            robot = TableRobot.from_env()
            result = robot.process_images(image_paths, output_dir=output_dir)

            context.robot_result = result
            context.set_variable(store_result_var, result)
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
    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> None:
        try:
            seconds = float(params.get("seconds", 1))
            if seconds < 0:
                raise ValueError("Seconds must be non-negative")
            await asyncio.sleep(seconds)
        except Exception as e:
            raise ActionError(
                f"Wait action failed: {e}",
                context.current_step_id,
                context.current_step_name,
                "wait",
            ) from e


class ScreenshotAction(Action):
    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> Path | None:
        try:
            runtime = _runtime(context)
            name = params.get("name", "screenshot")
            screenshot_dir = Path("./logs") / context.workflow_name
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            screenshot_path = screenshot_dir / f"{context.current_step_id}_{name}.png"
            await runtime.page.screenshot(path=str(screenshot_path), full_page=True)
            context.add_screenshot(screenshot_path)
            return screenshot_path
        except Exception as e:
            logger.warning("Failed to take screenshot: %s", e)
            return None


class ClickAction(Action):
    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> None:
        try:
            runtime = _runtime(context)
            locator = params.get("locator")
            timeout = int(float(params.get("timeout", context.config.timeout)) * 1000)
            if not locator:
                raise ValueError("Locator must be specified")

            target = runtime.page.locator(locator)
            await target.first.wait_for(state="visible", timeout=timeout)
            await target.first.click(timeout=timeout)
        except Exception as e:
            raise NavigationError(
                f"Failed to click on element: {e}",
                context.current_step_id,
                context.current_step_name,
                "click",
            ) from e


class TypeAction(Action):
    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> None:
        try:
            runtime = _runtime(context)
            text = params.get("text", "")
            locator = params.get("locator")
            timeout = int(float(params.get("timeout", context.config.timeout)) * 1000)

            if locator:
                target = runtime.page.locator(locator).first
                await target.wait_for(state="visible", timeout=timeout)
                await target.fill(str(text), timeout=timeout)
                return

            await runtime.page.keyboard.type(str(text))
        except Exception as e:
            raise ActionError(
                f"Failed to type text: {e}",
                context.current_step_id,
                context.current_step_name,
                "type",
            ) from e


class OpenBrowserAction(Action):
    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> None:
        try:
            from playwright.async_api import async_playwright

            runtime = context.playwright_runtime
            if runtime is not None:
                await runtime.close()

            url = params.get("url", context.config.gmail_base_url)
            headless = bool(params.get("headless", context.config.browser_headless))
            timeout = int(float(params.get("timeout", context.config.timeout)) * 1000)

            user_data_dir = Path(params.get("user_data_dir", context.config.playwright_user_data_dir))
            user_data_dir.mkdir(parents=True, exist_ok=True)

            downloads_dir = Path(params.get("downloads_dir", context.config.downloads_dir))
            downloads_dir.mkdir(parents=True, exist_ok=True)

            playwright = await async_playwright().start()
            browser_type = getattr(playwright, context.config.playwright_browser_name)

            launch_kwargs: dict[str, Any] = {
                "headless": headless,
                "accept_downloads": True,
                "downloads_path": str(downloads_dir),
                "args": ['--disable-blink-features=AutomationControlled'],
            }
            if context.config.playwright_channel:
                launch_kwargs["channel"] = context.config.playwright_channel

            browser_context = await browser_type.launch_persistent_context(
                str(user_data_dir),
                **launch_kwargs,
            )
            page = browser_context.pages[0] if browser_context.pages else await browser_context.new_page()
            page.set_default_timeout(timeout)
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)

            context.playwright_runtime = PlaywrightRuntime(playwright, browser_context, page)
            context.set_variable("current_url", url)
        except Exception as e:
            raise ActionError(
                f"Failed to open browser with Playwright: {e}",
                context.current_step_id,
                context.current_step_name,
                "open_browser",
            ) from e


class CloseApplicationAction(Action):
    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> None:
        runtime = context.playwright_runtime
        if runtime is None:
            logger.info("No active browser runtime to close")
            return
        try:
            await runtime.close()
        except Exception as e:
            logger.warning("Failed to close Playwright runtime: %s", e)
        finally:
            context.playwright_runtime = None


class ClickEmailAction(Action):
    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> None:
        try:
            runtime = _runtime(context)
            page = runtime.page
            from_sender = params.get("from_sender")
            subject = params.get("subject")
            unread_only = bool(params.get("unread_only", True))
            timeout = int(float(params.get("timeout", context.config.timeout)) * 1000)
            search_query = params.get("search_query") or _gmail_search_query(from_sender, subject, unread_only)

            if not search_query:
                raise ValueError("Specify from_sender, subject, or search_query")

            search_box = page.locator("input[name='q']").first
            await search_box.wait_for(state="visible", timeout=timeout)
            await search_box.fill(search_query, timeout=timeout)
            await search_box.press("Enter")

            first_row = page.locator("tr.zA").first
            await first_row.wait_for(state="visible", timeout=timeout)

            retries = int(params.get("retries", 2))
            for attempt in range(retries + 1):
                try:
                    await first_row.click(timeout=timeout)
                    await page.locator("div[role='main']").first.wait_for(
                        state="visible", timeout=timeout
                    )
                    return
                except Exception:
                    if attempt == retries:
                        raise
                    await page.reload(wait_until="domcontentloaded", timeout=timeout)
                    await search_box.wait_for(state="visible", timeout=timeout)
                    await search_box.fill(search_query, timeout=timeout)
                    await search_box.press("Enter")
                    first_row = page.locator("tr.zA").first
                    await first_row.wait_for(state="visible", timeout=timeout)

        except Exception as e:
            raise NavigationError(
                f"Failed to open Gmail email: {e}",
                context.current_step_id,
                context.current_step_name,
                "click_email",
            ) from e
        


class DownloadAttachmentsAction(Action):
    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> list[Path]:
        try:
            runtime = _runtime(context)
            page = runtime.page
            timeout = int(float(params.get("timeout", context.config.timeout)) * 1000)
            pattern = str(params.get("pattern", "*"))
            max_files = params.get("max_files")
            max_files = int(max_files) if max_files is not None else None

            download_dir = Path(params.get("download_dir", context.config.downloads_dir))
            download_dir.mkdir(parents=True, exist_ok=True)

            attachment_buttons = page.locator("[aria-label*='Download'], [aria-label*='Скачать файл']")
            attachment_imgs = page.locator("img[alt$='.png'], img[alt$='.jpg'], img[alt$='.jpeg']")
            count = await attachment_buttons.count()
            downloaded: list[Path] = []

            if count == 0:
                logger.info("No Gmail attachments found in current email")
                return downloaded

            for i in range(count):
                if max_files is not None and len(downloaded) >= max_files:
                    break

                button = attachment_buttons.nth(i)
                # filename = await button.get_attribute("data-tooltip") or await button.get_attribute("aria-label")
                # if filename:
                #     m = re.search(r"([\w\-. ]+\.[A-Za-z0-9]+)", filename)
                #     if m and not fnmatch.fnmatch(m.group(1), pattern):
                #         continue

                async with page.expect_download(timeout=timeout) as download_info:
                    await button.hover()
                    await button.click(timeout=timeout)
                download = await download_info.value
                suggested = download.suggested_filename
                if not fnmatch.fnmatch(suggested, pattern):
                    continue
                target_path = download_dir / suggested
                await download.save_as(str(target_path))
                downloaded.append(target_path)

            return downloaded
        except Exception as e:
            raise ActionError(
                f"Failed to download Gmail attachments: {e}",
                context.current_step_id,
                context.current_step_name,
                "download_attachments",
            ) from e


class SendEmailGmailAction(Action):
    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> dict[str, Any]:
        try:
            await page.goto('https://mail.google.com/mail/u/0/');

            runtime = _runtime(context)
            page = runtime.page
            timeout = int(float(params.get("timeout", context.config.timeout)) * 1000)

            to = params.get("to")
            if not to:
                raise ValueError("'to' is required")
            to_value = ", ".join(to) if isinstance(to, list) else str(to)

            subject = str(params.get("subject", ""))
            body = str(params.get("body", ""))
            cc = params.get("cc")
            bcc = params.get("bcc")
            attachments = params.get("attachments", [])
            send = bool(params.get("send", True))
            save_draft = bool(params.get("save_draft", False))

            await page.locator("div[gh='cm']").first.click(timeout=timeout)
            await page.locator("div[role='dialog']").first.wait_for(state="visible", timeout=timeout)

            await _fill_best_effort(page, ["input[role='combobox']"], to_value)
            await _fill_best_effort(page, ["input[name='subjectbox']"], subject)

            body_locator = page.locator("div[aria-label='Message Body'], div[role='textbox'][aria-label*='Message Body']").first
            await body_locator.click(timeout=timeout)
            await body_locator.fill(body, timeout=timeout)

            if cc:
                await page.locator("span:has-text('Cc')").first.click(timeout=timeout)
                cc_value = ", ".join(cc) if isinstance(cc, list) else str(cc)
                await _fill_best_effort(page, ["textarea[name='cc']", "input[aria-label^='Cc']"], cc_value)

            if bcc:
                await page.locator("span:has-text('Bcc')").first.click(timeout=timeout)
                bcc_value = ", ".join(bcc) if isinstance(bcc, list) else str(bcc)
                await _fill_best_effort(page, ["textarea[name='bcc']", "input[aria-label^='Bcc']"], bcc_value)

            if attachments:
                files = [str(Path(f)) for f in attachments]
                file_input = page.locator("input[type='file']").first
                await file_input.set_input_files(files, timeout=timeout)

            if send:
                #await page.locator("div[role='button'][data-tooltip^='Send']").first.click(timeout=timeout)
                await page.keyboard.press("Contrtol+Enter")
                await page.locator("span:has-text('Message sent'), span:has-text('отправлено')").first.wait_for(timeout=timeout)
                return {"status": "sent"}

            if save_draft:
                await page.keyboard.press("Escape")
                return {"status": "draft_saved"}

            return {"status": "composed"}

        except Exception as e:
            raise ActionError(
                f"Failed to send Gmail email: {e}",
                context.current_step_id,
                context.current_step_name,
                "send_email_gmail",
            ) from e


class RouteAndSendFromTablesAction(Action):
    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> dict[str, Any]:
        try:
            source_result_name = str(params.get("source_result", "robot_result"))
            model_dir = params.get("model_dir") or os.getenv(
                "RPA_TOPIC_MODEL_DIR", "data/rubert_it_classifier"
            )
            db_path = params.get("db_path") or os.getenv("RPA_EMAIL_DB_PATH", "data/sqlite.db")
            send = bool(params.get("send", False))
            stop_on_error = bool(params.get("stop_on_error", False))
            max_rows = params.get("max_rows")
            max_rows = int(max_rows) if max_rows is not None else None

            robot_result = context.get_variable(source_result_name)
            if robot_result is None and source_result_name == "robot_result":
                robot_result = context.robot_result
            if robot_result is None:
                raise ValueError(f"Robot result '{source_result_name}' not found in context")

            classifier = RubertTopicClassifier(model_dir=model_dir)
            messages = extract_messages_from_tables(robot_result)

            dispatch = DispatchResult()
            sender = SendEmailGmailAction()

            for msg in messages:
                if max_rows is not None and dispatch.processed_rows >= max_rows:
                    break
                dispatch.processed_rows += 1

                try:
                    prediction = classify_topic(msg.subject, msg.first_sentence, classifier)
                    recipients = resolve_recipients(db_path, prediction.topic)

                    if not recipients:
                        dispatch.skipped_rows += 1
                        dispatch.errors.append(
                            f"row={msg.row_index} table={msg.table_index}: no recipients for topic={prediction.topic}"
                        )
                        continue

                    await sender.execute(
                        {
                            "to": recipients,
                            "subject": msg.subject,
                            "body": msg.body,
                            "send": send,
                            "save_draft": not send,
                        },
                        context,
                    )
                    dispatch.sent_count += 1

                except Exception as row_exc:
                    dispatch.skipped_rows += 1
                    dispatch.errors.append(
                        f"row={msg.row_index} table={msg.table_index}: {row_exc}"
                    )
                    if stop_on_error:
                        raise

            return {
                "processed_rows": dispatch.processed_rows,
                "sent_count": dispatch.sent_count,
                "skipped_rows": dispatch.skipped_rows,
                "errors": dispatch.errors,
            }

        except Exception as e:
            raise ActionError(
                f"Failed to route and send from tables: {e}",
                context.current_step_id,
                context.current_step_name,
                "route_and_send_from_tables",
            ) from e


class OpenWordDocumentAction(Action):
    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> None:
        raise ActionError(
            "open_word is no longer supported in Playwright web mode.",
            context.current_step_id,
            context.current_step_name,
            "open_word",
        )


class FindAndReplaceAction(Action):
    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> None:
        raise ActionError(
            "find_and_replace is no longer supported in Playwright web mode.",
            context.current_step_id,
            context.current_step_name,
            "find_and_replace",
        )


class InsertTextAction(Action):
    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> None:
        raise ActionError(
            "insert_text is no longer supported in Playwright web mode.",
            context.current_step_id,
            context.current_step_name,
            "insert_text",
        )


class SaveDocumentAction(Action):
    async def execute(self, params: dict[str, Any], context: WorkflowContext) -> None:
        raise ActionError(
            "save_document is no longer supported in Playwright web mode.",
            context.current_step_id,
            context.current_step_name,
            "save_document",
        )


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
    "send_email_gmail": SendEmailGmailAction,
    "route_and_send_from_tables": RouteAndSendFromTablesAction,
    "open_word": OpenWordDocumentAction,
    "find_and_replace": FindAndReplaceAction,
    "insert_text": InsertTextAction,
    "save_document": SaveDocumentAction,
}


def get_action(action_name: str) -> type[Action]:
    if action_name not in ACTION_REGISTRY:
        available = ", ".join(ACTION_REGISTRY.keys())
        raise ActionError(f"Unknown action: {action_name}. Available actions: {available}")
    return ACTION_REGISTRY[action_name]
