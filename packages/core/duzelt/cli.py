"""Command line entry point.

    duzelt --lexicon data/processed/lexicon.jsonl "sence neden basliyaq"
    cat notes.txt | duzelt --lexicon data/processed/lexicon.jsonl

The lexicon has to be pointed at for now, either with ``--lexicon`` or through the
``DUZELT_LEXICON`` environment variable. Once the trained model ships with the package,
it becomes the default and the flag turns optional.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from duzelt.lexicon import Lexicon
from duzelt.restore import LexiconRestorer

ENV_LEXICON = "DUZELT_LEXICON"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="duzelt",
        description="Restore Azerbaijani diacritics in text typed without them.",
    )
    parser.add_argument("text", nargs="*", help="text to fix; read from stdin when omitted")
    parser.add_argument(
        "--lexicon",
        type=Path,
        default=os.environ.get(ENV_LEXICON),
        help=f"path to a lexicon file (default: ${ENV_LEXICON})",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.lexicon is None:
        print(
            f"no lexicon given; pass --lexicon or set {ENV_LEXICON}",
            file=sys.stderr,
        )
        return 2

    lexicon_path = Path(args.lexicon)
    if not lexicon_path.exists():
        print(f"lexicon not found: {lexicon_path}", file=sys.stderr)
        return 1

    text = " ".join(args.text) if args.text else sys.stdin.read()
    if not text.strip():
        return 0

    restorer = LexiconRestorer(Lexicon.load(lexicon_path))
    sys.stdout.write(restorer.restore(text))
    if args.text:
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
