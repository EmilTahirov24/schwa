"""Scoring a restorer.

The headline number is accuracy on ambiguous words: the ones whose typed form stands for
more than one real word. Overall accuracy is reported too, but it starts high before any
model exists, because most words are unambiguous once the diacritics are dropped.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from schwa.alphabet import strip_diacritics
from schwa.lexicon import Lexicon
from schwa.tokenize import iter_words, key_of

__all__ = ["Scores", "evaluate"]


@dataclass
class Scores:
    """Counts and the rates derived from them."""

    words: int = 0
    words_correct: int = 0
    ambiguous_words: int = 0
    ambiguous_correct: int = 0
    characters: int = 0
    characters_wrong: int = 0
    sentences: int = 0
    sentences_correct: int = 0
    unseen_words: int = 0
    errors: list[tuple[str, str, str]] = field(default_factory=list)

    @property
    def word_accuracy(self) -> float:
        return self.words_correct / self.words if self.words else 0.0

    @property
    def ambiguous_accuracy(self) -> float:
        return self.ambiguous_correct / self.ambiguous_words if self.ambiguous_words else 0.0

    @property
    def character_error_rate(self) -> float:
        return self.characters_wrong / self.characters if self.characters else 0.0

    @property
    def sentence_accuracy(self) -> float:
        return self.sentences_correct / self.sentences if self.sentences else 0.0

    def as_dict(self) -> dict[str, float | int]:
        return {
            "words": self.words,
            "word_accuracy": round(self.word_accuracy, 4),
            "ambiguous_words": self.ambiguous_words,
            "ambiguous_accuracy": round(self.ambiguous_accuracy, 4),
            "character_error_rate": round(self.character_error_rate, 4),
            "sentences": self.sentences,
            "sentence_accuracy": round(self.sentence_accuracy, 4),
            "unseen_words": self.unseen_words,
        }


def evaluate(
    references: Iterable[str],
    predictions: Iterable[str],
    lexicon: Lexicon,
    keep_errors: int = 200,
) -> Scores:
    """Compare predictions against the correctly spelled references.

    Both sides must have the same text once diacritics are removed; a restorer that fails
    that is broken, not merely inaccurate.
    """
    scores = Scores()

    for reference, prediction in zip(references, predictions, strict=True):
        if strip_diacritics(reference) != strip_diacritics(prediction):
            raise ValueError(
                "prediction changed more than diacritics:\n"
                f"  reference:  {reference!r}\n"
                f"  prediction: {prediction!r}"
            )

        scores.sentences += 1
        scores.sentences_correct += reference == prediction
        scores.characters += len(reference)
        scores.characters_wrong += sum(
            1 for left, right in zip(reference, prediction, strict=True) if left != right
        )

        for start, end in iter_words(reference):
            expected = reference[start:end]
            produced = prediction[start:end]
            key = key_of(expected)
            correct = expected == produced

            scores.words += 1
            scores.words_correct += correct
            if key not in lexicon:
                scores.unseen_words += 1
            if lexicon.is_ambiguous(key):
                scores.ambiguous_words += 1
                scores.ambiguous_correct += correct
            if not correct and len(scores.errors) < keep_errors:
                scores.errors.append((key, expected, produced))

    return scores
