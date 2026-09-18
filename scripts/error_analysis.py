"""Where the shipped model's remaining errors are, by kind of word.

Only words that could be wrong are counted: those with at least one letter that could carry
a diacritic. Each is sorted by its capitalisation and position, since a capital in the middle
of a sentence is the cheapest available sign of a name, and separately by what the training
text knew about it.

One kind of error is not the model's fault in the ordinary sense: the model wrote the
spelling the training text uses almost every time, and the reference says otherwise. That is
either a rare reading the model could not know about, or a typo in the reference; this script
counts them without deciding which.

    uv run python scripts/error_analysis.py --split test
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from evaluate import run
from results_page import write_section
from schwa.alphabet import az_lower, is_foldable, strip_diacritics
from schwa.bundled import MODEL, default_restorer
from schwa.lexicon import Lexicon
from schwa.tokenize import iter_words, key_of

DATA = Path("data/processed")
CASES = ("capitalised, mid-sentence", "capitalised, first word", "all capitals", "lowercase")
# How dominant a spelling must be in training for an error against it to count as "the model
# wrote what the training text writes".
DOMINANT = 0.95


def case_of(word: str, first: bool) -> str:
    letters = [char for char in word if char.isalpha()]
    if len(letters) > 1 and all(char.isupper() for char in letters):
        return "all capitals"
    if word[:1].isupper():
        return "capitalised, first word" if first else "capitalised, mid-sentence"
    return "lowercase"


def dominant_form(lexicon: Lexicon, key: str) -> str | None:
    candidates = lexicon.candidates(key)
    total = sum(count for _, count in candidates)
    if not total:
        return None
    form, count = candidates[0]
    return form if count / total >= DOMINANT else None


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--split", default="test", choices=["dev", "test", "web_dev", "web_test"])
    parser.add_argument("--limit", type=int, default=0, help="only the first N sentences")
    args = parser.parse_args()

    path = DATA / f"{args.split}.txt"
    training_lexicon = DATA / "lexicon.jsonl"
    for needed in (path, training_lexicon):
        if not needed.exists():
            print(f"missing: {needed}", file=sys.stderr)
            return 1

    restorer = default_restorer()
    if restorer.name != "hybrid":
        print(f"the bundle gave {restorer.name!r}, not the hybrid", file=sys.stderr)
        return 1
    # The full training lexicon, not the shipped subset: this asks what training knew.
    lexicon = Lexicon.load(training_lexicon)

    references = path.read_text(encoding="utf-8").splitlines()
    if args.limit:
        references = references[: args.limit]
    print(f"restoring {len(references):,} sentences with {MODEL.name}", flush=True)
    predictions = run(restorer, [strip_diacritics(sentence) for sentence in references])

    words: Counter[str] = Counter()
    errors: Counter[str] = Counter()
    mistakes: Counter[tuple[str, str]] = Counter()
    for reference, prediction in zip(references, predictions, strict=True):
        for index, (start, end) in enumerate(iter_words(reference)):
            expected, produced = reference[start:end], prediction[start:end]
            key = key_of(expected)
            if not any(is_foldable(char) for char in key):
                continue

            kinds = [case_of(expected, index == 0)]
            if key not in lexicon:
                kinds.append("never seen in training")
            elif lexicon.is_ambiguous(key):
                kinds.append("ambiguous")
            words.update(kinds)
            if expected == produced:
                continue

            if dominant_form(lexicon, key) == az_lower(produced):
                kinds.append("wrote the spelling training uses 95% of the time")
            errors.update(kinds)
            errors["all"] += 1
            mistakes[az_lower(expected), az_lower(produced)] += 1

    total_words = sum(words[kind] for kind in CASES)
    total_errors = errors["all"]
    rows = [
        *CASES,
        "never seen in training",
        "ambiguous",
        "wrote the spelling training uses 95% of the time",
    ]
    lines = [
        f"The shipped model ({MODEL.name}, int8, with the lexicon) on {len(references):,} "
        f"sentences of the {args.split} split: {total_errors:,} wrong words out of "
        f"{total_words:,} that could be wrong. The first four rows split every word by case "
        "and position; the others overlap them.",
        "",
        "| Words | Share of words | Share of errors | Error rate |",
        "|---|---|---|---|",
    ]
    for kind in rows:
        share_of_words = words[kind] / total_words if kind in words else None
        rate = errors[kind] / words[kind] if words.get(kind) else None
        lines.append(
            f"| {kind} | {'—' if share_of_words is None else f'{share_of_words:.1%}'} "
            f"| {errors[kind] / total_errors:.1%} | {'—' if rate is None else f'{rate:.2%}'} |"
        )
    common = ", ".join(
        f"{expected} → {produced} ({count})"
        for (expected, produced), count in mistakes.most_common(12)
    )
    lines += ["", f"Most frequent: {common}."]
    write_section(f"errors ({args.split})", "\n".join(lines))

    summary = {
        "split": args.split,
        "sentences": len(references),
        "words": dict(words),
        "errors": dict(errors),
        "most_common": [
            {"expected": expected, "produced": produced, "count": count}
            for (expected, produced), count in mistakes.most_common(50)
        ],
    }
    out = DATA / f"errors_{args.split}.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
