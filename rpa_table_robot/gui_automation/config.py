"""Configuration for GUI automation module."""

from __future__ import annotations

import os
from dataclasses import dataclass
from logging import INFO
from pathlib import Path

from dotenv import load_dotenv

from rpa_table_robot.config import RobotConfig


@dataclass(frozen=True)
class GUIAutomationConfig:
    """GUI automation configuration."""

    workflow_dir: Path = Path("./workflows")
    log_level: int = INFO
    browser_headless: bool = False
    robot_config: RobotConfig | None = None
    timeout: float = 30.0

    @classmethod
    def from_env(cls) -> "GUIAutomationConfig":
        """Load configuration from environment variables.

        Environment variables:
        - RPA_GUI_WORKFLOW_DIR: Path to workflow directory
        - RPA_GUI_LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        - RPA_GUI_BROWSER_HEADLESS: Browser headless mode (true/false)
        - RPA_GUI_TIMEOUT: Global timeout in seconds
        """
        load_dotenv()

        workflow_dir = Path(
            os.getenv("RPA_GUI_WORKFLOW_DIR", str(cls.workflow_dir))
        )

        log_level_str = os.getenv("RPA_GUI_LOG_LEVEL", "INFO").upper()
        log_level_map = {
            "DEBUG": 10,
            "INFO": 20,
            "WARNING": 30,
            "ERROR": 40,
            "CRITICAL": 50,
        }
        log_level = log_level_map.get(log_level_str, INFO)

        browser_headless = os.getenv("RPA_GUI_BROWSER_HEADLESS", "false").lower() == "true"
        timeout = float(os.getenv("RPA_GUI_TIMEOUT", "30"))

        robot_config = RobotConfig.from_env()

        return cls(
            workflow_dir=workflow_dir,
            log_level=log_level,
            browser_headless=browser_headless,
            robot_config=robot_config,
            timeout=timeout,
        )

    def validate(self) -> None:
        """Validate configuration."""
        if not self.workflow_dir.exists():
            raise ValueError(f"Workflow directory does not exist: {self.workflow_dir}")

        if self.timeout <= 0:
            raise ValueError(f"Timeout must be positive: {self.timeout}")

        if self.robot_config:
            self.robot_config.validate()
