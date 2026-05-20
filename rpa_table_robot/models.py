from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass
class RecognizedTable:
    source_image: Path
    table_index: int
    dataframe: pd.DataFrame
    raw_cells: list[dict[str, Any]] = field(default_factory=list)
    bbox: list[float] | None = None
    confidence: float | None = None
    html: str | None = None
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ArtifactPaths:
    output_dir: Path
    workbook: Path
    json: Path
    markdown_report: Path
    csv_files: list[Path]


@dataclass
class RobotResult:
    tables: list[RecognizedTable]
    report: str
    artifacts: ArtifactPaths | None = None
    warnings: list[str] = field(default_factory=list)
    engine_metadata: dict[str, Any] = field(default_factory=dict)
