from pathlib import Path

import pandas as pd

from rpa_table_robot.models import RecognizedTable, RobotResult
from rpa_table_robot.topic_routing import (
    classify_topic,
    extract_messages_from_tables,
    first_sentence,
    resolve_recipients,
)


class _FakeClassifier:
    def predict(self, subject, first_sentence):
        _ = subject, first_sentence
        return "data_ai", 0.77


def test_first_sentence_extracts_until_terminal_mark():
    text = "Первое предложение. Второе предложение"
    assert first_sentence(text) == "Первое предложение."


def test_extract_messages_from_tables_finds_russian_columns():
    df = pd.DataFrame(
        {
            "Тема": ["Безопасность"],
            "Текст письма": ["Проверьте SOC отчеты. Вторая строка"],
        }
    )
    table = RecognizedTable(source_image=Path("img.png"), table_index=1, dataframe=df)
    result = RobotResult(tables=[table], report="ok")

    rows = extract_messages_from_tables(result)
    assert len(rows) == 1
    assert rows[0].subject == "Безопасность"
    assert rows[0].first_sentence == "Проверьте SOC отчеты."


def test_resolve_recipients_from_sqlite_db():
    recipients = resolve_recipients("data/sqlite.db", "cybersecurity")
    assert recipients
    assert all("@" in r for r in recipients)


def test_classify_topic_with_classifier_wrapper():
    pred = classify_topic("Forecast", "We trained a model.", _FakeClassifier())
    assert pred.topic == "data_ai"
    assert pred.score == 0.77
