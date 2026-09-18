"""Tests for picking the restorer a deployment actually has files for."""

from __future__ import annotations

import pytest
from schwa.context import ContextModel
from schwa.lexicon import Lexicon
from schwa.restore import IdentityRestorer
from schwa_api.restorers import ENV_CONTEXT, ENV_LEXICON, ENV_TAGGER, load_restorer

SENTENCES = ["Səncə nədən başlayaq?", "İşıq söndü."]


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for variable in (ENV_LEXICON, ENV_CONTEXT, ENV_TAGGER):
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


@pytest.fixture
def onnx_stand_in(monkeypatch, tmp_path):
    """An .onnx path that routes past torch, without needing a real model file."""
    import schwa.onnx_tagger as onnx_tagger

    stand_in = IdentityRestorer()
    stand_in.name = "tagger (onnx)"
    monkeypatch.setattr(onnx_tagger, "load_onnx_restorer", lambda path: stand_in)

    model = tmp_path / "tagger.onnx"
    model.write_bytes(b"")
    monkeypatch.setenv(ENV_TAGGER, str(model))
    return model


def test_a_tagger_alone_is_served_on_its_own(onnx_stand_in):
    loaded = load_restorer()
    assert loaded.name == "tagger (onnx)"
    assert loaded.sources == {"tagger": str(onnx_stand_in)}


def test_a_tagger_next_to_a_lexicon_is_served_as_the_hybrid(
    monkeypatch, onnx_stand_in, lexicon_file
):
    # Measured on dev, the lexicon overruling the tagger on unanimous words is worth 1.5
    # points of whole-sentence accuracy, so a deployment with both must use both.
    monkeypatch.setenv(ENV_LEXICON, str(lexicon_file))

    loaded = load_restorer()
    assert loaded.name == "hybrid"
    assert set(loaded.sources) == {"tagger", "lexicon"}
