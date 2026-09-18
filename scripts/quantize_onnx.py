"""Shrink the exported tagger with dynamic int8 quantisation, and measure what it costs.

A smaller model is the difference between shipping it inside the browser extension and
asking the browser to download it. Quantisation is only worth taking if the accuracy it
costs is small, so this script reports both rather than just doing it.

    uv run --group train python scripts/quantize_onnx.py
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

from schwa.alphabet import is_foldable, strip_diacritics, to_labels
from schwa.onnx_tagger import load_onnx_predictor, sidecar_path

DEFAULT_IN = Path("models/tagger.onnx")
DEFAULT_OUT = Path("models/tagger.int8.onnx")
DEFAULT_DEV = Path("data/processed/dev.txt")


def decision_accuracy(predict, sentences: list[str]) -> tuple[float, float]:
    """Accuracy on the characters that needed a decision, and seconds taken."""
    typed = [strip_diacritics(sentence) for sentence in sentences]

    started = time.perf_counter()
    predictions = predict(typed)
    elapsed = time.perf_counter() - started

    correct = total = 0
    for sentence, predicted in zip(sentences, predictions, strict=True):
        stripped, labels = to_labels(sentence)
        for char, expected, got in zip(stripped, labels, predicted, strict=True):
            if is_foldable(char):
                total += 1
                correct += expected == got

    return (correct / total if total else 0.0), elapsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=DEFAULT_IN)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--dev", type=Path, default=DEFAULT_DEV)
    parser.add_argument("--sentences", type=int, default=3000)
    args = parser.parse_args()

    if not args.model.exists():
        print(f"missing model: {args.model}", file=sys.stderr)
        return 1

    from onnxruntime.quantization import QuantType, quantize_dynamic

    quantize_dynamic(str(args.model), str(args.out), weight_type=QuantType.QInt8)
    shutil.copyfile(sidecar_path(args.model), sidecar_path(args.out))

    sentences = args.dev.read_text(encoding="utf-8").splitlines()[: args.sentences]
    results = {}
    for name, path in (("float32", args.model), ("int8", args.out)):
        predict, _ = load_onnx_predictor(path)
        accuracy, elapsed = decision_accuracy(predict, sentences)
        results[name] = (path.stat().st_size / 1e6, accuracy, elapsed)

    print(f"\n{len(sentences)} dev sentences\n")
    print(f"{'model':<8} {'size MB':>8} {'decisions':>10} {'seconds':>9}")
    for name, (size, accuracy, elapsed) in results.items():
        print(f"{name:<8} {size:>8.1f} {accuracy:>10.4f} {elapsed:>9.2f}")

    lost = results["float32"][1] - results["int8"][1]
    smaller = results["float32"][0] / results["int8"][0]
    print(f"\nint8 is {smaller:.1f}x smaller and loses {lost * 100:.2f} points of accuracy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
