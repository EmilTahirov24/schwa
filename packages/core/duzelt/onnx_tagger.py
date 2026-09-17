"""Run the character tagger from an ONNX file instead of a torch checkpoint.

Two reasons this exists. The service can then run without torch, which takes a container
image from gigabytes to tens of megabytes, and the same file is what the extension will load
to restore text inside the browser, so that nothing has to be sent anywhere at all.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from duzelt.tagger import CharVocabulary, TaggerConfig, TaggerRestorer, config_from_dict

__all__ = ["load_onnx_predictor", "load_onnx_restorer", "sidecar_path"]


def sidecar_path(model_path: Path) -> Path:
    """Where the vocabulary and configuration sit next to an ONNX file."""
    return model_path.with_suffix(".json")


def load_onnx_predictor(model_path: Path, batch_size: int = 64):
    """Return a predictor backed by onnxruntime, plus the model's configuration."""
    import numpy as np
    import onnxruntime

    meta = json.loads(sidecar_path(model_path).read_text(encoding="utf-8"))
    vocabulary = CharVocabulary(meta["characters"])
    config = config_from_dict(meta["config"])

    session = onnxruntime.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name

    def predict(texts: Sequence[str]) -> list[list[int]]:
        labels: list[list[int]] = []

        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            encoded = [vocabulary.encode(text) for text in batch]
            width = max((len(row) for row in encoded), default=1)

            ids = np.zeros((len(batch), width), dtype=np.int64)
            for row, values in enumerate(encoded):
                ids[row, : len(values)] = values

            logits = session.run(None, {input_name: ids})[0]
            choices = logits.argmax(axis=-1)
            labels.extend(choices[row, : len(text)].tolist() for row, text in enumerate(batch))

        return labels

    return predict, config


def load_onnx_restorer(model_path: Path) -> TaggerRestorer:
    """A restorer that needs only onnxruntime."""
    predict, config = load_onnx_predictor(model_path)
    restorer = TaggerRestorer(predict, config)
    restorer.name = "tagger (onnx)"
    return restorer


def write_sidecar(model_path: Path, vocabulary: CharVocabulary, config: TaggerConfig) -> Path:
    """Store what the ONNX graph does not carry: the character ids and the window sizes."""
    from duzelt.tagger import config_to_dict

    path = sidecar_path(model_path)
    path.write_text(
        json.dumps(
            {"characters": vocabulary.characters[2:], "config": config_to_dict(config)},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path
