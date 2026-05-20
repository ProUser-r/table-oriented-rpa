from __future__ import annotations

import os
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from rpa_table_robot import TableRobot
from rpa_table_robot.exceptions import OcrServiceUnavailable


@pytest.mark.skipif(
    os.getenv("RPA_RUN_SIDECAR_SMOKE") != "1",
    reason="set RPA_RUN_SIDECAR_SMOKE=1 to run the real OCR sidecar smoke test",
)
def test_real_sidecar_smoke(tmp_path: Path) -> None:
    image_path = tmp_path / "sample_table.png"
    _create_sample_table_image(image_path)

    robot = TableRobot.from_env()
    try:
        result = robot.process_images([image_path], output_dir=tmp_path / "output")
    except OcrServiceUnavailable as exc:
        pytest.fail(str(exc))

    assert result.artifacts is not None
    assert result.artifacts.workbook.exists()
    assert result.artifacts.json.exists()
    assert result.artifacts.markdown_report.exists()
    assert result.tables, "The sidecar returned no recognized tables."
    assert result.tables[0].dataframe.shape[0] >= 1
    assert result.tables[0].dataframe.shape[1] >= 1


def _create_sample_table_image(path: Path) -> None:
    image = Image.new("RGB", (720, 360), "white")
    draw = ImageDraw.Draw(image)
    x0, y0 = 50, 60
    cell_w, cell_h = 155, 64
    rows = [
        ["Name", "Qty", "Price", "Total"],
        ["Paper", "2", "50", "100"],
        ["Pen", "5", "20", "100"],
        ["Sum", "", "", "200"],
    ]
    for row in range(len(rows) + 1):
        y = y0 + row * cell_h
        draw.line((x0, y, x0 + cell_w * 4, y), fill="black", width=3)
    for col in range(5):
        x = x0 + col * cell_w
        draw.line((x, y0, x, y0 + cell_h * len(rows)), fill="black", width=3)
    for row_index, row in enumerate(rows):
        for col_index, value in enumerate(row):
            draw.text(
                (x0 + col_index * cell_w + 16, y0 + row_index * cell_h + 20),
                value,
                fill="black",
            )
    image.save(path)
