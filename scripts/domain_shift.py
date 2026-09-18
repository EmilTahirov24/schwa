"""How much does it matter what the tagger read? Score taggers trained on different text on
both test splits, Wikipedia and the web.

Every tagger has the same architecture, settings and seed; only what it read differs - which
text, or the same text with some of it in capitals. The comparison is the tagger alone,
without the lexicon, so that nothing else in the table depends on Wikipedia. Intervals come
from the same article- and document-level bootstrap as the main results, and each model is
compared with the first on the same resamples.

    uv run --group train python scripts/domain_shift.py \\
        --models wikipedia=models/tagger.pt web=models/tagger_web.pt both=models/tagger_both.pt
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from evaluate import run
from results_page import write_section
from schwa.alphabet import is_foldable, strip_diacritics
from schwa.lexicon import Lexicon
from schwa.metrics import Interval, Scores, bootstrap, evaluate
from schwa.tokenize import iter_words, key_of

DATA = Path("data/processed")
SPLITS = {"test": "Wikipedia test", "web_test": "Web test"}


def capitals(references: list[str], predictions: list[str]) -> tuple[int, int]:
    """Words written entirely in capitals that could be wrong: how many, how many right.

    The same words scripts/error_analysis.py counts as "all capitals".
    """
    total = right = 0
    for reference, prediction in zip(references, predictions, strict=True):
        for start, end in iter_words(reference):
            word = reference[start:end]
            letters = [char for char in word if char.isalpha()]
            if len(letters) < 2 or not all(char.isupper() for char in letters):
                continue
            if not any(is_foldable(char) for char in key_of(word)):
                continue
            total += 1
            right += word == prediction[start:end]
    return total, right


def cell(value: float, interval: Interval) -> str:
    return f"{value:.1%} ({interval.low * 100:.1f}–{interval.high * 100:.1f})"


def difference(value: float, interval: Interval) -> str:
    return f"{value * 100:+.2f} ({interval.low * 100:+.2f} to {interval.high * 100:+.2f})"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--models",
        nargs="+",
        required=True,
        help="name=checkpoint pairs; the first is the baseline the others are compared with",
    )
    parser.add_argument("--resamples", type=int, default=1000)
    parser.add_argument("--limit", type=int, default=0, help="score only the first N sentences")
    args = parser.parse_args()

    models = dict(item.split("=", 1) for item in args.models)
    for path in models.values():
        if not Path(path).exists():
            print(f"missing: {path}", file=sys.stderr)
            return 1

    from schwa.tagger import TaggerRestorer

    lexicon = Lexicon.load(DATA / "lexicon.jsonl")
    taggers = {name: TaggerRestorer.from_checkpoint(Path(path)) for name, path in models.items()}
    names = list(taggers)

    results: dict[str, dict] = {}
    for split in SPLITS:
        references = (DATA / f"{split}.txt").read_text(encoding="utf-8").splitlines()
        groups = (DATA / f"{split}.groups").read_text(encoding="utf-8").splitlines()
        if args.limit:
            references, groups = references[: args.limit], groups[: args.limit]
        typed = [strip_diacritics(sentence) for sentence in references]

        scores: list[Scores] = []
        shouted: list[tuple[int, int]] = []
        for name, tagger in taggers.items():
            predictions = run(tagger, typed)
            scores.append(evaluate(references, predictions, lexicon, groups=groups))
            shouted.append(capitals(references, predictions))
            print(
                f"{split:>9} {name:>10}: ambiguous {scores[-1].ambiguous_accuracy:.2%}, "
                f"sentences {scores[-1].sentence_accuracy:.2%}, "
                f"capitals {shouted[-1][1] / max(shouted[-1][0], 1):.2%}",
                flush=True,
            )
        intervals, differences = bootstrap(
            scores,
            resamples=args.resamples,
            pairs=[(0, index) for index in range(1, len(scores))],
        )
        results[split] = {
            "sentences": len(references),
            "groups": len(scores[0].by_group),
            "scores": scores,
            "capitals": shouted,
            "intervals": intervals,
            "differences": differences,
        }

    header = "| Trained on | " + " | ".join(
        f"{SPLITS[split]}: {what}" for split in SPLITS for what in ("ambiguous", "sentences")
    )
    lines = [
        "The tagger alone, trained "
        + ", ".join(f"{name} (`{path}`)" for name, path in models.items())
        + ". Same architecture, settings and seed; only what it read differs. In brackets: "
        f"95% interval from {args.resamples:,} bootstrap resamples of whole articles or "
        "documents.",
        "",
        header + " |",
        "|---" * (1 + 2 * len(SPLITS)) + "|",
    ]
    for index, name in enumerate(names):
        cells = []
        for split in SPLITS:
            score = results[split]["scores"][index]
            bounds = results[split]["intervals"][index]
            cells += [
                cell(score.ambiguous_accuracy, bounds["ambiguous_accuracy"]),
                cell(score.sentence_accuracy, bounds["sentence_accuracy"]),
            ]
        lines.append(f"| {name} | " + " | ".join(cells) + " |")

    lines += ["", f"Against the model trained on {names[0]}, in points:", "", header + " |"]
    lines.append("|---" * (1 + 2 * len(SPLITS)) + "|")
    for index, name in enumerate(names[1:], start=1):
        cells = []
        for split in SPLITS:
            base = results[split]["scores"][0]
            score = results[split]["scores"][index]
            bounds = results[split]["differences"][index - 1]
            cells += [
                difference(
                    score.ambiguous_accuracy - base.ambiguous_accuracy,
                    bounds["ambiguous_accuracy"],
                ),
                difference(
                    score.sentence_accuracy - base.sentence_accuracy, bounds["sentence_accuracy"]
                ),
            ]
        lines.append(f"| {name} | " + " | ".join(cells) + " |")

    lines += [
        "",
        "Words written entirely in capitals, restored right:",
        "",
        "| Trained on | " + " | ".join(SPLITS.values()) + " |",
        "|---" * (1 + len(SPLITS)) + "|",
    ]
    for index, name in enumerate(names):
        cells = []
        for split in SPLITS:
            total, right = results[split]["capitals"][index]
            cells.append(f"{right / max(total, 1):.1%} of {total:,}")
        lines.append(f"| {name} | " + " | ".join(cells) + " |")

    write_section("domain shift", "\n".join(lines))

    summary = {
        split: {
            "sentences": result["sentences"],
            "groups": result["groups"],
            "models": {
                name: {
                    **result["scores"][index].as_dict(),
                    "capitals": dict(
                        zip(("words", "right"), result["capitals"][index], strict=True)
                    ),
                    "intervals": {
                        rate: [bound.low, bound.high]
                        for rate, bound in result["intervals"][index].items()
                    },
                }
                for index, name in enumerate(names)
            },
        }
        for split, result in results.items()
    }
    (DATA / "domain_shift.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("results -> data/processed/domain_shift.json and docs/results.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
