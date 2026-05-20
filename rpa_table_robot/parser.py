from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd

from .models import RecognizedTable


def tables_from_ocr_response(
    response: dict[str, Any],
    source_image: Path,
    low_confidence_threshold: float,
) -> list[RecognizedTable]:
    tables: list[RecognizedTable] = []
    for index, item in enumerate(response.get("tables", []), start=1):
        dataframe = _dataframe_from_item(item)
        confidence = _coerce_confidence(item.get("confidence"))
        warnings = list(item.get("warnings") or [])
        if confidence is not None and confidence < low_confidence_threshold:
            warnings.append(
                f"Low OCR confidence: {confidence:.2f} "
                f"(threshold {low_confidence_threshold:.2f})"
            )
        tables.append(
            RecognizedTable(
                source_image=source_image,
                table_index=index,
                dataframe=dataframe,
                raw_cells=list(item.get("cells") or []),
                bbox=item.get("bbox"),
                confidence=confidence,
                html=item.get("html"),
                warnings=warnings,
                metadata=dict(item.get("metadata") or {}),
            )
        )
    return tables


def _dataframe_from_item(item: dict[str, Any]) -> pd.DataFrame:
    html = item.get("html")
    if html:
        try:
            tables = pd.read_html(StringIO(html))
            if tables:
                return tables[0].fillna("")
        except ValueError:
            pass

    rows = item.get("rows")
    if isinstance(rows, list):
        return pd.DataFrame(rows).fillna("")

    cells = item.get("cells")
    if isinstance(cells, list) and cells:
        return _dataframe_from_cells(cells)

    return pd.DataFrame()


def _dataframe_from_cells(cells: list[dict[str, Any]]) -> pd.DataFrame:
    max_row = 0
    max_col = 0
    for cell in cells:
        max_row = max(max_row, int(cell.get("row", 0)))
        max_col = max(max_col, int(cell.get("col", 0)))
    grid = [["" for _ in range(max_col + 1)] for _ in range(max_row + 1)]
    for cell in cells:
        row = int(cell.get("row", 0))
        col = int(cell.get("col", 0))
        grid[row][col] = str(cell.get("text", ""))
    return pd.DataFrame(grid).fillna("")


def _coerce_confidence(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
