from pathlib import Path

import pandas as pd

from rpa_table_robot.models import RecognizedTable
from rpa_table_robot.report import build_fallback_report, summarize_table


def test_summarize_table_numeric_columns_and_empty_cells():
    table = RecognizedTable(
        source_image=Path("invoice.png"),
        table_index=1,
        dataframe=pd.DataFrame({"Name": ["A", "B", ""], "Amount": ["10", "20", ""]}),
        confidence=0.9,
    )

    summary = summarize_table(table)

    assert summary["rows"] == 3
    assert summary["columns"] == 2
    assert summary["empty_cells"] == 2
    assert summary["numeric_columns"][0]["name"] == "Amount"
    assert summary["numeric_columns"][0]["sum"] == 30


def test_build_fallback_report_contains_core_metrics():
    table = RecognizedTable(
        source_image=Path("invoice.png"),
        table_index=1,
        dataframe=pd.DataFrame({"Name": ["A"], "Amount": ["10"]}),
        confidence=0.8,
    )

    report = build_fallback_report([table], ["sample warning"])

    assert "Recognized tables: 1" in report
    assert "sample warning" in report
    assert "1 rows x 2 columns" in report
