from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .config import RobotConfig
from .exporter import export_result
from .llm import ReportGenerator
from .models import RobotResult
from .ocr_client import OcrSidecarClient
from .parser import tables_from_ocr_response


class TableRobot:
    def __init__(
        self,
        config: RobotConfig,
        ocr_client: OcrSidecarClient | None = None,
        report_generator: ReportGenerator | None = None,
    ):
        config.validate()
        self.config = config
        self.ocr_client = ocr_client or OcrSidecarClient(config)
        self.report_generator = report_generator or ReportGenerator(config)

    @classmethod
    def from_env(cls) -> "TableRobot":
        return cls(RobotConfig.from_env())

    def process_images(
        self,
        image_paths: Iterable[str | Path],
        output_dir: str | Path | None = None,
    ) -> RobotResult:
        paths = [Path(path) for path in image_paths]
        if not paths:
            raise ValueError("image_paths must contain at least one image")
        for path in paths:
            if not path.exists():
                raise FileNotFoundError(path)
            if not path.is_file():
                raise ValueError(f"Not a file: {path}")

        warnings: list[str] = []
        engine_metadata = {"ocr_health": self.ocr_client.health()}
        tables = []
        for path in paths:
            response = self.ocr_client.recognize(path)
            engine_metadata.setdefault("recognition", []).append(response.get("engine", {}))
            image_warnings = list(response.get("warnings") or [])
            warnings.extend(f"{path.name}: {warning}" for warning in image_warnings)
            tables.extend(
                tables_from_ocr_response(
                    response,
                    source_image=path,
                    low_confidence_threshold=self.config.low_confidence_threshold,
                )
            )

        if not tables:
            warnings.append("No tables were recognized in the provided images.")

        report = self.report_generator.build_report(tables, warnings)
        artifacts = export_result(tables, report, Path(output_dir)) if output_dir else None
        return RobotResult(
            tables=tables,
            report=report,
            artifacts=artifacts,
            warnings=warnings,
            engine_metadata=engine_metadata,
        )
