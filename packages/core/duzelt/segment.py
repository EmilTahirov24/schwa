"""Split Azerbaijani text into sentences.

Used twice: when building the training corpus, and at inference time to cut long input
into pieces the model can take. It is deliberately simple — a regular expression plus a
short list of abbreviations that must not end a sentence.
"""

from __future__ import annotations

import re

__all__ = ["split_sentences"]

# A sentence ends at .!?… followed by space, but not inside an abbreviation.
_BOUNDARY = re.compile(r"(?<=[.!?…])[ \t]+|\n+")

# Abbreviations whose trailing dot is not a sentence end.
_ABBREVIATIONS = frozenset(
    {
        "akad",
        "b",
        "c",
        "d",
        "dos",
        "e",
        "əsr",
        "hək",
        "ing",
        "məs",
        "mln",
        "mlrd",
        "prof",
        "red",
        "s",
        "sm",
        "təq",
        "y",
        "yun",
    }
)

_LAST_WORD = re.compile(r"([^\s.]+)\.\s*$")


def _ends_with_abbreviation(piece: str) -> bool:
    match = _LAST_WORD.search(piece)
    if match is None:
        return False
    word = match.group(1)
    # "b.e.ə." and friends: a chain of single letters separated by dots.
    if all(len(part) <= 1 for part in word.split(".")):
        return True
    return word.rsplit(".", 1)[-1].lower() in _ABBREVIATIONS


def split_sentences(text: str) -> list[str]:
    """Return the sentences of ``text``, with surrounding whitespace removed."""
    sentences: list[str] = []
    current = ""

    for piece in _BOUNDARY.split(text):
        if not piece.strip():
            continue
        current = f"{current} {piece}".strip() if current else piece.strip()
        if not _ends_with_abbreviation(current):
            sentences.append(current)
            current = ""

    if current:
        sentences.append(current)

    return sentences
