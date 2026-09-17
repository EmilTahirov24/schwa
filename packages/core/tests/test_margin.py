"""Tests for the margin that guards the context model's answer."""

from __future__ import annotations

import pytest
from duzelt.context import START, ContextModel
from duzelt.lexicon import Lexicon
from duzelt.restore import ContextRestorer

TRAINING = ["Qız gəldi."] * 90 + ["Qiz sözü qədimdir."] * 10


@pytest.fixture
def lexicon() -> Lexicon:
    return Lexicon.from_sentences(TRAINING)


@pytest.fixture
def model() -> ContextModel:
    # A small vocabulary keeps the smoothing mass in proportion to these counts.
    model = ContextModel(vocabulary={"geldi", "sozu"})
    for _ in range(90):
        model.observe("qiz", "qız", START, "geldi")
    for _ in range(10):
        model.observe("qiz", "qiz", START, "sozu")
    return model


def test_without_a_margin_the_context_decides(lexicon: Lexicon, model: ContextModel):
    restorer = ContextRestorer(lexicon, model)
    assert restorer.restore("Qiz sozu qedimdir.") == "Qiz sözü qədimdir."


def test_a_high_margin_keeps_the_most_frequent_spelling(lexicon: Lexicon, model: ContextModel):
    restorer = ContextRestorer(lexicon, model, margin=100.0)
    assert restorer.restore("Qiz sozu qedimdir.") == "Qız sözü qədimdir."


def test_the_margin_only_guards_disagreements(lexicon: Lexicon, model: ContextModel):
    # Where the context agrees with the lexicon, the margin cannot change anything.
    careful = ContextRestorer(lexicon, model, margin=100.0)
    assert careful.restore("Qiz geldi.") == "Qız gəldi."


def test_the_margin_shows_up_in_the_system_name(lexicon: Lexicon, model: ContextModel):
    assert ContextRestorer(lexicon, model).name == "context"
    assert ContextRestorer(lexicon, model, margin=2).name == "context (margin 2)"
