"""Annotate real, informal sentences to build the evaluation set people actually write.

Wikipedia is formal prose; chat messages are not. This set is the only way to see how far
that gap goes, so it is annotated by hand and never used for training.

Put the sentences as they were typed - one per line - into data/real/raw.txt, then:

    uv run python scripts/annotate.py --annotator emil

For each sentence the current restorer's guess is shown. Press Enter to accept it, type the
correct sentence to replace it, "s" to skip, or "q" to stop. Progress is saved after every
line, so the file can be worked through in several sittings.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from duzelt.alphabet import strip_diacritics
from duzelt.lexicon import Lexicon
from duzelt.restore import IdentityRestorer, LexiconRestorer, Restorer

DEFAULT_RAW = Path("data/real/raw.txt")
DEFAULT_OUT = Path("data/real/annotated.jsonl")
DEFAULT_LEXICON = Path("data/processed/lexicon.jsonl")


def load_done(path: Path) -> set[str]:
    """Return the typed sentences that are already annotated."""
    if not path.exists():
        return set()
    with path.open(encoding="utf-8") as source:
        return {json.loads(line)["typed"] for line in source if line.strip()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--lexicon", type=Path, default=DEFAULT_LEXICON)
    parser.add_argument("--annotator", required=True, help="who is annotating")
    args = parser.parse_args()

    if not args.raw.exists():
        print(f"no sentences to annotate: {args.raw}", file=sys.stderr)
        return 1

    if args.lexicon.exists():
        restorer: Restorer = LexiconRestorer(Lexicon.load(args.lexicon))
    else:
        restorer = IdentityRestorer()

    done = load_done(args.out)
    args.out.parent.mkdir(parents=True, exist_ok=True)

    lines = [line.strip() for line in args.raw.read_text(encoding="utf-8").splitlines()]
    pending = [line for line in lines if line and line not in done]
    print(f"{len(done)} annotated, {len(pending)} to go\n")

    with args.out.open("a", encoding="utf-8") as out:
        for index, typed in enumerate(pending, start=1):
            suggestion = restorer.restore(typed)
            print(f"[{index}/{len(pending)}] typed:      {typed}")
            print(f"              suggestion: {suggestion}")
            answer = input("              correct:    ").strip()

            if answer.lower() == "q":
                break
            if answer.lower() == "s":
                print()
                continue

            correct = answer or suggestion
            if strip_diacritics(correct) != strip_diacritics(typed):
                print("              ! that changes more than diacritics, skipped\n")
                continue

            out.write(
                json.dumps(
                    {"typed": typed, "correct": correct, "annotator": args.annotator},
                    ensure_ascii=False,
                )
                + "\n"
            )
            out.flush()
            print()

    total = len(load_done(args.out))
    print(f"{total} sentences annotated -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
