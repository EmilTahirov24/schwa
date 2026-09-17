"""Tests for the tagger's text side: vocabulary, label application, batching."""

from __future__ import annotations

from collections.abc import Sequence

import pytest
from duzelt.alphabet import LABEL_KEEP, LABEL_MARK, strip_diacritics
from duzelt.tagger import (
    PAD,
    UNKNOWN,
    CharVocabulary,
    TaggerRestorer,
    foldable_positions,
    restore_with_labels,
)


def mark_every_e(texts: Sequence[str]) -> list[list[int]]:
    """A stand-in predictor: claims every "e" is really "ə"."""
    return [[LABEL_MARK if char == "e" else LABEL_KEEP for char in text] for text in texts]


class TestVocabulary:
    def test_reserves_padding_and_unknown(self):
        vocabulary = CharVocabulary(["a", "b"])
        assert vocabulary.characters[:2] == [PAD, UNKNOWN]
        assert len(vocabulary) == 4

    def test_unseen_characters_share_one_id(self):
        vocabulary = CharVocabulary(["a"])
        assert vocabulary.encode("xy") == [1, 1]
        assert vocabulary.encode("a") == [2]

    def test_is_built_from_stripped_text(self):
        # The model only ever sees text without diacritics, so the vocabulary must not
        # waste ids on letters it will never be given.
        vocabulary = CharVocabulary.from_texts(["səncə nədən"] * 20, min_count=20)
        assert "ə" not in vocabulary.characters
        assert "e" in vocabulary.characters

    def test_rare_characters_are_dropped(self):
        vocabulary = CharVocabulary.from_texts(["aaaa b"], min_count=2)
        assert "a" in vocabulary.characters
        assert "b" not in vocabulary.characters

    def test_survives_a_save_and_load_round_trip(self, tmp_path):
        vocabulary = CharVocabulary(["a", "e", "ş"])
        path = tmp_path / "vocabulary.json"
        vocabulary.save(path)
        assert CharVocabulary.load(path).characters == vocabulary.characters


class TestRestoreWithLabels:
    def test_applies_the_predicted_labels(self):
        assert restore_with_labels("sence", [0, 1, 0, 0, 1]) == "səncə"

    def test_keeps_the_diacritics_the_user_typed(self):
        # The user already wrote "mən"; the model must not be able to undo that, whatever
        # it predicts for those characters.
        text = "mən sence"
        predicted = [LABEL_KEEP] * len(strip_diacritics(text))
        assert restore_with_labels(text, predicted) == "mən sence"

    def test_foldable_positions_are_the_only_decisions(self):
        assert foldable_positions("qiz!") == [1]  # only "i" can hide another letter
        assert foldable_positions("xxx") == []


class TestTaggerRestorer:
    def test_restores_a_batch(self):
        restorer = TaggerRestorer(mark_every_e)
        assert restorer.restore_many(["sence", "neden"]) == ["səncə", "nədən"]

    def test_restores_a_single_text(self):
        assert TaggerRestorer(mark_every_e).restore("sence") == "səncə"

    def test_empty_batch_is_allowed(self):
        assert TaggerRestorer(mark_every_e).restore_many([]) == []

    @pytest.mark.parametrize("text", ["sence neden", "MƏN gəldim", "123 ?!", ""])
    def test_only_ever_changes_diacritics(self, text: str):
        restored = TaggerRestorer(mark_every_e).restore(text)
        assert strip_diacritics(restored) == strip_diacritics(text)
        assert len(restored) == len(text)
