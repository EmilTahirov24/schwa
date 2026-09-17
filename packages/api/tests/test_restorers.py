"""Tests for picking the restorer a deployment actually has files for."""

from __future__ import annotations

import pytest
from duzelt.context import ContextModel
from duzelt.lexicon import Lexicon
from duzelt_api.restorers import ENV_CONTEXT, ENV_LEXICON, load_restorer

SENTENCES = ["Səncə nədən başlayaq?", "İşıq söndü."]


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for variable in (ENV_LEXICON, ENV_CONTEXT):
        monkeypatch.delenv(variable, raising=False)


@pytest.fixture
def lexicon_file(tmp_path):
    path = tmp_path / "lexicon.jsonl"
    Lexicon.from_sentences(SENTENCES).save(path)
    return path


@pytest.fixture
def context_file(tmp_path):
    path = tmp_path / "context.jsonl"
    model = ContextModel()
    model.observe("sence", "səncə", "<s>", "neden")
    model.save(path)
    return path


def test_without_any_files_it_changes_nothing(monkeypatch):
    loaded = load_restorer()
    assert loaded.name == "identity"
    assert loaded.sources == {}
    assert loaded.restorer.restore("sence") == "sence"


def test_a_lexicon_alone_is_enough(monkeypatch, lexicon_file):
    monkeypatch.setenv(ENV_LEXICON, str(lexicon_file))
    loaded = load_restorer()
    assert loaded.name == "lexicon"
    assert loaded.restorer.restore("sence") == "səncə"


def test_the_context_model_is_used_when_present(monkeypatch, lexicon_file, context_file):
    monkeypatch.setenv(ENV_LEXICON, str(lexicon_file))
    monkeypatch.setenv(ENV_CONTEXT, str(context_file))
    loaded = load_restorer()
    assert loaded.name == "context"
    assert set(loaded.sources) == {"lexicon", "context"}


def test_a_path_that_does_not_exist_is_ignored(monkeypatch, tmp_path):
    # A deployment with a typo in its configuration should fall back visibly rather than
    # crash on the first request.
    monkeypatch.setenv(ENV_LEXICON, str(tmp_path / "missing.jsonl"))
    assert load_restorer().name == "identity"


def test_an_empty_variable_is_ignored(monkeypatch):
    monkeypatch.setenv(ENV_LEXICON, "")
    assert load_restorer().name == "identity"
