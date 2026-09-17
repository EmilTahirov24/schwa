"""Restorers: turn typed text back into properly spelled Azerbaijani.

Every restorer obeys the same contract, checked by tests: the output may differ from the
input in diacritics only. Anything else — length, case, punctuation, spacing — stays.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from duzelt.alphabet import az_upper, strip_diacritics
from duzelt.context import END, START, ContextModel
from duzelt.lexicon import Lexicon
from duzelt.tokenize import iter_words, key_of

__all__ = [
    "ContextRestorer",
    "IdentityRestorer",
    "LexiconRestorer",
    "Restorer",
    "WordRestorer",
    "restore_case",
]


@runtime_checkable
class Restorer(Protocol):
    """Anything that can put the diacritics back."""

    name: str

    def restore(self, text: str) -> str: ...


def restore_case(typed: str, form: str) -> str:
    """Give ``form`` the capitalisation of ``typed``."""
    if typed.isupper() and len(typed) > 1:
        return az_upper(form)
    if typed[:1].isupper():
        return az_upper(form[:1]) + form[1:]
    return form


class IdentityRestorer:
    """Changes nothing. The floor every other system has to beat."""

    name = "identity"

    def restore(self, text: str) -> str:
        return text


class WordRestorer:
    """Walks the words of a text and lets a subclass choose each spelling.

    The walk keeps everything between the words untouched, restores the capitalisation of
    the typed word, and drops any suggestion that would change more than diacritics.
    """

    name = "word"

    def restore(self, text: str) -> str:
        spans = iter_words(text)
        keys = [key_of(text[start:end]) for start, end in spans]
        pieces: list[str] = []
        cursor = 0

        for index, (start, end) in enumerate(spans):
            word = text[start:end]
            left = keys[index - 1] if index else START
            right = keys[index + 1] if index + 1 < len(keys) else END
            form = self.form_for(keys[index], left, right)

            pieces.append(text[cursor:start])
            pieces.append(self._apply(word, form))
            cursor = end

        pieces.append(text[cursor:])
        return "".join(pieces)

    def form_for(self, key: str, left: str, right: str) -> str | None:
        """Return the lowercase spelling chosen for ``key``, or None to keep the word."""
        raise NotImplementedError

    @staticmethod
    def _apply(word: str, form: str | None) -> str:
        if form is None:
            return word
        candidate = restore_case(word, form)
        # Guard the contract: a suggestion may only put diacritics back.
        if strip_diacritics(candidate) != strip_diacritics(word):
            return word
        return candidate


class LexiconRestorer(WordRestorer):
    """Replaces each word with the spelling seen most often in training.

    It has no notion of context, so for an ambiguous word it always answers the same way.
    That is exactly the limit the context model has to improve on.
    """

    name = "lexicon"

    def __init__(self, lexicon: Lexicon) -> None:
        self.lexicon = lexicon

    def form_for(self, key: str, left: str, right: str) -> str | None:
        return self.lexicon.best(key)


class ContextRestorer(WordRestorer):
    """Chooses among the candidate spellings using the neighbouring words.

    The most frequent spelling is already right about four times out of five, so the
    context only overrules it when it scores at least ``margin`` higher. With a margin of
    zero the model decides on its own; raising it makes the model speak up only where the
    evidence is clear. Keys the model never saw fall back to the lexicon.
    """

    name = "context"

    def __init__(self, lexicon: Lexicon, model: ContextModel, margin: float = 0.0) -> None:
        self.lexicon = lexicon
        self.model = model
        self.margin = margin
        if margin:
            self.name = f"context (margin {margin:g})"

    def form_for(self, key: str, left: str, right: str) -> str | None:
        fallback = self.lexicon.best(key)
        chosen = self.model.best(key, left, right)

        if chosen is None or chosen == fallback:
            return fallback
        if fallback is None:
            return chosen

        gap = self.model.score(key, chosen, left, right) - self.model.score(
            key, fallback, left, right
        )
        return chosen if gap >= self.margin else fallback
