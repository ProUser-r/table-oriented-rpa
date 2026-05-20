from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Query, UploadFile

app = FastAPI(title="RPA Table Robot OCR Sidecar", version="0.1.0")


class PaddleTableEngine:
    def __init__(self) -> None:
        self._pipeline: Any | None = None
        self._device: str | None = None
        self._gpu_available = False
        self._paddle_version: str | None = None

    def health(self) -> dict[str, Any]:
        paddle_info = self._paddle_info()
        return {
            "status": "ok",
            "engine": "PaddleOCR PP-StructureV3",
            "loaded": self._pipeline is not None,
            "device": self._device,
            **paddle_info,
        }

    def recognize(self, image_path: Path, requested_device: str) -> dict[str, Any]:
        device = self._resolve_device(requested_device)
        pipeline = self._get_pipeline(device)
        raw_result = self._predict(pipeline, image_path)
        normalized = normalize_paddle_result(raw_result)
        normalized["engine"] = {
            "name": "PaddleOCR PP-StructureV3",
            "device": device,
            "requested_device": requested_device,
        }
        return normalized

    def _get_pipeline(self, device: str) -> Any:
        if self._pipeline is not None and self._device == device:
            return self._pipeline
        try:
            from paddleocr import PPStructureV3
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"PaddleOCR PP-StructureV3 is not installed or failed to import: {exc}",
            ) from exc

        errors = []
        attempts = []
        if device == "cpu":
            attempts.extend(
                [
                    {"device": "cpu", "enable_mkldnn": False},
                    {"device": "cpu"},
                ]
            )
        else:
            attempts.extend(
                [
                    {"device": "gpu:0"},
                    {"device": "gpu"},
                ]
            )
        attempts.append({})
        for kwargs in attempts:
            try:
                self._pipeline = PPStructureV3(**kwargs)
                self._device = device
                return self._pipeline
            except TypeError as exc:
                errors.append(f"{kwargs}: {exc}")
            except Exception as exc:
                errors.append(f"{kwargs}: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Unable to initialize PP-StructureV3. Attempts: " + " | ".join(errors),
        )

    def _predict(self, pipeline: Any, image_path: Path) -> Any:
        errors = []
        for call in (
            lambda: pipeline.predict(str(image_path)),
            lambda: pipeline.predict(input=str(image_path)),
            lambda: pipeline(str(image_path)),
        ):
            try:
                return call()
            except TypeError as exc:
                errors.append(str(exc))
                continue
            except Exception as exc:
                raise HTTPException(
                    status_code=500,
                    detail=f"PP-StructureV3 prediction failed: {exc.__class__.__name__}: {exc}",
                ) from exc
        raise HTTPException(
            status_code=500,
            detail="PP-StructureV3 prediction API is unsupported. Attempts: " + " | ".join(errors),
        )

    def _resolve_device(self, requested_device: str) -> str:
        requested_device = requested_device.lower()
        if requested_device not in {"cpu", "auto", "gpu"}:
            raise HTTPException(status_code=400, detail="device must be one of: cpu, auto, gpu")
        info = self._paddle_info()
        gpu_available = bool(info["gpu_available"])
        if requested_device == "gpu" and not gpu_available:
            raise HTTPException(
                status_code=503,
                detail=(
                    "GPU was requested, but Paddle cannot see CUDA/NVIDIA runtime. "
                    "Run the gpu compose profile with NVIDIA Container Toolkit, or set "
                    "RPA_OCR_DEVICE=cpu."
                ),
            )
        if requested_device == "auto":
            return "gpu" if gpu_available else "cpu"
        return requested_device

    def _paddle_info(self) -> dict[str, Any]:
        try:
            import paddle

            compiled = bool(paddle.is_compiled_with_cuda())
            count = 0
            if compiled:
                try:
                    count = int(paddle.device.cuda.device_count())
                except Exception:
                    count = 0
            self._gpu_available = compiled and count > 0
            self._paddle_version = getattr(paddle, "__version__", None)
            return {
                "paddle_version": self._paddle_version,
                "cuda_compiled": compiled,
                "gpu_count": count,
                "gpu_available": self._gpu_available,
            }
        except Exception as exc:
            return {
                "paddle_version": None,
                "cuda_compiled": False,
                "gpu_count": 0,
                "gpu_available": False,
                "paddle_error": str(exc),
            }


engine = PaddleTableEngine()


@app.get("/health")
def health() -> dict[str, Any]:
    return engine.health()


@app.post("/recognize")
async def recognize(
    file: UploadFile = File(...),
    device: str | None = Query(default=None),
) -> dict[str, Any]:
    requested_device = device or os.getenv("RPA_OCR_DEVICE", "cpu")
    suffix = Path(file.filename or "image").suffix or ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)
    try:
        return engine.recognize(tmp_path, requested_device=requested_device)
    finally:
        tmp_path.unlink(missing_ok=True)


def normalize_paddle_result(raw_result: Any) -> dict[str, Any]:
    items = list(raw_result) if isinstance(raw_result, (list, tuple)) else [raw_result]
    tables = []
    warnings = []
    for item in items:
        payload = _to_plain(item)
        table_items = _find_table_payloads(payload)
        if not table_items:
            warnings.append("No table payload found in PaddleOCR result item.")
        for table in table_items:
            html = _first_present(table, "html", "table_html", "pred_html", "res_html")
            cells = _first_present(table, "cells", "table_cells", "cell_bbox", default=[])
            confidence = _first_present(table, "confidence", "score", "rec_score", "table_score")
            bbox = _first_present(table, "bbox", "box", "layout_bbox")
            rows = _first_present(table, "rows", "data", default=None)
            if not html and not cells and rows is None:
                continue
            tables.append(
                {
                    "html": html,
                    "cells": cells or [],
                    "rows": rows,
                    "bbox": bbox,
                    "confidence": confidence,
                    "metadata": {"raw_type": type(item).__name__},
                    "warnings": [],
                }
            )
    return {"tables": tables, "warnings": warnings}


def _to_plain(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(key): _to_plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(item) for item in value]
    for attr in ("json", "res", "dict", "data"):
        if hasattr(value, attr):
            candidate = getattr(value, attr)
            try:
                return _to_plain(candidate() if callable(candidate) else candidate)
            except Exception:
                continue
    if hasattr(value, "__dict__"):
        return _to_plain(vars(value))
    return str(value)


def _find_table_payloads(payload: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        label = str(payload.get("type") or payload.get("label") or payload.get("category") or "").lower()
        has_table_content = any(
            key in payload for key in ("html", "table_html", "pred_html", "res_html", "cells", "rows")
        )
        if "table" in label or has_table_content:
            found.append(payload)
        for value in payload.values():
            found.extend(_find_table_payloads(value))
    elif isinstance(payload, list):
        for value in payload:
            found.extend(_find_table_payloads(value))
    return found


def _first_present(payload: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return default
