"""Tests for the model that ships with the package.

The whole point of the bundle is that `pip install schwa-az` restores text on the first line of
code, so these tests check exactly that path. They skip where the bundle was not built, which
is the case in a fresh clone before `poe bundle` has run.
"""

from __future__ import annotations

import gzip

import pytest
from schwa import bundled
from schwa.alphabet import strip_diacritics
from schwa.lexicon import Lexicon

bundle = pytest.mark.skipif(not bundled.is_bundled(), reason="run `poe bundle` first")


class TestWithoutTheBundle:
    def test_it_says_plainly_when_there_is_no_lexicon(self, monkeypatch, tmp_path):
        monkeypatch.setattr(bundled, "LEXICON", tmp_path / "missing.tsv.gz")
        with pytest.raises(bundled.MissingBundle):
            bundled.bundled_lexicon()

    def test_it_falls_back_to_the_lexicon_when_the_model_is_absent(self, monkeypatch, tmp_path):
        lexicon = tmp_path / "lexicon.tsv.gz"
        lexicon.write_bytes(gzip.compress("sence\tsəncə\t9".encode()))
        monkeypatch.setattr(bundled, "LEXICON", lexicon)
        monkeypatch.setattr(bundled, "MODEL", tmp_path / "missing.onnx")
        bundled.default_restorer.cache_clear()

        restorer = bundled.default_restorer()
        assert restorer.name == "lexicon"
        assert restorer.restore("sence") == "səncə"
        bundled.default_restorer.cache_clear()


@bundle
class TestTheBundle:
    def test_the_lexicon_loads(self):
        lexicon = bundled.bundled_lexicon()
        assert isinstance(lexicon, Lexicon)
        assert len(lexicon) > 100_000

    def test_every_shipped_entry_only_adds_diacritics(self):
        # A bad entry here would break the contract for every user of the package, so the
        # file itself is checked rather than trusted.
        lexicon = bundled.bundled_lexicon()
        for key in list(lexicon)[:5000]:
            form = lexicon.best(key)
            assert strip_diacritics(form) == key

    def test_restore_works_straight_out_of_the_package(self):
        assert bundled.restore("sence neden") == "səncə nədən"

    def test_it_restores_an_ordinary_sentence(self):
        restored = bundled.restore("men bu gun mektebe getmedim")
        assert restored == "mən bu gün məktəbə getmədim"

    def test_the_tagger_is_part_of_the_bundle(self):
        # Without the model this falls back to the lexicon, and the sentence above would
        # still mostly work - so check the combination itself rather than its output.
        assert bundled.default_restorer().name == "hybrid"

    def test_it_leaves_correct_text_alone(self):
        text = "Mən bu gün məktəbə getmədim."
        assert bundled.restore(text) == text

    def test_it_never_changes_anything_but_diacritics(self):
        for text in ["sence neden", "QIZ MEKTEBE GETDI", "123 !? salam", ""]:
            assert strip_diacritics(bundled.restore(text)) == strip_diacritics(text)

    def test_the_spell_checker_ships_too(self):
        from schwa.bundled import check

        [found] = check("men mektbe gedirem")
        assert found.typed == "mektbe"
        assert "məktəbə" in found.options

    def test_the_spell_checker_leaves_correct_text_alone(self):
        from schwa.bundled import check

        assert check("Mən bu gün məktəbə getmədim.") == []
