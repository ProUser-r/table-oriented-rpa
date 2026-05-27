import asyncio
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from rpa_table_robot.gui_automation.builtin_actions import RouteAndSendFromTablesAction
from rpa_table_robot.gui_automation.config import GUIAutomationConfig
from rpa_table_robot.gui_automation.rpa_context import WorkflowContext
from rpa_table_robot.models import RecognizedTable, RobotResult


class DummyClassifier:
    def __init__(self, model_dir):
        self.model_dir = model_dir

    def predict(self, subject, first_sentence):
        _ = first_sentence
        if "security" in subject.lower() or "безопас" in subject.lower():
            return "cybersecurity", 0.9
        return "programming", 0.8


class DummySender:
    calls = []

    async def execute(self, params, context):
        _ = context
        self.calls.append(params)
        return {"status": "draft_saved" if not params.get("send") else "sent"}


def _ctx_with_robot_result():
    cfg = GUIAutomationConfig()
    ctx = WorkflowContext(workflow_name="wf", config=cfg)
    ctx.playwright_runtime = SimpleNamespace(page=object())
    df = pd.DataFrame(
        {
            "Тема": ["Security bulletin"],
            "Текст письма": ["Please patch systems. ASAP."],
        }
    )
    table = RecognizedTable(source_image=Path("img.png"), table_index=1, dataframe=df)
    robot_result = RobotResult(tables=[table], report="r")
    ctx.robot_result = robot_result
    ctx.set_variable("robot_result", robot_result)
    return ctx


def test_route_and_send_from_tables_uses_context_robot_result(monkeypatch):
    ctx = _ctx_with_robot_result()

    monkeypatch.setattr(
        "rpa_table_robot.gui_automation.builtin_actions.RubertTopicClassifier",
        DummyClassifier,
    )
    monkeypatch.setattr(
        "rpa_table_robot.gui_automation.builtin_actions.SendEmailGmailAction",
        DummySender,
    )

    result = asyncio.run(
        RouteAndSendFromTablesAction().execute(
            {
                "db_path": "data/sqlite.db",
                "model_dir": "data/rubert_it_classifier",
                "send": False,
            },
            ctx,
        )
    )

    assert result["processed_rows"] == 1
    assert result["sent_count"] == 1
    assert result["skipped_rows"] == 0
