"""Tests for Azerbaijani case mapping, folding, and character labels."""

from __future__ import annotations

import pytest
from duzelt.alphabet import (
    FOLD_PAIRS,
    LABEL_KEEP,
    LABEL_MARK,
    STRIP_MAP,
    apply_labels,
    az_lower,
    az_upper,
    strip_diacritics,
    to_labels,
)
from hypothesis import given
from hypothesis import strategies as st

AZ_LOWER = "abcçdeəfgğhxıijkqlmnoöprsştuüvyz"
AZ_UPPER = "ABCÇDEƏFGĞHXIİJKQLMNOÖPRSŞTUÜVYZ"

# Text built from the alphabet plus the characters that must survive untouched.
az_text = st.text(alphabet=AZ_LOWER + AZ_UPPER + " .,!?-0123456789", max_size=200)


class TestCaseMapping:
    def test_lowercase_keeps_the_two_i_families_apart(self):
        assert az_lower("IŞIQ") == "ışıq"
        assert az_lower("İSTİFADƏ") == "istifadə"

    def test_uppercase_keeps_the_two_i_families_apart(self):
        assert az_upper("ışıq") == "IŞIQ"
        assert az_upper("istifadə") == "İSTİFADƏ"

    def test_python_builtins_are_wrong_here(self):
        # Documents why this module exists. Unicode's default casing maps dotless "ı"
        # to "I" correctly, but it loses the distinction in the other three cases.
        assert "IŞIQ".lower() == "işiq"  # should be "ışıq"
        assert "istifadə".upper() == "ISTIFADƏ"  # should be "İSTİFADƏ"
        assert len("İ".lower()) == 2  # "i" plus a combining dot above

    @pytest.mark.parametrize("letter", list(AZ_LOWER))
    def test_case_round_trip_over_the_alphabet(self, letter: str):
        assert az_lower(az_upper(letter)) == letter

    @given(az_text)
    def test_case_change_preserves_length(self, text: str):
        assert len(az_lower(text)) == len(text)
        assert len(az_upper(text)) == len(text)


class TestStripping:
    def test_strips_a_sentence_the_way_people_type_it(self):
        assert strip_diacritics("səncə nədən başlayaq") == "sence neden baslayaq"

    def test_uppercase_dotted_i_becomes_plain_i(self):
        assert strip_diacritics("İSTİFADƏ") == "ISTIFADE"

    def test_leaves_ascii_text_alone(self):
        assert strip_diacritics("hello world 123") == "hello world 123"

    @given(az_text)
    def test_preserves_length(self, text: str):
        assert len(strip_diacritics(text)) == len(text)

    @given(az_text)
    def test_is_idempotent(self, text: str):
        once = strip_diacritics(text)
        assert strip_diacritics(once) == once

    @given(az_text)
    def test_only_touches_the_fourteen_letters(self, text: str):
        for original, stripped in zip(text, strip_diacritics(text), strict=True):
            if original == stripped:
                continue
            assert original in STRIP_MAP
            assert stripped == STRIP_MAP[original]


class TestLabels:
    def test_labels_mark_only_the_hidden_letters(self):
        stripped, labels = to_labels("səncə")
        assert stripped == "sence"
        # s e n c e -> only the two "e" characters stand for "ə"; the "c" is a real "c".
        assert labels == [LABEL_KEEP, LABEL_MARK, LABEL_KEEP, LABEL_KEEP, LABEL_MARK]

    def test_dotless_i_is_a_marked_lowercase_i(self):
        stripped, labels = to_labels("qız")
        assert stripped == "qiz"
        assert labels == [LABEL_KEEP, LABEL_MARK, LABEL_KEEP]

    def test_dotted_capital_i_is_a_marked_uppercase_i(self):
        stripped, labels = to_labels("İdman")
        assert stripped == "Idman"
        assert labels[0] == LABEL_MARK

    @given(az_text)
    def test_labels_rebuild_the_original(self, text: str):
        assert apply_labels(*to_labels(text)) == text

    @given(az_text)
    def test_marked_characters_strip_back_to_what_they_replaced(self, text: str):
        stripped, labels = to_labels(text)
        assert strip_diacritics(apply_labels(stripped, labels)) == stripped

    def test_rejects_a_label_count_that_does_not_match(self):
        with pytest.raises(ValueError):
            apply_labels("sence", [LABEL_KEEP])


class TestFoldPairs:
    def test_every_ascii_form_hides_exactly_one_letter(self):
        # The reason restoration is a binary decision per character.
        assert len(FOLD_PAIRS) == len(STRIP_MAP)
        for ascii_form, az_letter in FOLD_PAIRS.items():
            assert STRIP_MAP[az_letter] == ascii_form
