"""Tests for the context model and the restorer built on it."""

from __future__ import annotations

import pytest
from duzelt.context import END, START, UNKNOWN, ContextModel
from duzelt.lexicon import Lexicon
from duzelt.restore import ContextRestorer
from duzelt.tokenize import key_of

# "qiz" is genuinely ambiguous: "qız" (girl) and "qiz" both occur, and which one is meant
# shows in the neighbours.
TRAINING = (
    ["Qız məktəbə getdi."] * 60 + ["Qız bağçaya getdi."] * 40 + ["Bu qiz sözü qədimdir."] * 30
)


@pytest.fixture
def lexicon() -> Lexicon:
    return Lexicon.from_sentences(TRAINING)


@pytest.fixture
def model(lexicon: Lexicon) -> ContextModel:
    model = ContextModel()
    for sentence in TRAINING:
        words = sentence.rstrip(".").split()
        keys = [word.lower() for word in words]
        for index, word in enumerate(words):
            key = key_of(word)
            if not lexicon.is_ambiguous(key):
                continue
            left = key_of(words[index - 1]) if index else START
            right = key_of(words[index + 1]) if index + 1 < len(keys) else END
            model.observe(key, word.lower(), left, right)
    return model


class TestContextModel:
    def test_picks_the_form_that_fits_the_neighbours(self, model: ContextModel):
        assert model.best("qiz", START, "mektebe") == "qız"
        assert model.best("qiz", "bu", "sozu") == "qiz"

    def test_unknown_key_has_no_answer(self, model: ContextModel):
        assert model.best("yoxdur", START, END) is None

    def test_unseen_form_scores_as_impossible(self, model: ContextModel):
        assert model.score("qiz", "qız", START, "mektebe") > float("-inf")
        assert model.score("qiz", "qıs", START, "mektebe") == float("-inf")

    def test_survives_a_save_and_load_round_trip(self, model: ContextModel, tmp_path):
        path = tmp_path / "context.jsonl"
        model.save(path)
        reloaded = ContextModel.load(path)
        assert len(reloaded) == len(model)
        assert reloaded.best("qiz", "bu", "sozu") == "qiz"

    def test_keeps_its_feature_vocabulary_across_a_round_trip(self, tmp_path):
        model = ContextModel(vocabulary={"bu"})
        model.observe("qiz", "qız", "bu", "getdi")
        path = tmp_path / "context.jsonl"
        model.save(path)

        reloaded = ContextModel.load(path)
        assert reloaded.vocabulary == {"bu"}
        # "getdi" was never a feature, so it must arrive as UNKNOWN on both sides.
        assert reloaded.feature("getdi") == UNKNOWN
        assert reloaded.feature("bu") == "bu"

    def test_prune_drops_contexts_seen_once(self):
        model = ContextModel()
        for _ in range(3):
            model.observe("qiz", "qız", "bu", "getdi")
        model.observe("qiz", "qız", "nadir", "getdi")
        model.prune(min_context_count=2)
        assert "nadir" not in model.keys["qiz"].left["qız"]
        assert model.keys["qiz"].left["qız"]["bu"] == 3


class TestContextRestorer:
    def test_uses_the_context_where_it_has_learned_one(self, lexicon, model):
        restorer = ContextRestorer(lexicon, model)
        assert restorer.restore("Qiz mektebe getdi.") == "Qız məktəbə getdi."
        assert restorer.restore("Bu qiz sozu qedimdir.") == "Bu qiz sözü qədimdir."

    def test_falls_back_to_the_lexicon_for_keys_it_never_saw(self, lexicon):
        restorer = ContextRestorer(lexicon, ContextModel())
        assert restorer.restore("mektebe") == "məktəbə"
