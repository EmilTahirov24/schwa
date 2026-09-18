"""Command line entry point.

    schwa "sence neden basliyaq"
    cat notes.txt | schwa

The model that ships with the package is used unless ``--lexicon`` points somewhere else,
which is how a freshly trained model gets tried out before it is bundled.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from schwa.bundled import MissingBundle, default_restorer
from schwa.lexicon import Lexicon
from schwa.restore import LexiconRestorer, Restorer

ENV_LEXICON = "SCHWA_LEXICON"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="schwa",
        description="Restore Azerbaijani diacritics in text typed without them.",
    )
    parser.add_argument("text", nargs="*", help="text to fix; read from stdin when omitted")
    parser.add_argument(
        "--lexicon",
        type=Path,
        default=os.environ.get(ENV_LEXICON),
        help=f"use this lexicon instead of the bundled model (default: ${ENV_LEXICON})",
    )
    parser.add_argument(
        "--which",
        action="store_true",
        help="print which restorer would be used, and exit",
    )
    return parser


def pick_restorer(lexicon_path: Path | None) -> Restorer:
    """The restorer the arguments ask for."""
    if lexicon_path is None:
        return default_restorer()

    path = Path(lexicon_path)
    if not path.exists():
        raise FileNotFoundError(path)
    return LexiconRestorer(Lexicon.load(path))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        restorer = pick_restorer(args.lexicon)
    except FileNotFoundError as missing:
        print(f"lexicon not found: {missing}", file=sys.stderr)
        return 1
    except MissingBundle:
        print(
            f"this installation has no bundled model; pass --lexicon or set {ENV_LEXICON}",
            file=sys.stderr,
        )
        return 2

    if args.which:
        print(restorer.name)
        return 0

    text = " ".join(args.text) if args.text else sys.stdin.read()
    if not text.strip():
        return 0

    sys.stdout.write(restorer.restore(text))
    if args.text:
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
