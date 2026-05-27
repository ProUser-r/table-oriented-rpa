from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from rpa_table_robot.classifier import RubertTopicClassifier
from rpa_table_robot.models import RobotResult


TOPIC_COLUMN_ALIASES = {
    "тема",
    "theme",
    "subject",
}
TEXT_COLUMN_ALIASES = {
    "текст письма",
    "текст",
    "message",
    "body",
    "email_text",
}


@dataclass
class MessageRow:
    table_index: int
    row_index: int
    subject: str
    body: str
    first_sentence: str


@dataclass
class TopicPrediction:
    topic: str
    score: float


@dataclass
class PreparedEmail:
    message: MessageRow
    prediction: TopicPrediction
    recipients: list[str]


@dataclass
class DispatchResult:
    processed_rows: int = 0
    sent_count: int = 0
    skipped_rows: int = 0
    errors: list[str] = field(default_factory=list)


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", str(name).strip().lower())


def _pick_column(columns: Iterable[str], aliases: set[str]) -> str | None:
    for col in columns:
        if _norm(col) in aliases:
            return col
    return None


def first_sentence(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if not cleaned:
        return ""
    match = re.search(r"(.+?[.!?])(?:\s|$)", cleaned)
    if match:
        return match.group(1).strip()
    return cleaned


def extract_messages_from_tables(robot_result: RobotResult) -> list[MessageRow]:
    rows: list[MessageRow] = []
    for table in robot_result.tables:
        df = table.dataframe
        if df is None or df.empty:
            continue

        subject_col = _pick_column(df.columns, TOPIC_COLUMN_ALIASES)
        text_col = _pick_column(df.columns, TEXT_COLUMN_ALIASES)
        if not subject_col or not text_col:
            continue

        for idx, rec in df.iterrows():
            subject = str(rec.get(subject_col, "") or "").strip()
            body = str(rec.get(text_col, "") or "").strip()
            if not subject or not body:
                continue
            rows.append(
                MessageRow(
                    table_index=table.table_index,
                    row_index=int(idx),
                    subject=subject,
                    body=body,
                    first_sentence=first_sentence(body),
                )
            )
    return rows


def classify_topic(
    subject: str,
    first_sentence_text: str,
    classifier: RubertTopicClassifier,
) -> TopicPrediction:
    topic, score = classifier.predict(subject, first_sentence_text)
    return TopicPrediction(topic=topic, score=score)


def resolve_recipients(sqlite_path: str | Path, topic: str) -> list[str]:
    db_path = Path(sqlite_path)
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite DB not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute("SELECT email FROM emails WHERE topic = ?", (topic,))
        emails = [str(row[0]).strip() for row in cur.fetchall() if row and row[0]]
    finally:
        conn.close()

    dedup: list[str] = []
    seen: set[str] = set()
    for email in emails:
        key = email.lower()
        if key in seen:
            continue
        seen.add(key)
        dedup.append(email)
    return dedup
