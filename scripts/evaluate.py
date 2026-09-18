"""Score every restorer on a split and write the results table.

Input is the split with its diacritics removed, the reference is the split itself.

    uv run python scripts/evaluate.py --split dev
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from schwa.alphabet import strip_diacritics
from schwa.context import ContextModel
from schwa.lexicon import Lexicon
from schwa.metrics import evaluate
from schwa.restore import (
    ContextRestorer,
    HybridRestorer,
    IdentityRestorer,
    LexiconRestorer,
    Restorer,
)

DEFAULT_DATA = Path("data/processed")
RESULTS_MD = Path("docs/results.md")


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


def as_markdown(split: str, rows: list[dict]) -> str:
    header = (
        "| System | Ambiguous word accuracy | Word accuracy | CER | Sentence accuracy |"
        " ms / sentence |\n|---|---|---|---|---|---|\n"
    )
    body = "".join(
        "| {system} | {ambiguous_accuracy:.1%} | {word_accuracy:.1%} | {character_error_rate:.2%}"
        " | {sentence_accuracy:.1%} | {ms_per_sentence:.2f} |\n".format(**row)
        for row in rows
    )
    return f"### {split}\n\n{header}{body}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", default="dev", choices=["dev", "test"])
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
        default=[0.5],
        help="add-k smoothing values to compare",
    )
    args = parser.parse_args()

    split_path = args.data / f"{args.split}.txt"
    lexicon_path = args.data / "lexicon.jsonl"
    for path in (split_path, lexicon_path):
        if not path.exists():
            print(f"missing: {path}", file=sys.stderr)
            return 1

    references = split_path.read_text(encoding="utf-8").splitlines()
    if args.limit:
        references = references[: args.limit]
    typed = [strip_diacritics(sentence) for sentence in references]

    lexicon = Lexicon.load(lexicon_path)
    rows = []

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

        scores = evaluate(references, predictions, lexicon)
        row = {"system": system.name, **scores.as_dict()}
        row["ms_per_sentence"] = round(1000 * elapsed / max(len(references), 1), 3)
        row["top_errors"] = [
            {"key": key, "expected": expected, "produced": produced}
            for key, expected, produced in scores.errors[:20]
        ]
        rows.append(row)

        print(
            f"{system.name:>10}: ambiguous {scores.ambiguous_accuracy:.1%}, "
            f"words {scores.word_accuracy:.1%}, sentences {scores.sentence_accuracy:.1%}"
        )

    results_path = args.data / f"eval_{args.split}.json"
    results_path.write_text(
        json.dumps(
            {"split": args.split, "sentences": len(references), "systems": rows},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    RESULTS_MD.parent.mkdir(parents=True, exist_ok=True)
    intro = (
        "# Results\n\n"
        "Generated by `scripts/evaluate.py`. Ambiguous word accuracy is the headline "
        "number: it covers only the words whose typed form stands for more than one real "
        "word, which is the part a model can actually get wrong.\n\n"
    )
    previous = RESULTS_MD.read_text(encoding="utf-8") if RESULTS_MD.exists() else ""
    sections = {
        section.split("\n", 1)[0].strip(): f"### {section}"
        for section in previous.split("### ")[1:]
    }
    sections[args.split] = as_markdown(args.split, rows)
    RESULTS_MD.write_text(
        intro + "\n".join(sections[name] for name in sorted(sections)), encoding="utf-8"
    )

    print(f"results -> {results_path} and {RESULTS_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
