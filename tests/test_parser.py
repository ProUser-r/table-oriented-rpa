from pathlib import Path

from rpa_table_robot.parser import tables_from_ocr_response


def test_tables_from_html_with_low_confidence_warning():
    response = {
        "tables": [
            {
                "html": """
                <table>
                  <tr><th>Item</th><th>Amount</th></tr>
                  <tr><td>A</td><td>10</td></tr>
                  <tr><td>B</td><td>20</td></tr>
                </table>
                """,
                "confidence": 0.6,
            }
        ]
    }

    tables = tables_from_ocr_response(response, Path("sample.png"), 0.75)

    assert len(tables) == 1
    assert list(tables[0].dataframe.columns) == ["Item", "Amount"]
    assert tables[0].dataframe.shape == (2, 2)
    assert "Low OCR confidence" in tables[0].warnings[0]


def test_tables_from_cells_when_html_is_missing():
    response = {
        "tables": [
            {
                "cells": [
                    {"row": 0, "col": 0, "text": "Name"},
                    {"row": 0, "col": 1, "text": "Score"},
                    {"row": 1, "col": 0, "text": "Ivan"},
                    {"row": 1, "col": 1, "text": "5"},
                ]
            }
        ]
    }

    tables = tables_from_ocr_response(response, Path("sample.png"), 0.75)

    assert tables[0].dataframe.iloc[1, 0] == "Ivan"
    assert tables[0].dataframe.iloc[1, 1] == "5"
