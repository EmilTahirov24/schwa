"""Tests for the spell checker."""

from __future__ import annotations

import pytest
from schwa.spelling import Speller, edits1

# A small language: counts chosen so the rules can be seen working.
WORDS = {
    "xahis": ("xahiş", 1711),
    "xalis": ("xalis", 506),
    "xayis": ("xayiş", 4),
    "sonra": ("sonra", 137_108),
    "sora": ("sora", 119),
    "ev": ("ev", 8895),
    "ve": ("və", 1_084_336),
    "ne": ("nə", 12_463),
    "nem": ("nəm", 318),
    "bilim": ("bilim", 90),
    "kitab": ("kitab", 5000),
    "kitablar": ("kitablar", 900),
    "qelem": ("qələm", 700),
    "qelemler": ("qələmlər", 300),
    "mekteb": ("məktəb", 4000),
    "men": ("mən", 50_000),
    "gedirem": ("gedirəm", 800),
    "uzaqdir": ("uzaqdır", 300),
    "dunen": ("dünən", 2000),
    "geldi": ("gəldi", 9000),
}


@pytest.fixture
def speller() -> Speller:
    # "lar"/"ler" count as an ending here because they follow known stems.
    return Speller(WORDS, suffixes={"lar", "ler", "lari"}, min_count=5)


class TestEdits:
    def test_cover_the_four_kinds_of_slip(self):
        edits = set(edits1("ab"))
        assert "b" in edits  # deletion
        assert "ba" in edits  # transposition
        assert "ac" in edits  # substitution
        assert "abc" in edits  # insertion

    def test_never_use_a_letter_the_keys_do_not_have(self):
        assert not any("w" in edit for edit in edits1("ab"))


class TestSuspicion:
    def test_an_unknown_word_is_suspect(self, speller: Speller):
        assert speller.is_suspicious("mektb")

    def test_a_rare_spelling_next_to_a_common_one_is_suspect(self, speller: Speller):
        # Four occurrences is below the vocabulary floor, so it counts as unknown.
        assert speller.is_suspicious("xayis")

    def test_a_common_word_is_never_suspect_however_close_a_bigger_one_is(self, speller: Speller):
        # "ev" (house) is one edit from "və", which is a hundred times more common. That
        # made the first version flag it; common words are now left alone.
        assert not speller.is_suspicious("ev")

    def test_a_known_stem_with_a_common_ending_is_plausible(self, speller: Speller):
        # Never seen, but "kitab" + "lari" reads as a real word.
        assert speller.plausible("kitablari")
        assert not speller.is_suspicious("kitablari")

    def test_short_words_are_not_judged(self, speller: Speller):
        assert not speller.is_suspicious("xy")


class TestSuggestions:
    def test_a_missing_letter_comes_back(self, speller: Speller):
        assert speller.suggest("mektb")[0] == "məktəb"

    def test_the_more_common_reading_ranks_first(self, speller: Speller):
        options = speller.suggest("xayis")
        assert options[0] == "xahiş"
        assert "xalis" in options

    def test_a_word_written_together_can_be_split(self, speller: Speller):
        options = speller.suggest("nebilim")
        assert "nə bilim" in options

    def test_suggestions_keep_the_capitalisation(self, speller: Speller):
        assert speller.suggest("Mektb")[0] == "Məktəb"

    def test_a_capitalised_word_mid_sentence_is_taken_for_a_name(self, speller: Speller):
        assert speller.suggest("Mektb", sentence_start=False) == ()

    def test_a_correct_word_gets_nothing(self, speller: Speller):
        assert speller.suggest("kitab") == ()


class TestCheck:
    def test_finds_the_misspelt_word_in_a_sentence(self, speller: Speller):
        [found] = speller.check("mən mektb gedirəm")
        assert (found.start, found.end, found.typed) == (4, 9, "mektb")
        assert found.options[0] == "məktəb"

    def test_a_name_inside_a_sentence_is_left_alone(self, speller: Speller):
        assert speller.check("dünən Mektb gəldi") == []

    def test_the_first_word_of_a_sentence_is_still_checked(self, speller: Speller):
        assert [s.typed for s in speller.check("Mektb uzaqdır. Mektb")] == ["Mektb", "Mektb"]

    def test_serialises_for_the_page(self, speller: Speller):
        [found] = speller.check("mektb")
        assert found.as_dict()["options"][0] == "məktəb"


class TestStorage:
    def test_survives_a_save_and_load_round_trip(self, speller: Speller, tmp_path):
        path = tmp_path / "vocabulary.tsv.gz"
        written = speller.save(path)
        reloaded = Speller.load(path)
        assert written == len(reloaded.words)
        assert reloaded.suffixes == speller.suffixes
        assert reloaded.suggest("mektb") == speller.suggest("mektb")

    def test_save_can_drop_rare_words(self, speller: Speller, tmp_path):
        path = tmp_path / "vocabulary.tsv.gz"
        speller.save(path, min_count=1000)
        assert "xalis" not in Speller.load(path).words


class TestSuffixes:
    def test_an_ending_after_many_stems_is_found(self):
        words = {f"stem{letter}": (f"stem{letter}", 10) for letter in "abcdefghij"}
        words.update({f"stem{letter}lar": (f"stem{letter}lar", 10) for letter in "abcdefghij"})
        assert "lar" in Speller.find_suffixes(words, min_count=5, min_stems=10)

    def test_an_ending_after_few_stems_is_not(self):
        words = {"kitab": ("kitab", 10), "kitabxyz": ("kitabxyz", 10)}
        assert "xyz" not in Speller.find_suffixes(words, min_count=5, min_stems=2)


class TestPersonalEndings:
    """Wikipedia is third person; people writing messages are not."""

    def test_a_first_person_form_of_a_known_verb_is_plausible(self):
        from schwa.lexicon import Lexicon

        # "getmədi" (he did not go) is common; "getmədim" (I did not go) never appears.
        lexicon = Lexicon.from_sentences(["O getmədi."] * 10)
        speller = Speller.from_lexicon(lexicon)
        assert speller.plausible("getmedim")
        assert not speller.is_suspicious("getmedim")

    def test_the_grammar_endings_travel_with_the_saved_vocabulary(self, tmp_path):
        from schwa.lexicon import Lexicon
        from schwa.spelling import PERSONAL_ENDINGS

        speller = Speller.from_lexicon(Lexicon.from_sentences(["O getmədi."] * 10))
        path = tmp_path / "vocabulary.tsv.gz"
        speller.save(path)
        assert Speller.load(path).suffixes >= PERSONAL_ENDINGS


class TestSplitsAreALastResort:
    def test_no_split_is_offered_when_a_single_word_is_one_edit_away(self):
        words = {"mekteb": ("məktəb", 4000), "mek": ("mək", 50), "the": ("the", 900)}
        speller = Speller(words, min_count=5)
        assert all(" " not in option for option in speller.suggest("mektbe"))
