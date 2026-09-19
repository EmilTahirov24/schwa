"""Spelling suggestions: letters that are missing, extra, wrong or swapped.

This is deliberately a separate layer from diacritic restoration. Restoring diacritics can
only put accents back, so it is safe to apply automatically. Correcting spelling changes
letters, and a spell checker that is wrong turns a correct rare word - a name, a borrowing -
into a common one. So this module only ever *suggests*; the reader decides.

It is a noisy-channel spell checker. For a word that looks wrong, every string one or two
edits away is a candidate, and each is scored by how common it is in the language times how
likely that many typing mistakes are:

    log P(candidate) + edits * log P(edit)

Everything happens on keys - lowercase, diacritics removed - so a suggestion is found in the
space people actually type in, then shown with its accents from the lexicon.

Most of the work is in *not* flagging words. Measured on clean Wikipedia text, a plain
word-list checker flagged 6.6% of correct words, and three things caused nearly all of it:

* Real words beside a far more common one. "ev" (house, 8,895 occurrences) sits one edit from
  "və" (a million). Only words that are rare in absolute terms are held to that comparison.
* Names. Half the unknown words were capitalised mid-sentence; those are left alone.
* Morphology. Azerbaijani builds words by stacking suffixes, so correct forms like
  "cənazəsiylə" are simply too rare to be in any word list. A word made of a known stem and
  a suffix seen on many other stems is accepted as plausible.
"""

from __future__ import annotations

import gzip
import math
import re
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from schwa.lexicon import Lexicon
from schwa.restore import restore_case
from schwa.tokenize import iter_words, key_of

__all__ = ["Speller", "Suggestion", "edits1"]

#: The letters keys are made of: the Azerbaijani alphabet with its diacritics removed,
#: which is the Latin alphabet without "w".
LETTERS = "abcdefghijklmnopqrstuvxyz"

#: Stems shorter than this are too easy to find inside unrelated words to vouch for them.
MIN_STEM = 4

#: Personal endings, written as keys. Wikipedia is third person throughout, so "getmədi" is
#: there and "getmədim" (I did not go) never is - the data-driven endings cannot learn what
#: the corpus does not contain. People writing messages use exactly these forms, so they are
#: added from the grammar rather than from counts: -m / -am (I), -n / -san (you),
#: -q / -iq (we), -niz / -siniz (you, plural), with their vowel-harmony variants.
PERSONAL_ENDINGS = frozenset(
    {
        "m", "am", "em", "yam", "yem",
        "n", "san", "sen",
        "q", "k", "iq", "ik", "uq", "uk", "yiq", "yik", "yuq", "yuk",
        "niz", "nuz", "iniz", "unuz", "siniz", "sunuz",
    }
)  # fmt: skip

_SENTENCE_END = re.compile(r"[.!?…]\s*$")


def edits1(key: str) -> Iterator[str]:
    """Every string one deletion, transposition, substitution or insertion away."""
    splits = [(key[:i], key[i:]) for i in range(len(key) + 1)]
    for left, right in splits:
        if right:
            yield left + right[1:]
        if len(right) > 1:
            yield left + right[1] + right[0] + right[2:]
        for letter in LETTERS:
            if right and letter != right[0]:
                yield left + letter + right[1:]
            yield left + letter + right


@dataclass(frozen=True)
class Suggestion:
    """A word that may be misspelt, and what it might have meant."""

    start: int
    end: int
    typed: str
    options: tuple[str, ...]

    def as_dict(self) -> dict[str, int | str | list[str]]:
        return {
            "start": self.start,
            "end": self.end,
            "typed": self.typed,
            "options": list(self.options),
        }


class Speller:
    """Suggests corrections for words that look misspelt.

    The defaults were chosen on the dev split, trading typos caught against correct words
    flagged. Accepting any ending seen after 30 stems kept false alarms at 1.0% but let too
    many real typos pass as plausible; at 1,000 stems, top-3 recovery of one-edit typos rose
    from 84% to 93% for 0.4 points more false alarms, and 3,000 bought 1.2 points more for
    another 0.2. The edit probability barely moved anything; 0.05 was marginally best.
    """

    def __init__(
        self,
        words: dict[str, tuple[str, int]],
        suffixes: Iterable[str] = (),
        min_count: int = 5,
        rare_ceiling: int = 20,
        dominance: float = 100.0,
        edit_probability: float = 0.05,
        max_distance: int = 2,
    ) -> None:
        """
        :param words: key -> (spelling with diacritics, count)
        :param suffixes: endings seen on many known stems; see :meth:`find_suffixes`
        :param min_count: a key seen fewer times than this is treated as unknown
        :param rare_ceiling: only a known word seen fewer times than this can still be
            suspected of being a typo
        :param dominance: ... and only when a word one edit away is this many times as common
        :param edit_probability: the chance of one typing mistake, which sets how far a
            candidate's frequency has to outweigh each extra edit
        """
        self.words = words
        self.suffixes = frozenset(suffixes)
        self.min_count = min_count
        self.rare_ceiling = rare_ceiling
        self.dominance = dominance
        self.edit_cost = math.log(edit_probability)
        self.max_distance = max_distance
        self.total = sum(count for _, count in words.values()) or 1

    @classmethod
    def from_lexicon(cls, lexicon: Lexicon, **settings: float) -> Speller:
        words = {}
        for key in lexicon:
            form = lexicon.best(key)
            if form is not None:
                words[key] = (form, lexicon.total(key))
        min_count = int(settings.get("min_count", 5))
        suffixes = cls.find_suffixes(words, min_count)
        return cls(words, suffixes, **settings)  # type: ignore[arg-type]

    @staticmethod
    def find_suffixes(
        words: dict[str, tuple[str, int]], min_count: int = 5, min_stems: int = 1000
    ) -> set[str]:
        """Endings that follow many different known stems, plus the personal endings.

        For every known word that is a known stem plus something, count the something. An
        ending that turns up after hundreds of different stems - "lar", "ların", "sini",
        "ylə" - is grammar rather than coincidence. :data:`PERSONAL_ENDINGS` are added on
        top, being grammar the corpus is too third-person to show; both the product and the
        evaluation take their endings from here, so they cannot drift apart.
        """
        known = {key for key, (_, count) in words.items() if count >= min_count}
        endings: Counter[str] = Counter()
        for key in known:
            for cut in range(MIN_STEM, len(key)):
                if key[:cut] in known:
                    endings[key[cut:]] += 1
        found = {ending for ending, stems in endings.items() if stems >= min_stems}
        return found | PERSONAL_ENDINGS

    # -- storage ---------------------------------------------------------------------------

    def save(self, path: Path, min_count: int | None = None) -> int:
        """Write the suffixes, then `key<TAB>form<TAB>count` lines, gzipped."""
        floor = self.min_count if min_count is None else min_count
        rows = sorted(
            f"{key}\t{form}\t{count}" for key, (form, count) in self.words.items() if count >= floor
        )
        header = "@suffixes\t" + ",".join(sorted(self.suffixes))
        path.parent.mkdir(parents=True, exist_ok=True)
        # mtime=0: the same vocabulary always gives the same bytes.
        text = "\n".join([header, *rows]).encode("utf-8")
        path.write_bytes(gzip.compress(text, 9, mtime=0))
        return len(rows)

    @classmethod
    def load(cls, path: Path, **settings: float) -> Speller:
        words: dict[str, tuple[str, int]] = {}
        suffixes: list[str] = []
        with gzip.open(path, "rt", encoding="utf-8") as source:
            for line in source:
                if line.startswith("@suffixes\t"):
                    suffixes = [s for s in line.rstrip("\n").split("\t", 1)[1].split(",") if s]
                    continue
                key, form, count = line.rstrip("\n").split("\t")
                words[key] = (form, int(count))
        return cls(words, suffixes, **settings)  # type: ignore[arg-type]

    # -- the model -------------------------------------------------------------------------

    def count(self, key: str) -> int:
        entry = self.words.get(key)
        return entry[1] if entry else 0

    def known(self, key: str) -> bool:
        return self.count(key) >= self.min_count

    def plausible(self, key: str) -> bool:
        """True if `key` reads as a known stem with a common ending."""
        return any(
            key[cut:] in self.suffixes and self.known(key[:cut])
            for cut in range(MIN_STEM, len(key))
        )

    def _score(self, frequency: float, distance: int) -> float:
        return math.log(frequency / self.total) + distance * self.edit_cost

    def is_suspicious(self, key: str) -> bool:
        """True if `key` is more likely a mistake than a word."""
        if len(key) < 3:
            return False
        if self.known(key):
            count = self.count(key)
            if count >= self.rare_ceiling:
                return False
            return any(self.count(near) >= count * self.dominance for near in edits1(key))
        return not self.plausible(key)

    def candidates(self, key: str) -> list[tuple[float, tuple[str, ...]]]:
        """Scored corrections for `key`, best first; each is one word or a split into two."""
        scored: dict[tuple[str, ...], float] = {}

        frontier = {key}
        found_at = 0
        for distance in range(1, self.max_distance + 1):
            frontier = {edit for word in frontier for edit in edits1(word)}
            for candidate in frontier:
                if candidate != key and self.known(candidate):
                    score = self._score(self.count(candidate), distance)
                    scored[(candidate,)] = max(scored.get((candidate,), -math.inf), score)
            # A second edit is only worth looking at when one found nothing.
            if scored:
                found_at = distance
                break

        # Two words run together are considered as typed, and one edit away only when no
        # single word was one edit away: otherwise "mektbe" drew "mək the", an Azerbaijani
        # fragment glued to an English article Wikipedia happens to contain.
        joined_forms: list[tuple[int, str]] = [(0, key)]
        if found_at != 1:
            joined_forms += [(1, edit) for edit in set(edits1(key))]

        for distance, joined in joined_forms:
            for split in self._splits(joined):
                first, second = split
                frequency = self.count(first) * self.count(second) / self.total
                score = self._score(frequency, distance)
                scored[split] = max(scored.get(split, -math.inf), score)

        return sorted(((score, words) for words, score in scored.items()), reverse=True)

    def _splits(self, key: str) -> Iterable[tuple[str, str]]:
        """Two known words written together: "nebilim" -> ("ne", "bilim")."""
        for i in range(2, len(key) - 1):
            first, second = key[:i], key[i:]
            if self.known(first) and self.known(second):
                yield first, second

    def suggest(self, word: str, limit: int = 3, sentence_start: bool = True) -> tuple[str, ...]:
        """Corrections for `word`, spelled with their diacritics and its capitalisation.

        A capitalised word that does not open a sentence is taken to be a name and left alone.
        """
        if word[:1].isupper() and not sentence_start:
            return ()

        key = key_of(word)
        if not self.is_suspicious(key):
            return ()

        options = []
        for _, words in self.candidates(key)[:limit]:
            forms = [self.words[part][0] for part in words]
            forms[0] = restore_case(word, forms[0])
            options.append(" ".join(forms))
        return tuple(options)

    def check(self, text: str, limit: int = 3) -> list[Suggestion]:
        """Every word in `text` that looks misspelt, with its suggestions."""
        found = []
        for start, end in iter_words(text):
            before = text[:start]
            sentence_start = not before.strip() or bool(_SENTENCE_END.search(before))
            options = self.suggest(text[start:end], limit, sentence_start)
            if options:
                found.append(Suggestion(start, end, text[start:end], options))
        return found
