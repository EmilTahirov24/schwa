"""Scoring a restorer.

The headline number is accuracy on ambiguous words: the ones whose typed form stands for
more than one real word. Overall accuracy is reported too, but it starts high before any
model exists, because most words are unambiguous once the diacritics are dropped.

How far a number can be trusted is measured with a bootstrap over groups of sentences.
Sentences from one article share its names and its topic, so they are not independent, and
resampling them one by one would report intervals narrower than the truth.
"""

from __future__ import annotations

from collections.abc import Hashable, Iterable, Sequence
from dataclasses import dataclass, field

from schwa.alphabet import strip_diacritics
from schwa.lexicon import Lexicon
from schwa.tokenize import iter_words, key_of

__all__ = ["COUNTS", "RATES", "Interval", "Scores", "bootstrap", "evaluate"]

# The per-group counts a bootstrap adds up, in this order.
COUNTS = (
    "words",
    "words_correct",
    "ambiguous_words",
    "ambiguous_correct",
    "characters",
    "characters_wrong",
    "sentences",
    "sentences_correct",
)

# Every reported rate is one count over another.
RATES = {
    "ambiguous_accuracy": ("ambiguous_correct", "ambiguous_words"),
    "word_accuracy": ("words_correct", "words"),
    "character_error_rate": ("characters_wrong", "characters"),
    "sentence_accuracy": ("sentences_correct", "sentences"),
}


_END = object()


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
    # The same counts per group of sentences, in COUNTS order, when groups were given.
    by_group: dict[Hashable, list[int]] = field(default_factory=dict)

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
    groups: Iterable[Hashable] | None = None,
) -> Scores:
    """Compare predictions against the correctly spelled references.

    Both sides must have the same text once diacritics are removed; a restorer that fails
    that is broken, not merely inaccurate. `groups`, one label per sentence, keeps the counts
    of each group apart as well, which is what `bootstrap` needs.
    """
    scores = Scores()
    pairs = zip(references, predictions, strict=True)
    labels = iter(groups) if groups is not None else None

    for reference, prediction in pairs:
        if strip_diacritics(reference) != strip_diacritics(prediction):
            raise ValueError(
                "prediction changed more than diacritics:\n"
                f"  reference:  {reference!r}\n"
                f"  prediction: {prediction!r}"
            )

        words = words_correct = ambiguous = ambiguous_correct = 0
        for start, end in iter_words(reference):
            expected = reference[start:end]
            produced = prediction[start:end]
            key = key_of(expected)
            correct = expected == produced

            words += 1
            words_correct += correct
            if key not in lexicon:
                scores.unseen_words += 1
            if lexicon.is_ambiguous(key):
                ambiguous += 1
                ambiguous_correct += correct
            if not correct and len(scores.errors) < keep_errors:
                scores.errors.append((key, expected, produced))

        characters_wrong = sum(
            1 for left, right in zip(reference, prediction, strict=True) if left != right
        )
        counts = (
            words,
            words_correct,
            ambiguous,
            ambiguous_correct,
            len(reference),
            characters_wrong,
            1,
            int(reference == prediction),
        )
        for name, value in zip(COUNTS, counts, strict=True):
            setattr(scores, name, getattr(scores, name) + value)

        if labels is not None:
            try:
                label = next(labels)
            except StopIteration:
                raise ValueError("fewer group labels than sentences") from None
            totals = scores.by_group.setdefault(label, [0] * len(COUNTS))
            for index, value in enumerate(counts):
                totals[index] += value

    if labels is not None and next(labels, _END) is not _END:
        raise ValueError("more group labels than sentences")
    return scores


@dataclass(frozen=True)
class Interval:
    low: float
    high: float


def bootstrap(
    systems: Sequence[Scores],
    resamples: int = 1000,
    level: float = 0.95,
    seed: int = 0,
    pairs: Sequence[tuple[int, int]] | None = None,
) -> tuple[list[dict[str, Interval]], list[dict[str, Interval]]]:
    """Percentile intervals for every rate, resampling whole groups with replacement.

    Every system is scored on the same resamples, so the second list is a paired
    comparison: for each `(before, after)` pair of indices - by default each system and the
    one before it - the interval of `after` minus `before`. It answers whether one system
    beats another on this data, which two overlapping intervals cannot.
    """
    import numpy as np

    if not systems:
        return [], []
    if pairs is None:
        pairs = [(index - 1, index) for index in range(1, len(systems))]
    labels = list(systems[0].by_group)
    if not labels:
        raise ValueError("scores carry no groups; pass groups= to evaluate()")
    for scores in systems[1:]:
        if scores.by_group.keys() != systems[0].by_group.keys():
            raise ValueError("systems were scored on different groups")

    # counts[g, s, c]: count c of system s within group g.
    counts = np.array(
        [[scores.by_group[label] for scores in systems] for label in labels], dtype=np.float64
    )
    group_count, system_count, _ = counts.shape
    flat = counts.reshape(group_count, -1)

    rng = np.random.default_rng(seed)
    totals = np.empty((resamples, system_count, len(COUNTS)))
    chunk = max(1, 4_000_000 // group_count)
    for start in range(0, resamples, chunk):
        size = min(chunk, resamples - start)
        # Draw group_count groups per resample, then count how often each one came up.
        draws = rng.integers(0, group_count, size=(size, group_count))
        draws += np.arange(size)[:, None] * group_count
        weights = np.bincount(draws.ravel(), minlength=size * group_count)
        weights = weights.reshape(size, group_count).astype(np.float64)
        totals[start : start + size] = (weights @ flat).reshape(size, system_count, -1)

    tail = (1 - level) / 2 * 100
    rates = {}
    for name, (numerator, denominator) in RATES.items():
        above = totals[:, :, COUNTS.index(numerator)]
        below = totals[:, :, COUNTS.index(denominator)]
        rates[name] = np.divide(above, below, out=np.zeros_like(above), where=below > 0)

    def interval(samples) -> Interval:
        low, high = np.percentile(samples, [tail, 100 - tail])
        return Interval(float(low), float(high))

    per_system = [
        {name: interval(values[:, index]) for name, values in rates.items()}
        for index in range(system_count)
    ]
    differences = [
        {name: interval(values[:, after] - values[:, before]) for name, values in rates.items()}
        for before, after in pairs
    ]
    return per_system, differences
