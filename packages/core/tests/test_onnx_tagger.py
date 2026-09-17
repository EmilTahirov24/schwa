"""Tests for running the tagger from an ONNX file.

Skipped without torch, onnx and onnxruntime, which is the case in CI.
"""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("onnx")
pytest.importorskip("onnxruntime")

from duzelt._tagger_model import CharTagger, predict_labels  # noqa: E402
from duzelt.alphabet import strip_diacritics  # noqa: E402
from duzelt.onnx_tagger import (  # noqa: E402
    load_onnx_predictor,
    load_onnx_restorer,
    sidecar_path,
    write_sidecar,
)
from duzelt.tagger import CharVocabulary, TaggerConfig  # noqa: E402

VOCABULARY = CharVocabulary(list("abcdefghijklmnopqrstuvwxyz ,."))
CONFIG = TaggerConfig(embedding=8, hidden=8, layers=1, dropout=0.0, window=32, overlap=8)

TEXTS = ["sence neden", "a", "isiq sondu ve hec kim gelmedi", "salam dunya"] * 20


@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    """A tiny model exported the way the script exports the real one."""
    torch.manual_seed(0)
    model = CharTagger(len(VOCABULARY), CONFIG)
    model.eval()

    path = tmp_path_factory.mktemp("onnx") / "tagger.onnx"
    torch.onnx.export(
        model,
        (torch.zeros((1, CONFIG.window), dtype=torch.long),),
        str(path),
        input_names=["ids"],
        output_names=["logits"],
        dynamic_axes={"ids": {0: "batch", 1: "length"}, "logits": {0: "batch", 1: "length"}},
        opset_version=17,
        dynamo=False,
    )
    write_sidecar(path, VOCABULARY, CONFIG)
    return path, model


def test_the_sidecar_sits_next_to_the_model(exported):
    path, _ = exported
    assert sidecar_path(path).exists()
    assert sidecar_path(path).name == "tagger.json"


def test_it_agrees_with_the_checkpoint(exported):
    path, model = exported
    predict, config = load_onnx_predictor(path)
    assert config == CONFIG
    assert predict(TEXTS) == predict_labels(model, VOCABULARY, TEXTS, CONFIG, device="cpu")


def test_it_agrees_across_batch_sizes(exported):
    """The exported LSTM must not depend on how many texts arrive together."""
    path, _ = exported
    one_at_a_time, _ = load_onnx_predictor(path, batch_size=1)
    many, _ = load_onnx_predictor(path, batch_size=64)
    assert one_at_a_time(TEXTS) == many(TEXTS)


def test_the_restorer_only_changes_diacritics(exported):
    path, _ = exported
    restorer = load_onnx_restorer(path)
    assert restorer.name == "tagger (onnx)"
    for text in TEXTS[:4]:
        assert strip_diacritics(restorer.restore(text)) == text
