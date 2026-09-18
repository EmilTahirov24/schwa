"""The model that ships with the package.

The point of this module is that ``pip install schwa-az`` is enough:

    >>> from schwa import restore
    >>> restore("sence neden basliyaq")
    'səncə nədən başlıyaq'

Two files travel with the package — the quantised tagger and the part of the lexicon that
can be applied without context. Loading them is deferred until the first call and cached
afterwards, so importing ``schwa`` stays instant.
"""

from __future__ import annotations

import gzip
from collections import Counter
from functools import lru_cache
from pathlib import Path

from schwa.lexicon import Lexicon
from schwa.restore import HybridRestorer, LexiconRestorer, Restorer
from schwa.spelling import Speller, Suggestion

DATA = Path(__file__).parent / "data"
MODEL = DATA / "tagger.onnx"
LEXICON = DATA / "lexicon.tsv.gz"
VOCABULARY = DATA / "vocabulary.tsv.gz"

__all__ = [
    "bundled_lexicon",
    "check",
    "default_restorer",
    "default_speller",
    "is_bundled",
    "restore",
]


class MissingBundle(RuntimeError):
    """Raised when the package was built without its model."""


def is_bundled() -> bool:
    """True if this installation carries the model."""
    return LEXICON.exists()


def bundled_lexicon() -> Lexicon:
    """The shipped lexicon: one spelling per key, all of them safe to apply."""
    if not LEXICON.exists():
        raise MissingBundle(f"no lexicon in this installation: {LEXICON}")

    forms: dict[str, Counter[str]] = {}
    with gzip.open(LEXICON, "rt", encoding="utf-8") as source:
        for line in source:
            key, form, count = line.rstrip("\n").split("\t")
            forms[key] = Counter({form: int(count)})

    return Lexicon(forms)


@lru_cache(maxsize=1)
def default_restorer() -> Restorer:
    """The best restorer this installation can build.

    With onnxruntime present that is the tagger corrected by the lexicon — the combination
    that scores highest. Without it, the lexicon alone still restores most text, so the
    package stays useful rather than refusing to work.
    """
    lexicon = bundled_lexicon()

    if not MODEL.exists():
        return LexiconRestorer(lexicon)

    try:
        from schwa.onnx_tagger import load_onnx_restorer
    except ImportError:
        return LexiconRestorer(lexicon)

    try:
        tagger = load_onnx_restorer(MODEL)
    except Exception:  # noqa: BLE001 - any runtime problem means falling back, not failing
        return LexiconRestorer(lexicon)

    return HybridRestorer(tagger, lexicon)


def restore(text: str) -> str:
    """Restore Azerbaijani diacritics in ``text``."""
    return default_restorer().restore(text)


@lru_cache(maxsize=1)
def default_speller() -> Speller:
    """The spell checker built from the shipped vocabulary."""
    if not VOCABULARY.exists():
        raise MissingBundle(f"no vocabulary in this installation: {VOCABULARY}")
    return Speller.load(VOCABULARY)


def check(text: str) -> list[Suggestion]:
    """Words in ``text`` that look misspelt, each with up to three suggestions.

    Unlike :func:`restore`, this never changes the text: spelling corrections change letters,
    and a wrong one is worse than none, so the caller decides which to apply.
    """
    return default_speller().check(text)
