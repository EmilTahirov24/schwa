"""The torch side of the character tagger: the network, batching and checkpoints.

Kept apart from :mod:`schwa.tagger` so that importing the package never imports torch.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import torch
from torch import nn

from schwa.tagger import (
    CharVocabulary,
    TaggerConfig,
    config_from_dict,
    config_to_dict,
    window_bounds,
)

__all__ = ["CharTagger", "encode_batch", "load_predictor", "save_checkpoint"]

PAD_ID = 0


class CharTagger(nn.Module):
    """Bidirectional LSTM over characters with a two-way decision per position.

    Both directions matter here: whether ``e`` is really ``ə`` depends on the letters that
    follow as much as on the ones before.
    """

    def __init__(self, vocabulary_size: int, config: TaggerConfig) -> None:
        super().__init__()
        self.config = config
        self.embedding = nn.Embedding(vocabulary_size, config.embedding, padding_idx=PAD_ID)
        self.encoder = nn.LSTM(
            config.embedding,
            config.hidden,
            num_layers=config.layers,
            batch_first=True,
            bidirectional=True,
            dropout=config.dropout if config.layers > 1 else 0.0,
        )
        self.dropout = nn.Dropout(config.dropout)
        self.head = nn.Linear(2 * config.hidden, 2)

    def forward(self, ids: torch.Tensor) -> torch.Tensor:
        embedded = self.dropout(self.embedding(ids))
        encoded, _ = self.encoder(embedded)
        return self.head(self.dropout(encoded))


def encode_batch(
    texts: Sequence[str],
    vocabulary: CharVocabulary,
    device: torch.device | str = "cpu",
) -> tuple[torch.Tensor, torch.Tensor]:
    """Return padded character ids and a mask marking the real characters."""
    encoded = [vocabulary.encode(text) for text in texts]
    # At least one column: an LSTM cannot be given a zero-length sequence.
    width = max((len(row) for row in encoded), default=1) or 1

    ids = torch.full((len(encoded), width), PAD_ID, dtype=torch.long)
    mask = torch.zeros((len(encoded), width), dtype=torch.bool)
    for row, values in enumerate(encoded):
        ids[row, : len(values)] = torch.tensor(values, dtype=torch.long)
        mask[row, : len(values)] = True

    return ids.to(device), mask.to(device)


# Shared with the ONNX runtimes, so every one of them cuts long text the same way.
_window_bounds = window_bounds


@torch.inference_mode()
def predict_labels(
    model: CharTagger,
    vocabulary: CharVocabulary,
    texts: Sequence[str],
    config: TaggerConfig,
    device: torch.device | str = "cpu",
    batch_size: int = 128,
) -> list[list[int]]:
    """Predict one label per character for each text."""
    model.eval()
    labels: list[list[int]] = [[] for _ in texts]

    # One flat list of windows across all texts keeps the batches full even when the
    # texts differ wildly in length.
    pieces: list[tuple[int, int, int, str]] = []
    for index, text in enumerate(texts):
        for start, end, commit_start, commit_end in _window_bounds(
            len(text), config.window, config.overlap
        ):
            pieces.append((index, commit_start - start, commit_end - start, text[start:end]))

    predicted: list[list[int]] = []
    for offset in range(0, len(pieces), batch_size):
        batch = pieces[offset : offset + batch_size]
        ids, _ = encode_batch([piece[3] for piece in batch], vocabulary, device)
        choices = model(ids).argmax(dim=-1).tolist()
        predicted.extend(
            row[piece[1] : piece[2]] for row, piece in zip(choices, batch, strict=True)
        )

    for (index, _, _, _), row in zip(pieces, predicted, strict=True):
        labels[index].extend(row)

    return labels


def save_checkpoint(
    path: Path,
    model: CharTagger,
    vocabulary: CharVocabulary,
    config: TaggerConfig,
) -> None:
    """Write weights, vocabulary and configuration as one file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "characters": vocabulary.characters[2:],
            "config": config_to_dict(config),
        },
        path,
    )


def load_predictor(path: Path, device: str | None = None):
    """Return a batch predictor and the configuration stored with the checkpoint."""
    resolved = device or ("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(path, map_location=resolved, weights_only=True)

    vocabulary = CharVocabulary(checkpoint["characters"])
    config = config_from_dict(checkpoint["config"])
    model = CharTagger(len(vocabulary), config).to(resolved)
    model.load_state_dict(checkpoint["state_dict"])

    def predict(texts: Sequence[str]) -> list[list[int]]:
        return predict_labels(model, vocabulary, texts, config, device=resolved)

    return predict, config
