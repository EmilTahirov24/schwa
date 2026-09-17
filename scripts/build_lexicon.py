"""Build the word lexicon from the training split and report what is ambiguous.

The lexicon is what the first restorer uses and what decides which words count as
ambiguous when scoring, so it is built from training sentences only.

    uv run python scripts/build_lexicon.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from duzelt.lexicon import Lexicon
from duzelt.tokenize import key_of, words_of

DEFAULT_TRAIN = Path("data/processed/train.txt")
DEFAULT_OUT = Path("data/processed/lexicon.jsonl")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, default=DEFAULT_TRAIN)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--min-count",
        type=int,
        default=2,
        help="drop spellings seen fewer times than this; they are mostly typos",
    )
    args = parser.parse_args()

    if not args.train.exists():
        print(f"training split not found: {args.train}", file=sys.stderr)
        return 1

    sentences = args.train.read_text(encoding="utf-8").splitlines()
    lexicon = Lexicon.from_sentences(sentences)
    before = len(lexicon)
    lexicon.prune(args.min_count)
    lexicon.save(args.out)

    # How much of running text is actually ambiguous - the share the models must fix.
    key_counts: Counter[str] = Counter()
    for sentence in sentences:
        key_counts.update(key_of(word) for word in words_of(sentence))

    ambiguous_keys = set(lexicon.ambiguous_keys)
    tokens = sum(key_counts.values())
    ambiguous_tokens = sum(count for key, count in key_counts.items() if key in ambiguous_keys)

    stats = {
        "sentences": len(sentences),
        "tokens": tokens,
        "keys_before_pruning": before,
        "keys": len(lexicon),
        "ambiguous_keys": len(ambiguous_keys),
        "ambiguous_token_share": round(ambiguous_tokens / tokens, 4) if tokens else 0.0,
        "most_frequent_ambiguous": [
            {
                "key": key,
                "count": count,
                "forms": dict(lexicon.candidates(key)),
            }
            for key, count in key_counts.most_common()
            if key in ambiguous_keys
        ][:25],
    }

    stats_path = args.out.with_name("lexicon_stats.json")
    stats_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"lexicon: {len(lexicon)} keys ({len(ambiguous_keys)} ambiguous) -> {args.out}")
    print(f"ambiguous share of running text: {stats['ambiguous_token_share']:.2%}")
    print(f"stats -> {stats_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
