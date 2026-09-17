"""Tests for the lexicon, the restorers and the scoring."""

from __future__ import annotations

import pytest
from duzelt.alphabet import strip_diacritics
from duzelt.lexicon import Lexicon
from duzelt.metrics import evaluate
from duzelt.restore import IdentityRestorer, LexiconRestorer, restore_case
from duzelt.tokenize import key_of, words_of
from hypothesis import given
from hypothesis import strategies as st

SENTENCES = [
    "Səncə nədən başlayaq?",
    "Qız məktəbə getdi.",
    "Qız bağçada oynayır.",
    "İşıq söndü.",
    "Şəhərdə yaşayır.",
]


@pytest.fixture
def lexicon() -> Lexicon:
    return Lexicon.from_sentences(SENTENCES)


class TestTokenize:
    def test_key_ignores_case_and_diacritics(self):
        assert key_of("Səncə") == key_of("sence") == "sence"
        assert key_of("İŞIQ") == key_of("isiq") == "isiq"

    def test_words_exclude_punctuation(self):
        assert words_of("Səncə nədən başlayaq?") == ["Səncə", "nədən", "başlayaq"]


class TestLexicon:
    def test_counts_forms_per_key(self, lexicon: Lexicon):
        assert lexicon.candidates("qiz") == [("qız", 2)]
        assert lexicon.best("sence") == "səncə"

    def test_reports_ambiguity(self):
        lexicon = Lexicon.from_sentences(["Qız gəldi.", "Qiz sözü yoxdur."])
        assert lexicon.is_ambiguous("qiz")
        assert not lexicon.is_ambiguous("geldi")

    def test_unknown_key_has_no_candidates(self, lexicon: Lexicon):
        assert lexicon.candidates("yoxdur") == []
        assert lexicon.best("yoxdur") is None

    def test_survives_a_save_and_load_round_trip(self, lexicon: Lexicon, tmp_path):
        path = tmp_path / "lexicon.jsonl"
        lexicon.save(path)
        reloaded = Lexicon.load(path)
        assert len(reloaded) == len(lexicon)
        assert reloaded.candidates("qiz") == lexicon.candidates("qiz")

    def test_prune_drops_rare_spellings(self):
        lexicon = Lexicon.from_sentences(["Qız qız qız gəldi.", "Qiz sözü."])
        lexicon.prune(min_count=2)
        assert lexicon.candidates("qiz") == [("qız", 3)]


class TestCaseRestoration:
    @pytest.mark.parametrize(
        ("typed", "form", "expected"),
        [
            ("sence", "səncə", "səncə"),
            ("Sence", "səncə", "Səncə"),
            ("SENCE", "səncə", "SƏNCƏ"),
            ("Idman", "idman", "İdman"),
            ("ISIQ", "ışıq", "IŞIQ"),
        ],
    )
    def test_matches_the_typed_capitalisation(self, typed: str, form: str, expected: str):
        assert restore_case(typed, form) == expected


class TestRestorers:
    def test_identity_changes_nothing(self):
        assert IdentityRestorer().restore("sence neden") == "sence neden"

    def test_lexicon_restores_known_words(self, lexicon: Lexicon):
        assert LexiconRestorer(lexicon).restore("sence neden baslayaq?") == (
            "səncə nədən başlayaq?"
        )

    def test_lexicon_keeps_unknown_words_untouched(self, lexicon: Lexicon):
        assert LexiconRestorer(lexicon).restore("kompyuter") == "kompyuter"

    def test_lexicon_keeps_punctuation_and_spacing(self, lexicon: Lexicon):
        text = "  Isiq   sondu...  "
        assert LexiconRestorer(lexicon).restore(text) == "  İşıq   söndü...  "

    @given(st.text(alphabet="sencdiqzbaşlöüğ ?.!", max_size=80))
    def test_lexicon_only_ever_changes_diacritics(self, text: str):
        restorer = LexiconRestorer(Lexicon.from_sentences(SENTENCES))
        assert strip_diacritics(restorer.restore(text)) == strip_diacritics(text)


class TestEvaluate:
    def test_perfect_prediction_scores_one(self, lexicon: Lexicon):
        scores = evaluate(SENTENCES, SENTENCES, lexicon)
        assert scores.word_accuracy == 1.0
        assert scores.sentence_accuracy == 1.0
        assert scores.character_error_rate == 0.0

    def test_typed_input_scores_the_stripped_words_as_wrong(self, lexicon: Lexicon):
        references = ["Səncə nədən başlayaq?"]
        predictions = [strip_diacritics(references[0])]
        scores = evaluate(references, predictions, lexicon)
        assert scores.words == 3
        assert scores.words_correct == 0
        assert scores.sentence_accuracy == 0.0

    def test_counts_ambiguous_words_separately(self):
        lexicon = Lexicon.from_sentences(["Qız gəldi.", "Qız getdi.", "Qiz sözü."])
        scores = evaluate(["Qız gəldi."], ["Qiz gəldi."], lexicon)
        assert scores.ambiguous_words == 1
        assert scores.ambiguous_correct == 0

    def test_rejects_a_prediction_that_rewrote_the_text(self, lexicon: Lexicon):
        with pytest.raises(ValueError):
            evaluate(["Səncə gəldi."], ["Səncə getdi."], lexicon)
