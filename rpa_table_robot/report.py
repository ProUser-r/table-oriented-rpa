from __future__ import annotations

import json
from typing import Any

import pandas as pd

from .models import RecognizedTable


def build_fallback_report(tables: list[RecognizedTable], warnings: list[str]) -> str:
    lines = ["# Table Recognition Report", ""]
    lines.append(f"Recognized tables: {len(tables)}")
    if warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in warnings)

    for table in tables:
        lines.extend(["", f"## Table {table.table_index}: {table.source_image.name}"])
        summary = summarize_table(table)
        lines.append(f"- Shape: {summary['rows']} rows x {summary['columns']} columns")
        lines.append(f"- Empty cells: {summary['empty_cells']}")
        if table.confidence is not None:
            lines.append(f"- OCR confidence: {table.confidence:.2f}")
        if summary["headers"]:
            lines.append(f"- Headers: {', '.join(summary['headers'])}")
        if summary["numeric_columns"]:
            lines.append("- Numeric columns:")
            for item in summary["numeric_columns"]:
                lines.append(
                    f"  - {item['name']}: count={item['count']}, "
                    f"min={item['min']}, max={item['max']}, sum={item['sum']}"
                )
        if table.warnings:
            lines.append("- Table warnings:")
            lines.extend(f"  - {warning}" for warning in table.warnings)

    return "\n".join(lines).strip() + "\n"


def summarize_table(table: RecognizedTable) -> dict[str, Any]:
    df = table.dataframe
    headers = _headers(df)
    numeric_columns = []
    for column in df.columns:
        series = pd.to_numeric(df[column], errors="coerce")
        non_null = series.dropna()
        if non_null.empty:
            continue
        numeric_columns.append(
            {
                "name": str(column),
                "count": int(non_null.count()),
                "min": _json_number(non_null.min()),
                "max": _json_number(non_null.max()),
                "sum": _json_number(non_null.sum()),
            }
        )
    return {
        "source_image": str(table.source_image),
        "table_index": table.table_index,
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "headers": headers,
        "empty_cells": int((df.astype(str).map(lambda value: value.strip() == "")).sum().sum())
        if not df.empty
        else 0,
        "confidence": table.confidence,
        "warnings": table.warnings,
        "numeric_columns": numeric_columns,
    }


def tables_for_llm(tables: list[RecognizedTable]) -> str:
    payload = []
    for table in tables:
        records = table.dataframe.head(20).astype(str).to_dict(orient="records")
        payload.append(
            {
                "source_image": str(table.source_image),
                "table_index": table.table_index,
                "summary": summarize_table(table),
                "sample_records": records,
            }
        )
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _headers(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return []
    headers = [str(column).strip() for column in df.columns]
    if headers and not all(header.isdigit() for header in headers):
        return [header for header in headers if header]
    first_row = [str(value).strip() for value in df.iloc[0].tolist()]
    return [value for value in first_row if value]


def _json_number(value: Any) -> int | float:
    if pd.isna(value):
        return 0
    value = float(value)
    return int(value) if value.is_integer() else value
