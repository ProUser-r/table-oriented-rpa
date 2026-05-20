from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class RobotConfig:
    ocr_url: str = "http://127.0.0.1:8765"
    ocr_device: str = "cpu"
    ocr_timeout: float = 300.0
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    low_confidence_threshold: float = 0.75

    @classmethod
    def from_env(cls) -> "RobotConfig":
        load_dotenv()
        timeout = float(os.getenv("RPA_OCR_TIMEOUT", "300"))
        threshold = float(os.getenv("RPA_LOW_CONFIDENCE_THRESHOLD", "0.75"))
        return cls(
            ocr_url=os.getenv("RPA_OCR_URL", cls.ocr_url).rstrip("/"),
            ocr_device=os.getenv("RPA_OCR_DEVICE", cls.ocr_device).lower(),
            ocr_timeout=timeout,
            llm_base_url=os.getenv("RPA_LLM_BASE_URL", cls.llm_base_url).rstrip("/"),
            llm_api_key=os.getenv("RPA_LLM_API_KEY"),
            llm_model=os.getenv("RPA_LLM_MODEL", cls.llm_model),
            low_confidence_threshold=threshold,
        )

    def validate(self) -> None:
        if self.ocr_device not in {"cpu", "auto", "gpu"}:
            raise ValueError("RPA_OCR_DEVICE must be one of: cpu, auto, gpu")
