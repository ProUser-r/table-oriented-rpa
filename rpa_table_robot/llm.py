from __future__ import annotations

import httpx

from .config import RobotConfig
from .models import RecognizedTable
from .report import build_fallback_report, tables_for_llm


class ReportGenerator:
    def __init__(self, config: RobotConfig):
        self.config = config

    def build_report(self, tables: list[RecognizedTable], warnings: list[str]) -> str:
        fallback = build_fallback_report(tables, warnings)
        if not self.config.llm_api_key:
            return fallback
        try:
            llm_report = self._build_llm_report(tables, warnings)
        except httpx.HTTPError as exc:
            return (
                fallback
                + "\n## LLM Report Warning\n"
                + f"LLM summary failed: {exc.__class__.__name__}.\n"
            )
        return llm_report.strip() + "\n"

    def _build_llm_report(self, tables: list[RecognizedTable], warnings: list[str]) -> str:
        prompt = (
            "Сформируй краткий поверхностный отчет на русском языке по распознанным "
            "таблицам. Не выдумывай факты. Укажи размеры таблиц, заметные пропуски, "
            "числовые итоги/диапазоны, низкую уверенность OCR и 3-5 практичных "
            "наблюдений. Данные:\n"
            f"{tables_for_llm(tables)}\n\n"
            f"Warnings: {warnings}"
        )
        payload = {
            "model": self.config.llm_model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a concise data quality analyst for OCR table outputs.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self.config.llm_api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=90.0) as client:
            response = client.post(
                f"{self.config.llm_base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"]
