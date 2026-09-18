"""Tests for the torch side of the tagger.

Skipped where torch is not installed, which is the case in CI: the training dependencies
live in their own group so the test job stays fast.
"""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")

from schwa._tagger_model import (  # noqa: E402
    CharTagger,
    _window_bounds,
    encode_batch,
    load_predictor,
    predict_labels,
    save_checkpoint,
)
from schwa.tagger import CharVocabulary, TaggerConfig, TaggerRestorer  # noqa: E402

VOCABULARY = CharVocabulary(list("abcdefghijklmnopqrstuvwxyz "))
CONFIG = TaggerConfig(embedding=8, hidden=8, layers=1, dropout=0.0, window=16, overlap=4)


@pytest.fixture
def model() -> CharTagger:
    torch.manual_seed(0)
    return CharTagger(len(VOCABULARY), CONFIG)


class TestWindows:
    def test_a_short_text_is_one_window(self):
        assert _window_bounds(10, window=16, overlap=4) == [(0, 10, 0, 10)]

    def test_windows_cover_every_character_exactly_once(self):
        for length in (17, 40, 99, 256):
            bounds = _window_bounds(length, window=16, overlap=4)
            covered = [index for _, _, start, end in bounds for index in range(start, end)]
            assert covered == list(range(length))

    def test_every_committed_part_sits_inside_its_window(self):
        for start, end, commit_start, commit_end in _window_bounds(99, window=16, overlap=4):
            assert start <= commit_start < commit_end <= end


class TestEncoding:
    def test_pads_to_the_longest_text(self):
        ids, mask = encode_batch(["abc", "a"], VOCABULARY)
        assert ids.shape == (2, 3)
        assert mask.tolist() == [[True, True, True], [True, False, False]]
        assert ids[1, 1:].tolist() == [0, 0]


class TestPrediction:
    def test_returns_one_label_per_character(self, model: CharTagger):
        texts = ["sence neden", "a", "x" * 60]
        labels = predict_labels(model, VOCABULARY, texts, CONFIG)
        assert [len(row) for row in labels] == [len(text) for text in texts]

    def test_labels_are_binary(self, model: CharTagger):
        labels = predict_labels(model, VOCABULARY, ["sence neden basliyaq"], CONFIG)
        assert set(labels[0]) <= {0, 1}

    def test_an_untrained_model_still_only_changes_diacritics(self, model: CharTagger):
        from schwa.alphabet import strip_diacritics

        restorer = TaggerRestorer(
            lambda texts: predict_labels(model, VOCABULARY, texts, CONFIG), CONFIG
        )
        text = "sence neden basliyaq"
        assert strip_diacritics(restorer.restore(text)) == text


class TestCheckpoints:
    def test_a_checkpoint_round_trips(self, model: CharTagger, tmp_path):
        path = tmp_path / "tagger.pt"
        save_checkpoint(path, model, VOCABULARY, CONFIG)

        predict, config = load_predictor(path, device="cpu")
        assert config == CONFIG
        assert predict(["sence"]) == predict_labels(model, VOCABULARY, ["sence"], CONFIG)
