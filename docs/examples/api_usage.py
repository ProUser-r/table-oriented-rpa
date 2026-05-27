from pathlib import Path
import os

from rpa_table_robot import TableRobot

os.environ["RPA_OCR_DEVICE"] = "gpu"
robot = TableRobot.from_env()
result = robot.process_images([Path("./test_table.png")], output_dir=Path("output"))

print(result.report)
