"""The context model: pick a word's spelling from the words next to it.

The lexicon restorer always answers the same way for a given typed word, so every
ambiguous word it gets wrong stays wrong. This model looks at the neighbours instead.

For each ambiguous key it scores a candidate form with a naive Bayes estimate,

    log P(form) + log P(left | form) + log P(right | form)

where the neighbours are represented by their *keys*, not their spellings. That matters:
at restoration time the neighbours are still typed without diacritics, so their spelling is
unknown, while their key is always observable. Training therefore uses the same features
the model will actually see.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["ContextModel", "END", "START", "UNKNOWN"]

START = "<s>"
END = "</s>"
UNKNOWN = "<unk>"


@dataclass
class KeyModel:
    """Counts for one ambiguous key."""

    forms: Counter[str] = field(default_factory=Counter)
    left: dict[str, Counter[str]] = field(default_factory=lambda: defaultdict(Counter))
    right: dict[str, Counter[str]] = field(default_factory=lambda: defaultdict(Counter))


class ContextModel:
    """Scores the candidate spellings of ambiguous words from their neighbours."""

    #: Add-k smoothing weight. Tuned on dev over 0.01 to 20: accuracy on ambiguous words
    #: peaks at 1.0 (85.8%) and falls off on both sides, to 80.6% at 0.01 and 84.1% at 20.
    DEFAULT_SMOOTHING = 1.0

    def __init__(
        self,
        keys: dict[str, KeyModel] | None = None,
        smoothing: float = DEFAULT_SMOOTHING,
        vocabulary: set[str] | None = None,
    ) -> None:
        self.keys: dict[str, KeyModel] = keys or {}
        self.smoothing = smoothing
        #: Neighbours outside this set become UNKNOWN. Kept with the model so that
        #: training and restoration always see the same features.
        self.vocabulary = vocabulary

    def feature(self, neighbour: str) -> str:
        """Map a neighbouring key to the feature the model was trained on."""
        if self.vocabulary is None or neighbour in (START, END):
            return neighbour
        return neighbour if neighbour in self.vocabulary else UNKNOWN

    def observe(self, key: str, form: str, left: str, right: str) -> None:
        """Record one occurrence of ``form`` between ``left`` and ``right``."""
        model = self.keys.get(key)
        if model is None:
            model = self.keys[key] = KeyModel()
        model.forms[form] += 1
        model.left[form][self.feature(left)] += 1
        model.right[form][self.feature(right)] += 1

    def score(self, key: str, form: str, left: str, right: str) -> float:
        """Log score of ``form`` for ``key`` in this context; higher is better."""
        model = self.keys.get(key)
        if model is None or form not in model.forms:
            return -math.inf

        total = sum(model.forms.values())
        score = math.log(model.forms[form] / total)
        score += self._conditional(model.left[form], self.feature(left))
        score += self._conditional(model.right[form], self.feature(right))
        return score

    def _conditional(self, counts: Counter[str], neighbour: str) -> float:
        """Smoothed log P(neighbour | form).

        Normalised by the counts actually kept for this form rather than by how often the
        form was seen. Pruning removes most contexts, so the two differ by a lot, and
        dividing by the wrong one makes forms with heavily pruned tables look impossible.
        The smoothing vocabulary is the same for every form for the same reason.
        """
        kept = sum(counts.values())
        numerator = counts.get(neighbour, 0) + self.smoothing
        denominator = kept + self.smoothing * self.feature_count
        return math.log(numerator / denominator)

    @property
    def feature_count(self) -> int:
        """Size of the feature space used for smoothing, shared by every form."""
        return len(self.vocabulary) + 3 if self.vocabulary else 50_000

    def best(self, key: str, left: str, right: str) -> str | None:
        """Return the highest scoring form for ``key``, or None if the key is unknown."""
        model = self.keys.get(key)
        if model is None:
            return None
        return max(model.forms, key=lambda form: self.score(key, form, left, right))

    def prune(self, min_context_count: int = 2, max_contexts: int = 100) -> None:
        """Drop rare and excess contexts, which are mostly noise and most of the size."""
        for model in self.keys.values():
            for side in (model.left, model.right):
                for form, counts in list(side.items()):
                    kept = Counter(
                        {
                            neighbour: count
                            for neighbour, count in counts.most_common(max_contexts)
                            if count >= min_context_count
                        }
                    )
                    side[form] = kept

    def save(self, path: Path) -> None:
        """Write the feature vocabulary, then one JSON object per key."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as out:
            meta = {"vocabulary": sorted(self.vocabulary) if self.vocabulary else None}
            out.write(json.dumps({"meta": meta}, ensure_ascii=False) + "\n")
            for key in sorted(self.keys):
                model = self.keys[key]
                row = {
                    "key": key,
                    "forms": dict(model.forms),
                    "left": {form: dict(counts) for form, counts in model.left.items()},
                    "right": {form: dict(counts) for form, counts in model.right.items()},
                }
                out.write(json.dumps(row, ensure_ascii=False) + "\n")

    @classmethod
    def load(cls, path: Path, smoothing: float = DEFAULT_SMOOTHING) -> ContextModel:
        """Read a model written by :meth:`save`."""
        keys: dict[str, KeyModel] = {}
        vocabulary: set[str] | None = None

        with path.open(encoding="utf-8") as source:
            for line in source:
                row = json.loads(line)
                if "meta" in row:
                    words = row["meta"].get("vocabulary")
                    vocabulary = set(words) if words else None
                    continue

                model = KeyModel(forms=Counter(row["forms"]))
                for form, counts in row["left"].items():
                    model.left[form] = Counter(counts)
                for form, counts in row["right"].items():
                    model.right[form] = Counter(counts)
                keys[row["key"]] = model

        return cls(keys, smoothing=smoothing, vocabulary=vocabulary)

    def __len__(self) -> int:
        return len(self.keys)
