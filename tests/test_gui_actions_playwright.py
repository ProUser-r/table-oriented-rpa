import asyncio
from pathlib import Path
from types import SimpleNamespace

from rpa_table_robot.gui_automation.builtin_actions import (
    ClickEmailAction,
    DownloadAttachmentsAction,
    SendEmailGmailAction,
)
from rpa_table_robot.gui_automation.config import GUIAutomationConfig
from rpa_table_robot.gui_automation.rpa_context import WorkflowContext


class FakeDownload:
    def __init__(self, name: str):
        self.suggested_filename = name

    async def save_as(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("x", encoding="utf-8")


class FakeExpectDownload:
    def __init__(self, download: FakeDownload):
        self.value = download

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeLocator:
    def __init__(self, page, selector: str):
        self.page = page
        self.selector = selector
        self.first = self

    async def wait_for(self, **kwargs):
        return None

    async def fill(self, value, **kwargs):
        self.page.fills.append((self.selector, value))

    async def press(self, key):
        self.page.presses.append((self.selector, key))

    async def click(self, **kwargs):
        self.page.clicks.append(self.selector)

    async def count(self):
        return self.page.counts.get(self.selector, 1)

    def nth(self, idx: int):
        return FakeNthLocator(self.page, self.selector, idx)

    async def get_attribute(self, name: str):
        return None


class FakeNthLocator(FakeLocator):
    def __init__(self, page, selector: str, idx: int):
        super().__init__(page, selector)
        self.idx = idx

    async def click(self, **kwargs):
        self.page.clicked_attachment_index = self.idx

    async def get_attribute(self, name: str):
        attrs = self.page.attachment_attrs[self.idx]
        return attrs.get(name)


class FakePage:
    def __init__(self):
        self.fills = []
        self.presses = []
        self.clicks = []
        self.counts = {}
        self.download_names = []
        self.attachment_attrs = []
        self.clicked_attachment_index = None
        self.keyboard = SimpleNamespace(type=self._k_type, press=self._k_press)
        self.typed = []
        self.keys = []

    async def _k_type(self, text):
        self.typed.append(text)

    async def _k_press(self, key):
        self.keys.append(key)

    def locator(self, selector: str):
        return FakeLocator(self, selector)

    async def reload(self, **kwargs):
        return None

    def expect_download(self, timeout=0):
        idx = self.clicked_attachment_index or 0
        return FakeExpectDownload(FakeDownload(self.download_names[idx]))


def make_context(page: FakePage) -> WorkflowContext:
    cfg = GUIAutomationConfig()
    ctx = WorkflowContext(workflow_name="wf", config=cfg)
    ctx.playwright_runtime = SimpleNamespace(page=page)
    return ctx


def test_click_email_builds_query_from_sender_unread_subject():
    page = FakePage()
    ctx = make_context(page)

    asyncio.run(
        ClickEmailAction().execute(
            {"from_sender": "a@b.com", "subject": "Daily", "unread_only": True},
            ctx,
        )
    )

    assert ("input[name='q']", 'from:a@b.com is:unread subject:"Daily"') in page.fills


def test_download_attachments_filters_pattern(tmp_path):
    page = FakePage()
    key = "div[download_url], span[download_url], div[role='link'][aria-label*='Download']"
    page.counts[key] = 2
    page.attachment_attrs = [
        {"data-tooltip": "table.png"},
        {"data-tooltip": "notes.pdf"},
    ]
    page.download_names = ["table.png", "notes.pdf"]

    ctx = make_context(page)

    files = asyncio.run(
        DownloadAttachmentsAction().execute(
            {"download_dir": str(tmp_path), "pattern": "*.png"},
            ctx,
        )
    )

    assert len(files) == 1
    assert files[0].name == "table.png"
    assert files[0].exists()


def test_send_email_gmail_composes_and_sends():
    page = FakePage()
    ctx = make_context(page)

    result = asyncio.run(
        SendEmailGmailAction().execute(
            {
                "to": ["user@example.com"],
                "subject": "Report",
                "body": "Done",
                "send": True,
            },
            ctx,
        )
    )

    assert result["status"] == "sent"
    assert any(sel == "textarea[name='to']" and "user@example.com" in val for sel, val in page.fills)
    assert any(sel == "input[name='subjectbox']" and val == "Report" for sel, val in page.fills)
