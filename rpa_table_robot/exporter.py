from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .models import ArtifactPaths, RecognizedTable
from .report import summarize_table


def export_result(tables: list[RecognizedTable], report: str, output_dir: Path) -> ArtifactPaths:
    output_dir.mkdir(parents=True, exist_ok=True)
    workbook = output_dir / "recognized_tables.xlsx"
    json_path = output_dir / "recognized_tables.json"
    markdown_path = output_dir / "report.md"
    csv_files = []

    with workbook.open("wb"):
        pass
    with _excel_writer(workbook) as writer:
        if not tables:
            import pandas as pd

            pd.DataFrame({"message": ["No tables recognized"]}).to_excel(
                writer, sheet_name="summary", index=False
            )
        for table in tables:
            sheet = _sheet_name(table)
            table.dataframe.to_excel(writer, sheet_name=sheet, index=False)

    for table in tables:
        csv_path = output_dir / f"{_file_stem(table)}.csv"
        table.dataframe.to_csv(csv_path, index=False, encoding="utf-8-sig")
        csv_files.append(csv_path)

    json_path.write_text(
        json.dumps(_json_payload(tables), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    markdown_path.write_text(report, encoding="utf-8")
    return ArtifactPaths(
        output_dir=output_dir,
        workbook=workbook,
        json=json_path,
        markdown_report=markdown_path,
        csv_files=csv_files,
    )


def _excel_writer(path: Path):
    import pandas as pd

    return pd.ExcelWriter(path, engine="openpyxl")


def _json_payload(tables: list[RecognizedTable]) -> dict[str, Any]:
    return {
        "tables": [
            {
                "source_image": str(table.source_image),
                "table_index": table.table_index,
                "bbox": table.bbox,
                "confidence": table.confidence,
                "warnings": table.warnings,
                "metadata": table.metadata,
                "summary": summarize_table(table),
                "records": table.dataframe.astype(str).to_dict(orient="records"),
                "raw_cells": table.raw_cells,
                "html": table.html,
            }
            for table in tables
        ]
    }


def _sheet_name(table: RecognizedTable) -> str:
    return _sanitize(f"t{table.table_index}_{table.source_image.stem}")[:31] or "table"


def _file_stem(table: RecognizedTable) -> str:
    return _sanitize(f"table_{table.table_index}_{table.source_image.stem}") or f"table_{table.table_index}"


def _sanitize(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")
