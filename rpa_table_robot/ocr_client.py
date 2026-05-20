from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from .config import RobotConfig
from .exceptions import OcrRecognitionError, OcrServiceUnavailable


class OcrSidecarClient:
    def __init__(self, config: RobotConfig):
        self.config = config

    def health(self) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self.config.ocr_url}/health")
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            raise OcrServiceUnavailable(
                "OCR sidecar is unavailable. Start it with "
                "`docker compose up --build ocr-cpu`, or enable Docker Desktop "
                "WSL integration if Docker is not visible from WSL."
            ) from exc

    def recognize(self, image_path: Path) -> dict[str, Any]:
        params = {"device": self.config.ocr_device}
        try:
            with image_path.open("rb") as image_file:
                files = {"file": (image_path.name, image_file, "application/octet-stream")}
                with httpx.Client(timeout=self.config.ocr_timeout) as client:
                    response = client.post(
                        f"{self.config.ocr_url}/recognize",
                        params=params,
                        files=files,
                    )
            if response.status_code >= 400:
                detail = _extract_error_detail(response)
                raise OcrRecognitionError(detail)
            return response.json()
        except OcrRecognitionError:
            raise
        except httpx.HTTPError as exc:
            raise OcrServiceUnavailable(
                "OCR sidecar request failed. Check that the service is running at "
                f"{self.config.ocr_url}. For GPU mode, verify NVIDIA runtime/CUDA; "
                "for CPU mode, set RPA_OCR_DEVICE=cpu."
            ) from exc


def _extract_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text or f"OCR service failed with HTTP {response.status_code}"
    detail = payload.get("detail", payload)
    if isinstance(detail, str):
        return detail
    return str(detail)
