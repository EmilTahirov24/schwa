"""Train the context model on the training split.

Two approximations keep the counts in memory, and both are on purpose:

* Neighbours outside the most frequent keys are folded into a single ``<unk>`` feature.
  Rare neighbours carry little evidence and would dominate the table size.
* Contexts seen only once are dropped periodically rather than at the end. That slightly
  undercounts a context that appears once in each of two windows, in exchange for a bound
  on memory.

    uv run python scripts/train_context.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from schwa.alphabet import az_lower
from schwa.context import END, START, ContextModel
from schwa.lexicon import Lexicon
from schwa.tokenize import key_of, words_of

DEFAULT_TRAIN = Path("data/processed/train.txt")
DEFAULT_LEXICON = Path("data/processed/lexicon.jsonl")
DEFAULT_OUT = Path("data/processed/context.jsonl")

UNKNOWN = "<unk>"
PRUNE_EVERY = 500_000


def neighbour_vocabulary(lexicon: Lexicon, size: int) -> set[str]:
    """The most frequent keys, which are the only neighbours kept as features."""
    return set(sorted(lexicon, key=lexicon.total, reverse=True)[:size])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, default=DEFAULT_TRAIN)
    parser.add_argument("--lexicon", type=Path, default=DEFAULT_LEXICON)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--vocabulary", type=int, default=30_000, help="neighbour features")
    parser.add_argument("--max-contexts", type=int, default=200, help="kept per form and side")
    parser.add_argument("--smoothing", type=float, default=1.0, help="add-k smoothing")
    parser.add_argument("--limit", type=int, default=0, help="stop after N sentences")
    args = parser.parse_args()

    for path in (args.train, args.lexicon):
        if not path.exists():
            print(f"missing: {path}", file=sys.stderr)
            return 1

    lexicon = Lexicon.load(args.lexicon)
    ambiguous = set(lexicon.ambiguous_keys)
    vocabulary = neighbour_vocabulary(lexicon, args.vocabulary)
    print(f"{len(ambiguous)} ambiguous keys, {len(vocabulary)} neighbour features")

    # The model carries the vocabulary, so it maps neighbours to features the same way
    # here and later when it restores text.
    model = ContextModel(vocabulary=vocabulary, smoothing=args.smoothing)
    seen = 0

    with args.train.open(encoding="utf-8") as source:
        for line in source:
            words = words_of(line)
            if not words:
                continue

            keys = [key_of(word) for word in words]

            for index, key in enumerate(keys):
                if key not in ambiguous:
                    continue
                left = keys[index - 1] if index else START
                right = keys[index + 1] if index + 1 < len(keys) else END
                model.observe(key, az_lower(words[index]), left, right)

            seen += 1
            if seen % PRUNE_EVERY == 0:
                model.prune(min_context_count=2, max_contexts=10 * args.max_contexts)
                print(f"{seen:>9} sentences", file=sys.stderr, flush=True)
            if args.limit and seen >= args.limit:
                break

    model.prune(min_context_count=2, max_contexts=args.max_contexts)
    model.save(args.out)
    print(f"context model for {len(model)} keys -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
