"""Tests for the hybrid restorer: the tagger, overruled where the lexicon is unanimous."""

from __future__ import annotations

from collections.abc import Sequence

import pytest
from schwa.alphabet import strip_diacritics
from schwa.lexicon import Lexicon
from schwa.restore import HybridRestorer, IdentityRestorer

# "sulaveri" is unanimous in training; "qiz" has two real readings; "tsxenitskali" is unknown.
TRAINING = (
    ["Şulaveri kəndi qədimdir."] * 9 + ["Qız məktəbə getdi."] * 60 + ["Bu qiz sözü qədimdir."] * 20
)


class FakeTagger:
    """Stands in for the neural tagger with a fixed, deliberately imperfect answer."""

    name = "fake tagger"

    def __init__(self, answers: dict[str, str]) -> None:
        self.answers = answers
        self.batches: list[int] = []

    def restore(self, text: str) -> str:
        return self.answers.get(text, text)

    def restore_many(self, texts: Sequence[str]) -> list[str]:
        self.batches.append(len(texts))
        return [self.restore(text) for text in texts]


@pytest.fixture
def lexicon() -> Lexicon:
    return Lexicon.from_sentences(TRAINING)


def test_the_lexicon_fixes_a_name_the_tagger_garbled(lexicon: Lexicon):
    # The exact failure this class exists for: the tagger leaves "Sulaveri" alone while the
    # training text says "Şulaveri" nine times out of nine.
    tagger = FakeTagger({"Sulaveri kendi qedimdir.": "Sulaveri kəndi qədimdir."})
    hybrid = HybridRestorer(tagger, lexicon)
    assert hybrid.restore("Sulaveri kendi qedimdir.") == "Şulaveri kəndi qədimdir."


def test_the_tagger_keeps_the_ambiguous_words(lexicon: Lexicon):
    # "qiz" has two readings, so the lexicon must not touch it - that is the tagger's call.
    tagger = FakeTagger({"Bu qiz sozu qedimdir.": "Bu qiz sözü qədimdir."})
    hybrid = HybridRestorer(tagger, lexicon)
    assert hybrid.restore("Bu qiz sozu qedimdir.") == "Bu qiz sözü qədimdir."


def test_unknown_words_are_left_to_the_tagger(lexicon: Lexicon):
    tagger = FakeTagger({"Tsxenitskali cayi": "Tsxenitskalı çayı"})
    hybrid = HybridRestorer(tagger, lexicon)
    assert hybrid.restore("Tsxenitskali cayi") == "Tsxenitskalı çayı"


def test_a_rarely_seen_spelling_does_not_overrule_the_tagger(lexicon: Lexicon):
    tagger = FakeTagger({"Sulaveri": "Sulaveri"})
    careful = HybridRestorer(tagger, lexicon, min_count=50)
    assert careful.restore("Sulaveri") == "Sulaveri"


def test_it_passes_whole_batches_to_the_tagger(lexicon: Lexicon):
    tagger = FakeTagger({})
    HybridRestorer(tagger, lexicon).restore_many(["biri", "ikisi", "ucu"])
    assert tagger.batches == [3]


def test_the_context_model_can_take_the_ambiguous_words(lexicon: Lexicon):
    from schwa.context import END, START, ContextModel

    model = ContextModel()
    for _ in range(20):
        model.observe("qiz", "qiz", "bu", "sozu")
    tagger = FakeTagger({"Bu qiz sozu": "Bu qız sozu"})

    hybrid = HybridRestorer(tagger, lexicon, model)
    assert hybrid.restore("Bu qiz sozu").startswith("Bu qiz")
    assert model.best("qiz", START, END) is not None


@pytest.mark.parametrize("text", ["Sulaveri kendi", "QIZ MEKTEBE", "123 !?", ""])
def test_only_diacritics_ever_change(lexicon: Lexicon, text: str):
    hybrid = HybridRestorer(IdentityRestorer(), lexicon)
    restored = hybrid.restore(text)
    assert strip_diacritics(restored) == strip_diacritics(text)
    assert len(restored) == len(text)
