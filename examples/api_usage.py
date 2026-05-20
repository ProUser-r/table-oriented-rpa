from pathlib import Path

from rpa_table_robot import TableRobot


robot = TableRobot.from_env()
result = robot.process_images([Path("examples/table.png")], output_dir=Path("output"))

print(result.report)
