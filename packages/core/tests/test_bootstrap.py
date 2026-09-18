"""Tests for the per-group scores and the bootstrap intervals built on them."""

from __future__ import annotations

import pytest
from schwa.alphabet import strip_diacritics
from schwa.lexicon import Lexicon
from schwa.metrics import COUNTS, bootstrap, evaluate

pytest.importorskip("numpy")

REFERENCES = [
    "Qız məktəbə getdi.",
    "Səncə nədən başlayaq?",
    "Şəhərdə yaşayır.",
    "İşıq söndü.",
] * 10


@pytest.fixture
def lexicon() -> Lexicon:
    return Lexicon.from_sentences(REFERENCES)


def half_right(references: list[str], wrong_every: int) -> list[str]:
    """Strip the diacritics from every `wrong_every`-th sentence, leave the rest correct."""
    return [
        strip_diacritics(sentence) if index % wrong_every == 0 else sentence
        for index, sentence in enumerate(references)
    ]


class TestGroupedScores:
    def test_group_counts_add_up_to_the_totals(self, lexicon: Lexicon):
        predictions = half_right(REFERENCES, 3)
        labels = [index // 4 for index in range(len(REFERENCES))]
        scores = evaluate(REFERENCES, predictions, lexicon, groups=labels)

        assert len(scores.by_group) == 10
        for position, name in enumerate(COUNTS):
            assert sum(group[position] for group in scores.by_group.values()) == getattr(
                scores, name
            )

    def test_grouping_does_not_change_the_scores(self, lexicon: Lexicon):
        predictions = half_right(REFERENCES, 3)
        plain = evaluate(REFERENCES, predictions, lexicon)
        grouped = evaluate(REFERENCES, predictions, lexicon, groups=range(len(REFERENCES)))
        assert plain.as_dict() == grouped.as_dict()

    @pytest.mark.parametrize("labels", [range(3), range(100)])
    def test_rejects_labels_that_do_not_match_the_sentences(self, lexicon: Lexicon, labels):
        with pytest.raises(ValueError):
            evaluate(REFERENCES, REFERENCES, lexicon, groups=labels)


class TestBootstrap:
    def test_the_interval_holds_the_measured_rate(self, lexicon: Lexicon):
        scores = evaluate(
            REFERENCES, half_right(REFERENCES, 3), lexicon, groups=range(len(REFERENCES))
        )
        [intervals], _ = bootstrap([scores], resamples=500)
        interval = intervals["sentence_accuracy"]
        assert 0.0 <= interval.low <= scores.sentence_accuracy <= interval.high <= 1.0
        assert interval.low < interval.high

    def test_is_reproducible(self, lexicon: Lexicon):
        scores = evaluate(
            REFERENCES, half_right(REFERENCES, 3), lexicon, groups=range(len(REFERENCES))
        )
        assert bootstrap([scores], resamples=200) == bootstrap([scores], resamples=200)

    def test_a_system_does_not_differ_from_itself(self, lexicon: Lexicon):
        scores = evaluate(
            REFERENCES, half_right(REFERENCES, 3), lexicon, groups=range(len(REFERENCES))
        )
        _, [difference] = bootstrap([scores, scores], resamples=200)
        assert difference["word_accuracy"].low == difference["word_accuracy"].high == 0.0

    def test_a_clearly_better_system_wins_the_paired_comparison(self, lexicon: Lexicon):
        labels = range(len(REFERENCES))
        worse = evaluate(REFERENCES, half_right(REFERENCES, 2), lexicon, groups=labels)
        better = evaluate(REFERENCES, REFERENCES, lexicon, groups=labels)
        _, [difference] = bootstrap([worse, better], resamples=500)
        assert difference["sentence_accuracy"].low > 0

    def test_correlated_sentences_widen_the_interval(self, lexicon: Lexicon):
        # Whole groups of four are right or wrong together, as sentences of one article
        # tend to be. Resampling them one by one would pretend there were four times as
        # many independent observations as there are.
        references = REFERENCES * 5
        predictions = [
            strip_diacritics(sentence) if (index // 4) % 3 == 0 else sentence
            for index, sentence in enumerate(references)
        ]
        by_sentence = evaluate(references, predictions, lexicon, groups=range(len(references)))
        by_group = evaluate(
            references, predictions, lexicon, groups=[index // 4 for index in range(200)]
        )

        def width(scores) -> float:
            [intervals], _ = bootstrap([scores], resamples=1000)
            return intervals["sentence_accuracy"].high - intervals["sentence_accuracy"].low

        assert width(by_group) > 1.5 * width(by_sentence)

    def test_compares_any_pair_asked_for(self, lexicon: Lexicon):
        labels = range(len(REFERENCES))
        worst = evaluate(REFERENCES, half_right(REFERENCES, 1), lexicon, groups=labels)
        middle = evaluate(REFERENCES, half_right(REFERENCES, 2), lexicon, groups=labels)
        best = evaluate(REFERENCES, REFERENCES, lexicon, groups=labels)
        _, [best_over_worst, worst_over_middle] = bootstrap(
            [worst, middle, best], resamples=300, pairs=[(0, 2), (1, 0)]
        )
        assert best_over_worst["sentence_accuracy"].low == 1.0
        assert worst_over_middle["sentence_accuracy"].high < 0

    def test_needs_groups(self, lexicon: Lexicon):
        with pytest.raises(ValueError):
            bootstrap([evaluate(REFERENCES, REFERENCES, lexicon)])
