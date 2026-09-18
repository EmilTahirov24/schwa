"""Azerbaijani letters: case mapping, diacritic folding, and character labels.

Two things in this module are easy to get wrong and are the reason it exists.

1. Python's built-in case functions are wrong for Azerbaijani. The language has two
   pairs of "i" letters: dotted ``i``/``İ`` and dotless ``ı``/``I``. Python maps
   ``"I".lower()`` to ``"i"`` (should be ``"ı"``) and ``"i".upper()`` to ``"I"``
   (should be ``"İ"``), and ``"İ".lower()`` even returns two code points
   (``i`` + COMBINING DOT ABOVE). :func:`az_lower` and :func:`az_upper` fix this.

2. When people type Azerbaijani without the proper keyboard layout, they replace each
   special letter with its closest ASCII letter: ``səncə`` becomes ``sence``. Exactly
   seven letter pairs collapse this way, and every collapsed form has exactly two
   possible originals. That is what makes restoration a per-character binary decision
   (see :data:`LABEL_KEEP` and :data:`LABEL_MARK`).
"""

from __future__ import annotations

__all__ = [
    "FOLD_PAIRS",
    "LABEL_KEEP",
    "LABEL_MARK",
    "STRIP_MAP",
    "apply_labels",
    "az_lower",
    "az_upper",
    "is_foldable",
    "mark",
    "strip_diacritics",
    "to_labels",
]

# ASCII form a typist produces -> the Azerbaijani letter it may stand for.
# Note the asymmetry in the i-family: lowercase "i" may hide dotless "ı", while
# uppercase "I" may hide dotted "İ".
FOLD_PAIRS: dict[str, str] = {
    "c": "ç",
    "e": "ə",
    "g": "ğ",
    "i": "ı",
    "o": "ö",
    "s": "ş",
    "u": "ü",
    "C": "Ç",
    "E": "Ə",
    "G": "Ğ",
    "I": "İ",
    "O": "Ö",
    "S": "Ş",
    "U": "Ü",
}

# Azerbaijani letter -> ASCII form, i.e. what typing without the layout produces.
STRIP_MAP: dict[str, str] = {
    "ç": "c",
    "ə": "e",
    "ğ": "g",
    "ı": "i",
    "ö": "o",
    "ş": "s",
    "ü": "u",
    "Ç": "C",
    "Ə": "E",
    "Ğ": "G",
    "İ": "I",
    "Ö": "O",
    "Ş": "S",
    "Ü": "U",
}

LABEL_KEEP = 0
"""The character stays as typed (e.g. ``e`` really is ``e``)."""

LABEL_MARK = 1
"""The character takes its Azerbaijani form (e.g. ``e`` is really ``ə``)."""

_STRIP_TABLE = str.maketrans(STRIP_MAP)
_MARK_TABLE = str.maketrans(FOLD_PAIRS)
_LOWER_SPECIAL = str.maketrans({"I": "ı", "İ": "i"})
_UPPER_SPECIAL = str.maketrans({"i": "İ", "ı": "I"})


def az_lower(text: str) -> str:
    """Lowercase ``text`` using Azerbaijani rules (``I`` -> ``ı``, ``İ`` -> ``i``)."""
    return text.translate(_LOWER_SPECIAL).lower()


def az_upper(text: str) -> str:
    """Uppercase ``text`` using Azerbaijani rules (``i`` -> ``İ``, ``ı`` -> ``I``)."""
    return text.translate(_UPPER_SPECIAL).upper()


def strip_diacritics(text: str) -> str:
    """Return ``text`` as someone would type it without an Azerbaijani keyboard.

    Only the fourteen letters in :data:`STRIP_MAP` change; length is preserved.
    """
    return text.translate(_STRIP_TABLE)


def is_foldable(char: str) -> bool:
    """True if ``char`` is an ASCII letter that may hide an Azerbaijani letter."""
    return char in FOLD_PAIRS


def mark(char: str) -> str:
    """Return the Azerbaijani form of ``char``, or ``char`` itself if it has none."""
    return FOLD_PAIRS.get(char, char)


def to_labels(text: str) -> tuple[str, list[int]]:
    """Split correct ``text`` into its typed form and one label per character.

    This is the training pair: the model sees the stripped text and predicts, for every
    character, whether it should be marked.
    """
    stripped = strip_diacritics(text)
    labels = [
        LABEL_MARK if is_foldable(typed) and original != typed else LABEL_KEEP
        for typed, original in zip(stripped, text, strict=True)
    ]
    return stripped, labels


def apply_labels(stripped: str, labels: list[int]) -> str:
    """Rebuild text from its typed form and per-character labels."""
    if len(stripped) != len(labels):
        raise ValueError(f"expected {len(stripped)} labels, got {len(labels)}")
    return "".join(
        char.translate(_MARK_TABLE) if label == LABEL_MARK else char
        for char, label in zip(stripped, labels, strict=True)
    )
