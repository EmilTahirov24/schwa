"""Does the threshold that defines "ambiguous" decide what the headline number says?

A second spelling of a typed form counts as a real reading, rather than as a typo in the
source text, once it reaches a share of that form's occurrences - 5% in
:data:`schwa.lexicon.MIN_MINORITY_SHARE`. The choice is a judgement, and it sets which words
the headline metric is measured on, so it deserves a number rather than an argument.

The same predictions are scored against several thresholds: how many words each one calls
ambiguous, how the lexicon and the shipped model do on them, and how far apart the two are.
The lexicon baseline is there because the gap between it and the model is what the metric
exists to show.

    uv run --group train python scripts/ambiguity_threshold.py --split test
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from evaluate import run
from results_page import write_section
from schwa.alphabet import strip_diacritics
from schwa.lexicon import MIN_MINORITY_COUNT, MIN_MINORITY_SHARE, Lexicon
from schwa.metrics import Scores, bootstrap, evaluate
from schwa.restore import HybridRestorer, LexiconRestorer

DATA = Path("data/processed")
SHARES = [0.01, 0.02, 0.05, 0.10, 0.20]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--split", default="test")
    parser.add_argument("--tagger", type=Path, default=Path("models/tagger.pt"))
    parser.add_argument("--shares", type=float, nargs="+", default=SHARES)
    parser.add_argument("--resamples", type=int, default=1000)
    parser.add_argument("--limit", type=int, default=0, help="score only the first N sentences")
    args = parser.parse_args()

    if not args.tagger.exists():
        print(f"missing: {args.tagger}", file=sys.stderr)
        return 1

    references = (DATA / f"{args.split}.txt").read_text(encoding="utf-8").splitlines()
    groups = (DATA / f"{args.split}.groups").read_text(encoding="utf-8").splitlines()
    if args.limit:
        references, groups = references[: args.limit], groups[: args.limit]
    typed = [strip_diacritics(sentence) for sentence in references]

    from schwa.tagger import TaggerRestorer

    lexicon = Lexicon.load(DATA / "lexicon.jsonl")
    tagger = TaggerRestorer.from_checkpoint(args.tagger)
    systems = [LexiconRestorer(lexicon), HybridRestorer(tagger, lexicon, None)]
    predictions = [run(system, typed) for system in systems]

    # The restorers keep the lexicon they were built with; only the scoring one changes.
    rows = []
    for share in args.shares:
        scoring = Lexicon.load(DATA / "lexicon.jsonl", min_minority_share=share)
        scores: list[Scores] = [
            evaluate(references, prediction, scoring, groups=groups) for prediction in predictions
        ]
        intervals, differences = bootstrap(scores, resamples=args.resamples, pairs=[(0, 1)])
        rows.append((share, scores, intervals, differences[0]))
        lexicon_rate, hybrid_rate = (score.ambiguous_accuracy for score in scores)
        print(
            f"{share:>5.0%}: {scores[0].ambiguous_words:>9,} ambiguous words, "
            f"lexicon {lexicon_rate:.2%}, hybrid {hybrid_rate:.2%}",
            flush=True,
        )

    words = rows[0][1][0].words
    lines = [
        f"The same predictions on the {args.split} split, {len(references):,} sentences, scored "
        f"against several definitions of an ambiguous word. A second spelling counts as a real "
        f"reading once it reaches this share of a typed form's occurrences and "
        f"{MIN_MINORITY_COUNT} occurrences in all; the repository uses "
        f"{MIN_MINORITY_SHARE:.0%}. In brackets: 95% interval from "
        f"{args.resamples:,} bootstrap resamples of whole articles or documents.",
        "",
        "| Minority share | Ambiguous words | Of all words | lexicon | hybrid | hybrid - lexicon |",
        "|---|---|---|---|---|---|",
    ]
    for share, scores, intervals, difference in rows:
        lexicon_rate, hybrid_rate = (score.ambiguous_accuracy for score in scores)
        bounds = [interval["ambiguous_accuracy"] for interval in intervals]
        gap = difference["ambiguous_accuracy"]
        lines.append(
            f"| {share:.0%}{' (shipped)' if share == MIN_MINORITY_SHARE else ''} "
            f"| {scores[0].ambiguous_words:,} | {scores[0].ambiguous_words / words:.1%} "
            f"| {lexicon_rate:.1%} ({bounds[0].low:.1%}–{bounds[0].high:.1%}) "
            f"| {hybrid_rate:.1%} ({bounds[1].low:.1%}–{bounds[1].high:.1%}) "
            f"| {(hybrid_rate - lexicon_rate) * 100:+.2f} "
            f"({gap.low * 100:+.2f} to {gap.high * 100:+.2f}) |"
        )

    write_section(f"ambiguity threshold ({args.split})", "\n".join(lines))
    print("results -> docs/results.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
