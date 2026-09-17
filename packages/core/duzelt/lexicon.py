"""The word lexicon: which real words hide behind each typed form, and how often.

Built from the training split only. It serves three purposes: it is the simplest restorer
on its own, it supplies the candidate list for every model that follows, and it decides
which words count as ambiguous when scoring.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from pathlib import Path

from duzelt.alphabet import az_lower
from duzelt.tokenize import key_of, words_of

__all__ = ["Lexicon"]


#: A rival spelling counts as real, rather than as a typo in the source text, once it
#: reaches this share of the key's occurrences and this many occurrences. Wikipedia
#: contains "bır" for "bir" a few dozen times in 286k occurrences; that is a typo, and
#: treating it as an ambiguity would put thousands of unwinnable words into the score.
MIN_MINORITY_SHARE = 0.05
MIN_MINORITY_COUNT = 10


class Lexicon:
    """Maps a typed form to the real words it can stand for, with their counts."""

    def __init__(
        self,
        forms: dict[str, Counter[str]] | None = None,
        min_minority_share: float = MIN_MINORITY_SHARE,
        min_minority_count: int = MIN_MINORITY_COUNT,
    ) -> None:
        self._forms: dict[str, Counter[str]] = defaultdict(Counter)
        self.min_minority_share = min_minority_share
        self.min_minority_count = min_minority_count
        if forms:
            for key, counts in forms.items():
                self._forms[key] = Counter(counts)

    @classmethod
    def from_sentences(cls, sentences: Iterable[str], **thresholds: float) -> Lexicon:
        """Count every word of every sentence into a new lexicon."""
        lexicon = cls(**thresholds)  # type: ignore[arg-type]
        for sentence in sentences:
            for word in words_of(sentence):
                lexicon.add(word)
        return lexicon

    def add(self, word: str) -> None:
        """Record one occurrence of ``word``."""
        self._forms[key_of(word)][az_lower(word)] += 1

    def candidates(self, key: str) -> list[tuple[str, int]]:
        """Return the possible words for ``key``, most frequent first."""
        return self._forms[key].most_common() if key in self._forms else []

    def best(self, key: str) -> str | None:
        """Return the most frequent word for ``key``, or None if it was never seen."""
        candidates = self.candidates(key)
        return candidates[0][0] if candidates else None

    def has_multiple_forms(self, key: str) -> bool:
        """True if ``key`` was ever seen spelled in more than one way, typos included."""
        return len(self._forms.get(key, ())) > 1

    def is_ambiguous(self, key: str) -> bool:
        """True if at least two spellings of ``key`` are common enough to be real.

        See :data:`MIN_MINORITY_SHARE`: a spelling that appears a handful of times against
        hundreds of thousands is a typo in the source text, not a second reading.
        """
        counts = self._forms.get(key)
        if counts is None or len(counts) < 2:
            return False

        total = sum(counts.values())
        runner_up = counts.most_common(2)[1][1]
        return runner_up >= self.min_minority_count and runner_up / total >= self.min_minority_share

    def count(self, key: str, form: str) -> int:
        """How often ``form`` was seen for ``key``."""
        return self._forms.get(key, Counter())[form]

    def total(self, key: str) -> int:
        """How often ``key`` was seen in any form."""
        return sum(self._forms.get(key, Counter()).values())

    def prune(self, min_count: int) -> None:
        """Drop rare spellings, which are mostly typos in the source text."""
        for key in list(self._forms):
            kept = Counter({f: c for f, c in self._forms[key].items() if c >= min_count})
            if kept:
                self._forms[key] = kept
            else:
                del self._forms[key]

    def save(self, path: Path) -> None:
        """Write the lexicon as one JSON object per key."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as out:
            for key in sorted(self._forms):
                row = {"key": key, "forms": dict(self._forms[key].most_common())}
                out.write(json.dumps(row, ensure_ascii=False) + "\n")

    @classmethod
    def load(cls, path: Path) -> Lexicon:
        """Read a lexicon written by :meth:`save`."""
        forms: dict[str, Counter[str]] = {}
        with path.open(encoding="utf-8") as source:
            for line in source:
                row = json.loads(line)
                forms[row["key"]] = Counter(row["forms"])
        return cls(forms)

    def __len__(self) -> int:
        return len(self._forms)

    def __contains__(self, key: object) -> bool:
        return key in self._forms

    def __iter__(self) -> Iterator[str]:
        return iter(self._forms)

    @property
    def ambiguous_keys(self) -> list[str]:
        """Every key with at least two spellings common enough to be real."""
        return [key for key in self._forms if self.is_ambiguous(key)]

    @property
    def keys_with_multiple_forms(self) -> list[str]:
        """Every key ever seen spelled in more than one way, typos included."""
        return [key for key, counts in self._forms.items() if len(counts) > 1]
