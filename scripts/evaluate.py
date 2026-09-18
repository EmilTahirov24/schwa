"""Score every restorer on a split and write the results table.

Input is the split with its diacritics removed, the reference is the split itself. Every rate
comes with a 95% interval from a bootstrap over whole articles - whole documents, for the web
splits - and every system is compared with the one above it on the same resamples.

    uv run python scripts/evaluate.py --split test
    uv run --group train python scripts/evaluate.py --split web_test
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from results_page import write_numbers, write_section
from schwa.alphabet import strip_diacritics
from schwa.context import ContextModel
from schwa.lexicon import Lexicon
from schwa.metrics import RATES, Interval, Scores, bootstrap, evaluate
from schwa.restore import (
    ContextRestorer,
    HybridRestorer,
    IdentityRestorer,
    LexiconRestorer,
    Restorer,
)

DEFAULT_DATA = Path("data/processed")
SPLITS = ("dev", "test", "web_dev", "web_test")


def build_systems(
    lexicon: Lexicon,
    context_path: Path,
    margins: list[float],
    smoothings: list[float],
    tagger_path: Path | None = None,
    hybrid_counts: list[int] | None = None,
) -> list[Restorer]:
    systems: list[Restorer] = [IdentityRestorer(), LexiconRestorer(lexicon)]

    if context_path.exists():
        for smoothing in smoothings:
            model = ContextModel.load(context_path, smoothing=smoothing)
            for margin in margins:
                restorer = ContextRestorer(lexicon, model, margin)
                if len(smoothings) > 1:
                    restorer.name = f"{restorer.name}, smoothing {smoothing:g}"
                systems.append(restorer)

    if tagger_path is not None and tagger_path.exists():
        from schwa.tagger import TaggerRestorer

        tagger = TaggerRestorer.from_checkpoint(tagger_path)
        systems.append(tagger)

        # The context model is deliberately not wired into the hybrid: measured on dev it
        # drags ambiguous accuracy from 92.9% down to its own 85.9%, because the tagger is
        # the better judge of exactly the words the context model was built for.
        for min_count in hybrid_counts or []:
            hybrid = HybridRestorer(tagger, lexicon, None, min_count=min_count)
            if len(hybrid_counts) > 1:
                hybrid.name = f"hybrid (min count {min_count})"
            systems.append(hybrid)

    return systems


def run(system: Restorer, texts: list[str]) -> list[str]:
    """Restore every text, in batches where the system supports them."""
    batched = getattr(system, "restore_many", None)
    if batched is None:
        return [system.restore(text) for text in texts]
    return [
        restored
        for start in range(0, len(texts), 512)
        for restored in batched(texts[start : start + 512])
    ]


def with_interval(value: float, interval: Interval | None, digits: int = 1) -> str:
    text = f"{value:.{digits}%}"
    if interval is None:
        return text
    return f"{text} ({interval.low * 100:.{digits}f}–{interval.high * 100:.{digits}f})"


def points(interval: Interval, value: float) -> str:
    return f"{value * 100:+.2f} ({interval.low * 100:+.2f} to {interval.high * 100:+.2f})"


def as_markdown(
    split: str,
    rows: list[dict],
    scores: list[Scores],
    intervals: list[dict[str, Interval]],
    differences: list[dict[str, Interval]],
    groups: int,
    resamples: int,
) -> str:
    source = "Web text (CC-100)" if split.startswith("web") else "Wikipedia"
    unit = "documents" if split.startswith("web") else "articles"
    first = scores[0]
    lines = [
        f"{source}, {first.sentences:,} sentences from {groups:,} {unit} never seen in "
        f"training. {first.unseen_words / first.words:.1%} of the words never occur in the "
        f"training text; {first.ambiguous_words / first.words:.1%} are ambiguous.",
    ]
    if intervals:
        lines.append(
            f"In brackets: 95% interval from {resamples:,} bootstrap resamples of whole {unit}."
        )
    lines += [
        "",
        "| System | Ambiguous word accuracy | Word accuracy | CER | Sentence accuracy"
        " | ms / sentence |",
        "|---|---|---|---|---|---|",
    ]
    for index, (row, score) in enumerate(zip(rows, scores, strict=True)):
        bounds = intervals[index] if intervals else {}
        lines.append(
            f"| {row['system']} "
            f"| {with_interval(score.ambiguous_accuracy, bounds.get('ambiguous_accuracy'))} "
            f"| {score.word_accuracy:.1%} "
            f"| {score.character_error_rate:.2%} "
            f"| {with_interval(score.sentence_accuracy, bounds.get('sentence_accuracy'))} "
            f"| {row['ms_per_sentence']:.2f} |"
        )

    if differences:
        lines += [
            "",
            "Each system against the one above it, in points, on the same resamples. An "
            "interval that excludes zero is a difference this data can tell apart.",
            "",
            "| Comparison | Ambiguous word accuracy | Sentence accuracy |",
            "|---|---|---|",
        ]
        for index, difference in enumerate(differences, start=1):
            after, before = scores[index], scores[index - 1]
            lines.append(
                f"| {rows[index]['system']} vs {rows[index - 1]['system']} "
                f"| {points(difference['ambiguous_accuracy'], after.ambiguous_accuracy - before.ambiguous_accuracy)} "  # noqa: E501
                f"| {points(difference['sentence_accuracy'], after.sentence_accuracy - before.sentence_accuracy)} |"  # noqa: E501
            )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", default="dev", choices=SPLITS)
    parser.add_argument("--tagger", type=Path, default=Path("models/tagger.pt"))
    parser.add_argument(
        "--hybrid-counts",
        type=int,
        nargs="*",
        default=[3],
        help="how often a single spelling must be seen before it overrules the tagger",
    )
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--limit", type=int, default=0, help="score only the first N sentences")
    parser.add_argument(
        "--margins",
        type=float,
        nargs="*",
        default=[0.0],
        help="how much better the context has to score before it overrules the lexicon",
    )
    parser.add_argument(
        "--smoothings",
        type=float,
        nargs="*",
        default=[1.0],
        help="add-k smoothing values to compare",
    )
    parser.add_argument(
        "--resamples", type=int, default=1000, help="bootstrap resamples; 0 skips the intervals"
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="print the scores and write nothing, for comparing settings",
    )
    args = parser.parse_args()

    split_path = args.data / f"{args.split}.txt"
    lexicon_path = args.data / "lexicon.jsonl"
    for path in (split_path, lexicon_path):
        if not path.exists():
            print(f"missing: {path}", file=sys.stderr)
            return 1

    references = split_path.read_text(encoding="utf-8").splitlines()
    groups_path = split_path.with_suffix(".groups")
    if groups_path.exists():
        groups = groups_path.read_text(encoding="utf-8").splitlines()
    else:
        print(f"no {groups_path}: treating every sentence as independent", file=sys.stderr)
        groups = [str(index) for index in range(len(references))]
    if args.limit:
        references, groups = references[: args.limit], groups[: args.limit]
    typed = [strip_diacritics(sentence) for sentence in references]

    lexicon = Lexicon.load(lexicon_path)
    rows: list[dict] = []
    all_scores: list[Scores] = []

    context_path = args.data / "context.jsonl"
    for system in build_systems(
        lexicon,
        context_path,
        args.margins,
        args.smoothings,
        args.tagger,
        args.hybrid_counts,
    ):
        started = time.perf_counter()
        predictions = run(system, typed)
        elapsed = time.perf_counter() - started

        scores = evaluate(references, predictions, lexicon, groups=groups)
        row = {"system": system.name, **scores.as_dict()}
        row["ms_per_sentence"] = round(1000 * elapsed / max(len(references), 1), 3)
        row["top_errors"] = [
            {"key": key, "expected": expected, "produced": produced}
            for key, expected, produced in scores.errors[:20]
        ]
        rows.append(row)
        all_scores.append(scores)

        print(
            f"{system.name:>10}: ambiguous {scores.ambiguous_accuracy:.1%}, "
            f"words {scores.word_accuracy:.1%}, sentences {scores.sentence_accuracy:.1%}",
            flush=True,
        )

    if args.no_report:
        return 0

    intervals: list[dict[str, Interval]] = []
    differences: list[dict[str, Interval]] = []
    if args.resamples:
        intervals, differences = bootstrap(all_scores, resamples=args.resamples)
        for row, bounds in zip(rows, intervals, strict=True):
            row["intervals"] = {name: [b.low, b.high] for name, b in bounds.items()}
        for row, bounds in zip(rows[1:], differences, strict=True):
            row["difference_from_previous"] = {name: [b.low, b.high] for name, b in bounds.items()}

    group_count = len(all_scores[0].by_group)
    results_path = args.data / f"eval_{args.split}.json"
    results_path.write_text(
        json.dumps(
            {
                "split": args.split,
                "sentences": len(references),
                "groups": group_count,
                "resamples": args.resamples,
                "systems": rows,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    write_section(
        args.split,
        as_markdown(
            args.split, rows, all_scores, intervals, differences, group_count, args.resamples
        ),
    )
    systems = {}
    for index, (row, score) in enumerate(zip(rows, all_scores, strict=True)):
        systems[row["system"]] = {rate: getattr(score, rate) for rate in RATES}
        if intervals:
            systems[row["system"]]["intervals"] = {
                rate: [bound.low, bound.high] for rate, bound in intervals[index].items()
            }
    write_numbers(
        args.split,
        {
            "sentences": len(references),
            "groups": group_count,
            "unseen_words": all_scores[0].unseen_words / all_scores[0].words,
            "ambiguous_words": all_scores[0].ambiguous_words / all_scores[0].words,
            "systems": systems,
        },
    )
    print(f"results -> {results_path}, docs/results.md and docs/results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
