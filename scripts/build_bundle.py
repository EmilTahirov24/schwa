"""Put the shipped model inside the Python package.

`pip install schwa-az` should restore text on the first line of code, with no files to fetch
and no flags to pass. That means carrying two things: the quantised tagger, and the part of
the lexicon that is safe to apply without context — the words the training text was unanimous
about. Together they are the same "hybrid" that scores best, at about 4 MB.

    uv run --group train python scripts/build_bundle.py
"""

from __future__ import annotations

import argparse
import gzip
import shutil
import sys
from pathlib import Path

from schwa.lexicon import Lexicon
from schwa.spelling import Speller

DEFAULT_MODEL = Path("models/tagger.int8.onnx")
DEFAULT_LEXICON = Path("data/processed/lexicon.jsonl")
DEFAULT_OUT = Path("packages/core/schwa/data")

MIN_COUNT = 2


def write_confident_lexicon(lexicon: Lexicon, path: Path) -> tuple[int, int]:
    """Write the entries that can be applied without looking at the context.

    A key qualifies when the training text only ever spelled it one way, that spelling was
    seen at least twice, and it actually differs from what a plain keyboard produces — an
    entry that changes nothing is only weight.
    """
    rows = []
    for key in lexicon:
        candidates = lexicon.candidates(key)
        if len(candidates) != 1:
            continue
        form, count = candidates[0]
        if count >= MIN_COUNT and form != key:
            rows.append(f"{key}\t{form}\t{count}")

    payload = "\n".join(sorted(rows)).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(payload, 9))
    return len(rows), path.stat().st_size


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--lexicon", type=Path, default=DEFAULT_LEXICON)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    for path in (args.model, args.lexicon):
        if not path.exists():
            print(f"missing: {path}", file=sys.stderr)
            return 1

    args.out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.model, args.out / "tagger.onnx")
    shutil.copyfile(args.model.with_suffix(".json"), args.out / "tagger.json")

    lexicon = Lexicon.load(args.lexicon)
    entries, size = write_confident_lexicon(lexicon, args.out / "lexicon.tsv.gz")

    # The spell checker needs every common word, not only the ones with diacritics, plus the
    # endings that make a rare inflected form plausible.
    speller = Speller.from_lexicon(lexicon)
    vocabulary = args.out / "vocabulary.tsv.gz"
    words = speller.save(vocabulary)
    print(
        f"vocabulary {vocabulary.stat().st_size / 1e6:.1f} MB ({words} words, "
        f"{len(speller.suffixes)} endings)"
    )

    total = sum(path.stat().st_size for path in args.out.iterdir())
    print(f"model      {(args.out / 'tagger.onnx').stat().st_size / 1e6:.1f} MB")
    print(f"lexicon    {size / 1e6:.1f} MB ({entries} entries)")
    print(f"bundle     {total / 1e6:.1f} MB -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
