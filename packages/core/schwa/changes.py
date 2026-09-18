"""Describe what a restorer changed, word by word.

The web page highlights each change and lets the reader reject it, and the extension needs
the same list to replace text in place. Both want spans, not a new string.
"""

from __future__ import annotations

from dataclasses import dataclass

from schwa.tokenize import iter_words

__all__ = ["Change", "changes_between"]


@dataclass(frozen=True)
class Change:
    """One word the restorer rewrote."""

    start: int
    end: int
    typed: str
    restored: str

    def as_dict(self) -> dict[str, int | str]:
        return {
            "start": self.start,
            "end": self.end,
            "from": self.typed,
            "to": self.restored,
        }


def changes_between(typed: str, restored: str) -> list[Change]:
    """Return the words that differ between the two texts.

    Both texts must have the same length: a restorer may only swap letters for their
    accented forms, never insert or delete anything.
    """
    if len(typed) != len(restored):
        raise ValueError("restored text must have the same length as the input")

    return [
        Change(start, end, typed[start:end], restored[start:end])
        for start, end in iter_words(typed)
        if typed[start:end] != restored[start:end]
    ]
