"""Word boundaries and the lookup key shared by every part of the project.

A "key" is the form a word takes once case and diacritics are gone: both ``Səncə`` and
``sence`` have the key ``sence``. Keys are what the lexicon is indexed by and what makes a
word ambiguous or not.
"""

from __future__ import annotations

import re

from duzelt.alphabet import az_lower, strip_diacritics

__all__ = ["iter_words", "key_of", "words_of"]

# Letters of the Azerbaijani and Latin alphabets, plus apostrophes inside a word.
_WORD = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*", re.UNICODE)


def iter_words(text: str) -> list[tuple[int, int]]:
    """Return the (start, end) span of every word in ``text``."""
    return [match.span() for match in _WORD.finditer(text)]


def words_of(text: str) -> list[str]:
    """Return the words of ``text``."""
    return _WORD.findall(text)


def key_of(word: str) -> str:
    """Return the case- and diacritic-free form used to look a word up."""
    return strip_diacritics(az_lower(word))
