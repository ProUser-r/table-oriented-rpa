from __future__ import annotations

import json
from pathlib import Path


class RubertTopicClassifier:
    """Local wrapper around ruBERT topic classification model."""

    def __init__(self, model_dir: str | Path = "data/rubert_it_classifier"):
        self.model_dir = Path(model_dir)
        if not self.model_dir.exists():
            raise FileNotFoundError(f"Topic model directory not found: {self.model_dir}")

        config_path = self.model_dir / "config.json"
        if not config_path.exists():
            raise FileNotFoundError(f"Model config not found: {config_path}")

        config = json.loads(config_path.read_text(encoding="utf-8"))
        self.id2label: dict[int, str] = {
            int(k): str(v) for k, v in (config.get("id2label") or {}).items()
        }
        self.label2id: dict[str, int] = {
            str(k): int(v) for k, v in (config.get("label2id") or {}).items()
        }

        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except Exception as exc:
            raise RuntimeError(
                "RubertTopicClassifier requires 'transformers' and 'torch'. "
                "Install them before running classification."
            ) from exc

        self._torch = torch
        self._tokenizer = AutoTokenizer.from_pretrained(str(self.model_dir), local_files_only=True)
        self._model = AutoModelForSequenceClassification.from_pretrained(
            str(self.model_dir),
            local_files_only=True,
        )
        self._model.eval()

    def predict(self, subject: str, first_sentence: str) -> tuple[str, float]:
        """Predict topic label from subject + first sentence text."""
        text = f"{subject} [SEP] {first_sentence}".strip()
        if not text:
            raise ValueError("Classification input cannot be empty")

        encoded = self._tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        )
        with self._torch.no_grad():
            logits = self._model(**encoded).logits
            probs = self._torch.softmax(logits, dim=-1)[0]
            idx = int(self._torch.argmax(probs).item())
            score = float(probs[idx].item())

        label = self.id2label.get(idx)
        if label is None:
            raise RuntimeError(f"Predicted label index {idx} is missing in id2label")
        return label, score
