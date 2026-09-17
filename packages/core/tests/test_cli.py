"""Tests for the command line entry point."""

from __future__ import annotations

import pytest
from duzelt.cli import ENV_LEXICON, main
from duzelt.lexicon import Lexicon


@pytest.fixture
def lexicon_file(tmp_path):
    lexicon = Lexicon.from_sentences(["Səncə nədən başlayaq?", "İşıq söndü."])
    path = tmp_path / "lexicon.jsonl"
    lexicon.save(path)
    return path


def test_fixes_text_given_as_arguments(lexicon_file, capsys):
    assert main(["--lexicon", str(lexicon_file), "sence", "neden", "baslayaq?"]) == 0
    assert capsys.readouterr().out == "səncə nədən başlayaq?\n"


def test_reads_stdin_when_no_text_is_given(lexicon_file, capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin.read", lambda: "isiq sondu.")
    assert main(["--lexicon", str(lexicon_file)]) == 0
    assert capsys.readouterr().out == "işıq söndü."


def test_takes_the_lexicon_from_the_environment(lexicon_file, capsys, monkeypatch):
    monkeypatch.setenv(ENV_LEXICON, str(lexicon_file))
    assert main(["sence"]) == 0
    assert capsys.readouterr().out == "səncə\n"


def test_explains_itself_when_no_lexicon_is_configured(capsys, monkeypatch):
    monkeypatch.delenv(ENV_LEXICON, raising=False)
    assert main(["sence"]) == 2
    assert ENV_LEXICON in capsys.readouterr().err


def test_reports_a_missing_lexicon_file(tmp_path, capsys):
    assert main(["--lexicon", str(tmp_path / "nope.jsonl"), "sence"]) == 1
    assert "not found" in capsys.readouterr().err
