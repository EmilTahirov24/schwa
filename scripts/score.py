"""Score any system's output on a test split, exactly the way every number here is scored.

Write out the split as a system would receive it - diacritics removed, one sentence per
line - run your system over that file, and score what comes back:

    uv run python scripts/score.py --split web_test --typed > typed.txt
    your-system < typed.txt > restored.txt
    uv run python scripts/score.py --split web_test restored.txt

A prediction may only put diacritics back; one that changes anything else is rejected
rather than scored. The report has the same metrics as docs/results.md, with 95% intervals
from the same bootstrap over whole articles or documents.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from schwa.alphabet import strip_diacritics
from schwa.lexicon import Lexicon
from schwa.metrics import RATES, bootstrap, evaluate

DATA = Path("data/processed")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("predictions", type=Path, nargs="?", help="one restored sentence per line")
    parser.add_argument("--split", default="test", choices=["dev", "test", "web_dev", "web_test"])
    parser.add_argument("--typed", action="store_true", help="print the input to restore, and stop")
    parser.add_argument("--resamples", type=int, default=1000)
    args = parser.parse_args()

    path = DATA / f"{args.split}.txt"
    if not path.exists():
        print(f"missing: {path} - build it with `poe data`", file=sys.stderr)
        return 1
    references = path.read_text(encoding="utf-8").splitlines()

    if args.typed:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdout.writelines(strip_diacritics(sentence) + "\n" for sentence in references)
        return 0
    if args.predictions is None:
        parser.error("give the file of predictions, or --typed")

    predictions = args.predictions.read_text(encoding="utf-8").splitlines()
    if len(predictions) != len(references):
        print(
            f"{len(predictions):,} predictions for {len(references):,} sentences", file=sys.stderr
        )
        return 1

    groups = path.with_suffix(".groups").read_text(encoding="utf-8").splitlines()
    lexicon = Lexicon.load(DATA / "lexicon.jsonl")
    try:
        scores = evaluate(references, predictions, lexicon, groups=groups)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    [intervals], _ = bootstrap([scores], resamples=args.resamples)

    print(f"{args.split}: {scores.sentences:,} sentences, {len(scores.by_group):,} groups")
    for rate in RATES:
        value, bounds = getattr(scores, rate), intervals[rate]
        print(f"  {rate:<22} {value:7.2%}  ({bounds.low:.2%} to {bounds.high:.2%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
