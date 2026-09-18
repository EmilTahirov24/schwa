"""Export a trained tagger to ONNX and check that it still gives the same answers.

    uv run --group train python scripts/export_onnx.py --checkpoint models/tagger.pt

The exported graph takes a padded batch of character ids and returns two scores per
character, with both the batch size and the length left dynamic.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch
from schwa._tagger_model import CharTagger, predict_labels
from schwa.onnx_tagger import load_onnx_predictor, write_sidecar
from schwa.tagger import CharVocabulary, config_from_dict

DEFAULT_CHECKPOINT = Path("models/tagger.pt")
DEFAULT_OUT = Path("models/tagger.onnx")

# Varied lengths, and enough of them to fill more than one batch. Torch warns that an LSTM
# exported at batch size one can misbehave at other sizes, so the check has to exercise that
# rather than take the warning's word for it.
SAMPLES = [
    "sence neden basliyaq",
    "isiq sondu ve hec kim gelmedi",
    "usaqlar bagcada oynayirdi, men ise mektebe getdim",
    "salam",
    "a",
    "bugun hava cox gozel idi, ona gore parkda gezdik ve sonra kitab oxuduq",
] * 30


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    if not args.checkpoint.exists():
        print(f"missing checkpoint: {args.checkpoint}", file=sys.stderr)
        return 1

    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=True)
    vocabulary = CharVocabulary(checkpoint["characters"])
    config = config_from_dict(checkpoint["config"])
    model = CharTagger(len(vocabulary), config)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    example = torch.zeros((1, config.window), dtype=torch.long)

    torch.onnx.export(
        model,
        (example,),
        str(args.out),
        input_names=["ids"],
        output_names=["logits"],
        dynamic_axes={"ids": {0: "batch", 1: "length"}, "logits": {0: "batch", 1: "length"}},
        opset_version=17,
        dynamo=False,
    )
    sidecar = write_sidecar(args.out, vocabulary, config)

    # An export that silently changes the answers is worse than no export.
    from_torch = predict_labels(model, vocabulary, SAMPLES, config, device="cpu")
    predict, _ = load_onnx_predictor(args.out)
    from_onnx = predict(SAMPLES)

    if from_torch != from_onnx:
        print("the exported model disagrees with the checkpoint", file=sys.stderr)
        return 1

    size = args.out.stat().st_size / 1e6
    print(f"exported {size:.1f} MB -> {args.out} (+ {sidecar.name}); answers match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
