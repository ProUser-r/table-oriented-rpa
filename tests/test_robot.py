from pathlib import Path

import pandas as pd

from rpa_table_robot import RobotConfig, TableRobot


class FakeOcrClient:
    def health(self):
        return {"status": "ok", "device": "cpu"}

    def recognize(self, image_path):
        return {
            "engine": {"name": "fake"},
            "tables": [
                {
                    "html": "<table><tr><th>A</th></tr><tr><td>1</td></tr></table>",
                    "confidence": 0.95,
                }
            ],
        }


class FakeReportGenerator:
    def build_report(self, tables, warnings):
        return f"tables={len(tables)} warnings={len(warnings)}"


def test_robot_process_images_and_exports(tmp_path):
    image = tmp_path / "table.png"
    image.write_bytes(b"not-a-real-image-for-mocked-client")
    robot = TableRobot(
        RobotConfig(),
        ocr_client=FakeOcrClient(),
        report_generator=FakeReportGenerator(),
    )

    result = robot.process_images([image], output_dir=tmp_path / "out")

    assert len(result.tables) == 1
    assert isinstance(result.tables[0].dataframe, pd.DataFrame)
    assert result.report == "tables=1 warnings=0"
    assert result.artifacts is not None
    assert result.artifacts.workbook.exists()
    assert result.artifacts.json.exists()
    assert result.artifacts.markdown_report.exists()
