# RPA Table Robot

Интеллектуальный Python API для распознавания таблиц на изображениях, восстановления `pandas.DataFrame` и формирования поверхностного отчета.

Архитектура:

- управляющий пакет `rpa_table_robot` работает в текущем `rpa_venv` на Python 3.14;
- тяжелое OCR/TSR-распознавание вынесено в Docker sidecar на совместимом Python с PaddleOCR PP-StructureV3;
- LLM-сводка подключается через OpenAI-compatible API и автоматически заменяется fallback-отчетом, если ключ не задан;
- CPU режим включен по умолчанию, GPU доступен опционально через отдельный compose profile.

## Установка Python API

```bash
./rpa_venv/bin/python -m pip install -r requirements-dev.txt
```

## Запуск OCR sidecar

CPU:

```bash
docker compose up --build ocr-cpu
```

GPU:

```bash
RPA_OCR_DEVICE=gpu docker compose --profile gpu up --build ocr-gpu
```

Если Docker в WSL не виден, включите Docker Desktop WSL integration для текущего дистрибутива.

## Использование API

```python
from pathlib import Path
from rpa_table_robot import TableRobot

robot = TableRobot.from_env()
result = robot.process_images(
    [Path("examples/table.png")],
    output_dir=Path("output"),
)

print(result.report)
print(result.tables[0].dataframe)
print(result.artifacts)
```

## Переменные окружения

- `RPA_OCR_URL`: URL sidecar, по умолчанию `http://127.0.0.1:8765`.
- `RPA_OCR_DEVICE`: `cpu`, `auto` или `gpu`, по умолчанию `cpu`.
- `RPA_OCR_TIMEOUT`: timeout запросов к OCR, по умолчанию `300`.
- `RPA_LLM_BASE_URL`: OpenAI-compatible base URL, по умолчанию `https://api.openai.com/v1`.
- `RPA_LLM_API_KEY`: ключ LLM API. Если отсутствует, используется fallback-отчет.
- `RPA_LLM_MODEL`: модель для сводки, по умолчанию `gpt-4o-mini`.

## Проверки

```bash
./rpa_venv/bin/python -m pytest
```

Smoke test против реального sidecar:

```bash
docker compose up --build ocr-cpu
RPA_RUN_SIDECAR_SMOKE=1 ./rpa_venv/bin/python -m pytest tests/test_sidecar_smoke.py
```
