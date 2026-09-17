"""Tests for sentence splitting."""

from __future__ import annotations

from duzelt.segment import split_sentences


def test_splits_on_sentence_punctuation():
    text = "Bu birinci cümlədir. Bu ikincidir! Üçüncüsü sualdır?"
    assert split_sentences(text) == [
        "Bu birinci cümlədir.",
        "Bu ikincidir!",
        "Üçüncüsü sualdır?",
    ]


def test_splits_on_line_breaks():
    assert split_sentences("Birinci sətir\nİkinci sətir") == ["Birinci sətir", "İkinci sətir"]


def test_keeps_abbreviations_inside_a_sentence():
    text = "Kitab, jurnal və s. burada saxlanılır. Növbəti cümlə."
    assert split_sentences(text) == [
        "Kitab, jurnal və s. burada saxlanılır.",
        "Növbəti cümlə.",
    ]


def test_keeps_initial_chains_together():
    text = "Şəhər b.e.ə. VII əsrdə salınıb. Sonra böyüdü."
    assert split_sentences(text) == ["Şəhər b.e.ə. VII əsrdə salınıb.", "Sonra böyüdü."]


def test_returns_nothing_for_blank_input():
    assert split_sentences("   \n\n  ") == []


def test_keeps_a_sentence_without_final_punctuation():
    assert split_sentences("Nöqtəsiz cümlə") == ["Nöqtəsiz cümlə"]
