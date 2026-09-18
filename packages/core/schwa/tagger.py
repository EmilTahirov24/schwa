"""The character tagger: decide for every character whether it carries a diacritic.

Unlike the lexicon and the context model, this one does not need to have seen a word before.
That is the point: most remaining errors are rare proper nouns that never appear in the
training text, and a word-level system can only leave those as typed.

Torch is imported lazily, so installing ``schwa`` does not drag a deep learning framework
onto machines that only want to restore text with the lexicon.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from schwa.alphabet import (
    LABEL_KEEP,
    LABEL_MARK,
    apply_labels,
    is_foldable,
    strip_diacritics,
    to_labels,
)

__all__ = ["CharVocabulary", "TaggerConfig", "TaggerRestorer", "restore_with_labels"]

PAD = "\x00"
UNKNOWN = "\x01"


@dataclass(frozen=True)
class TaggerConfig:
    """Everything needed to rebuild the model around a checkpoint."""

    embedding: int = 96
    hidden: int = 256
    layers: int = 2
    dropout: float = 0.2
    window: int = 256
    #: Windows overlap by this many characters so that a character near a cut is still
    #: predicted with context on both sides.
    overlap: int = 32


class CharVocabulary:
    """Maps characters to ids, with slots for padding and unseen characters."""

    def __init__(self, characters: Sequence[str]) -> None:
        self.characters = [PAD, UNKNOWN, *characters]
        self._ids = {char: index for index, char in enumerate(self.characters)}

    @classmethod
    def from_texts(cls, texts: Iterable[str], min_count: int = 20) -> CharVocabulary:
        """Collect the characters worth an embedding of their own."""
        counts: Counter[str] = Counter()
        for text in texts:
            counts.update(strip_diacritics(text))
        kept = sorted(char for char, count in counts.items() if count >= min_count)
        return cls([char for char in kept if char not in (PAD, UNKNOWN)])

    def encode(self, text: str) -> list[int]:
        """Return one id per character."""
        unknown = self._ids[UNKNOWN]
        return [self._ids.get(char, unknown) for char in text]

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.characters[2:], ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> CharVocabulary:
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def __len__(self) -> int:
        return len(self.characters)


def restore_with_labels(text: str, predicted: Sequence[int]) -> str:
    """Apply predicted labels to ``text``, keeping the diacritics the user typed.

    Someone who typed ``mən sence`` already told us about the first word. Those characters
    keep their own reading and only the plain ASCII ones are left to the model.
    """
    typed, written = to_labels(text)
    labels = [
        LABEL_MARK if written[index] == LABEL_MARK else int(predicted[index])
        for index in range(len(typed))
    ]
    return apply_labels(typed, labels)


def window_bounds(length: int, window: int, overlap: int) -> list[tuple[int, int, int, int]]:
    """Split a long text into overlapping windows.

    Returns (start, end, commit_start, commit_end) per window: the model reads the whole
    window but only the committed part of it is used, so every predicted character had
    context on both sides.

    Every runtime - torch, onnxruntime in Python, onnxruntime in the browser - has to cut
    text the same way, or the same model gives different answers on long input. Keeping
    this in the torch-free module is what lets all of them share it.
    """
    if length <= window:
        return [(0, length, 0, length)]

    stride = window - overlap
    half = overlap // 2
    bounds: list[tuple[int, int, int, int]] = []

    for start in range(0, length, stride):
        end = min(start + window, length)
        commit_start = start if start == 0 else start + half
        commit_end = end if end == length else end - half
        bounds.append((start, end, commit_start, commit_end))
        if end == length:
            break

    return bounds


def foldable_positions(text: str) -> list[int]:
    """Indices where a decision is actually needed."""
    return [index for index, char in enumerate(text) if is_foldable(char)]


class TaggerRestorer:
    """Restores text with a character tagger.

    The predictor is injected, so the class can be tested without torch and can later be
    served from ONNX just as well as from a checkpoint.
    """

    name = "tagger"

    def __init__(
        self,
        predict: Callable[[Sequence[str]], list[list[int]]],
        config: TaggerConfig | None = None,
    ) -> None:
        self.predict = predict
        self.config = config or TaggerConfig()

    def restore(self, text: str) -> str:
        return self.restore_many([text])[0]

    def restore_many(self, texts: Sequence[str]) -> list[str]:
        """Restore a batch of texts; batching is what makes the model usable at scale."""
        if not texts:
            return []

        stripped = [strip_diacritics(text) for text in texts]
        predictions = self.predict(stripped)
        return [
            restore_with_labels(text, labels)
            for text, labels in zip(texts, predictions, strict=True)
        ]

    @classmethod
    def from_checkpoint(cls, path: Path, device: str | None = None) -> TaggerRestorer:
        """Load a trained checkpoint. Requires torch."""
        from schwa._tagger_model import load_predictor  # noqa: PLC0415

        predict, config = load_predictor(path, device=device)
        return cls(predict, config)


def config_to_dict(config: TaggerConfig) -> dict[str, float | int]:
    return asdict(config)


def config_from_dict(values: dict[str, float | int]) -> TaggerConfig:
    fields = {
        field: values[field] for field in TaggerConfig.__dataclass_fields__ if field in values
    }
    return TaggerConfig(**fields)  # type: ignore[arg-type]


__all__ += ["LABEL_KEEP", "config_from_dict", "config_to_dict", "foldable_positions"]
