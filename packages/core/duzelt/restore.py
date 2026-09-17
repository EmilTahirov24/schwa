"""Restorers: turn typed text back into properly spelled Azerbaijani.

Every restorer obeys the same contract, checked by tests: the output may differ from the
input in diacritics only. Anything else — length, case, punctuation, spacing — stays.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from duzelt.alphabet import az_upper, strip_diacritics
from duzelt.lexicon import Lexicon
from duzelt.tokenize import iter_words, key_of

__all__ = ["IdentityRestorer", "LexiconRestorer", "Restorer", "restore_case"]


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


class LexiconRestorer:
    """Replaces each word with the spelling seen most often in training.

    It has no notion of context, so for an ambiguous word it always answers the same way.
    That is exactly the limit the later models have to improve on.
    """

    name = "lexicon"

    def __init__(self, lexicon: Lexicon) -> None:
        self.lexicon = lexicon

    def restore(self, text: str) -> str:
        pieces: list[str] = []
        cursor = 0

        for start, end in iter_words(text):
            pieces.append(text[cursor:start])
            pieces.append(self._restore_word(text[start:end]))
            cursor = end

        pieces.append(text[cursor:])
        return "".join(pieces)

    def _restore_word(self, word: str) -> str:
        form = self.lexicon.best(key_of(word))
        if form is None:
            return word

        candidate = restore_case(word, form)
        # Guard the contract: a lexicon entry may only put diacritics back, never
        # change the letters themselves.
        if strip_diacritics(candidate) != strip_diacritics(word):
            return word
        return candidate
