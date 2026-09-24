"""Turn an exported chat into sentences for the hand-annotated set.

Collecting 300 real messages by copying them one at a time is where this set kept stalling.
A chat export already has them: WhatsApp's "Export chat" (without media) writes a .txt, and
Telegram Desktop's "Export chat history" writes a result.json. This reads either, keeps only
the messages one person wrote, and samples them into data/real/raw.txt.

    uv run python scripts/import_chat.py data/exports/chat.txt            # who wrote how much
    uv run python scripts/import_chat.py data/exports/chat.txt --me Emil  # keep Emil's messages

Only what that person wrote is kept - never the other side of the conversation. A message is
dropped if it has a link, an email address or anything like a phone number in it, if it is a
media placeholder or a deleted message, if it was forwarded, or if it is too short to be a
sentence. Names cannot be found automatically: read the file before annotating it, and take
out anything you would not want public.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter
from collections.abc import Iterable, Iterator
from pathlib import Path

from schwa.alphabet import is_foldable, strip_diacritics

DEFAULT_OUT = Path("data/real/raw.txt")

# "24.09.2026, 14:05 - " (Android) or "[24.09.2026, 14:05:33] " (iPhone), with the date in any
# order and separator, and the time in 24 or 12 hours. A line that starts this way starts a
# new entry; the ones without "Author: " after it are WhatsApp's own notices.
HEADER = re.compile(
    r"^\u200e?\[?\d{1,4}[./-]\d{1,2}[./-]\d{1,4},?\s"
    r"\d{1,2}:\d{2}(?::\d{2})?(?:[\s\u202f]?[APap]\.?[Mm]\.?)?"
    r"(?:\]\s|\s-\s)"
)
AUTHOR = re.compile(r"^(?P<author>[^:]+?):\s(?P<text>.*)$")
LINK = re.compile(r"https?://|www\.|\S+@\S+\.\w+", re.IGNORECASE)
DIGITS = re.compile(r"\d[\d\s()+-]{5,}\d")
# What WhatsApp writes, as the whole message, in place of what it did not export. Media on
# Android comes in angle brackets in the phone's own language ("<Media omitted>"); on an
# iPhone the line starts with a left-to-right mark, which is checked separately.
DELETED = {"this message was deleted", "you deleted this message", "null"}
EDITED = "<This message was edited>"
MIN_WORDS = 3
MAX_CHARACTERS = 250


def whatsapp_messages(lines: Iterable[str]) -> Iterator[tuple[str, str]]:
    """(author, text) for every message; a line with no header continues the one before."""
    author: str | None = None
    text = ""
    for raw in lines:
        line = raw.rstrip("\r\n")
        header = HEADER.match(line)
        if header:
            if author is not None:
                yield author, text
            message = AUTHOR.match(line[header.end() :])
            author, text = (message["author"].strip(), message["text"]) if message else (None, "")
        elif author is not None and line.strip():
            text = f"{text} {line}"
    if author is not None:
        yield author, text


def telegram_messages(export: dict) -> Iterator[tuple[str, str]]:
    """(author, text) for every message someone wrote, not forwarded, in a Telegram export."""
    for message in export.get("messages", []):
        if message.get("type") != "message" or "forwarded_from" in message:
            continue
        parts = message.get("text", "")
        if isinstance(parts, list):
            parts = "".join(
                part if isinstance(part, str) else part.get("text", "") for part in parts
            )
        yield str(message.get("from") or ""), parts


def usable(text: str) -> str | None:
    """The message as one clean line, or None if it should not go into the set."""
    if text.startswith("\u200e"):  # an iPhone export's attachment or deleted message
        return None
    text = " ".join(text.replace("\u200e", " ").replace("\u200f", " ").split())
    text = text.removesuffix(EDITED).strip()
    lowered = text.lower()
    if (lowered.startswith("<") and lowered.endswith(">")) or lowered.endswith(" omitted"):
        return None
    if lowered in DELETED or "attached:" in lowered:
        return None
    if LINK.search(text) or DIGITS.search(text):
        return None
    if len(text.split()) < MIN_WORDS or len(text) > MAX_CHARACTERS:
        return None
    # A message with no letter that could carry a diacritic cannot be restored wrong or right.
    if not any(is_foldable(char) for char in strip_diacritics(text).lower()):
        return None
    return text


def read_export(path: Path) -> list[tuple[str, str]]:
    if path.suffix.lower() == ".json":
        return list(telegram_messages(json.loads(path.read_text(encoding="utf-8"))))
    return list(whatsapp_messages(path.read_text(encoding="utf-8-sig").splitlines()))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("exports", type=Path, nargs="+", help="WhatsApp .txt or Telegram .json")
    parser.add_argument("--me", help="the author whose messages to keep, as the export names them")
    parser.add_argument("--count", type=int, default=300)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--append", action="store_true", help="add to an existing file")
    args = parser.parse_args()

    messages = [message for path in args.exports for message in read_export(path)]
    if not messages:
        print("no messages found - is this a WhatsApp .txt or a Telegram result.json?")
        return 1

    authors = Counter(author for author, _ in messages)
    if not args.me:
        print("Messages by author - run again with --me and your name as it appears here:")
        for author, count in authors.most_common():
            print(f"  {count:>7,}  {author}")
        return 0
    if args.me not in authors:
        print(f"no messages by {args.me!r}; the authors are: {', '.join(authors)}")
        return 1

    existing = []
    if args.out.exists():
        if not args.append:
            print(f"{args.out} exists; pass --append to add to it", file=sys.stderr)
            return 1
        existing = args.out.read_text(encoding="utf-8").splitlines()

    mine = [text for author, text in messages if author == args.me]
    kept = list(dict.fromkeys(line for line in map(usable, mine) if line))
    fresh = [line for line in kept if line not in set(existing)]
    chosen = random.Random(args.seed).sample(fresh, min(args.count, len(fresh)))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join([*existing, *chosen]) + "\n", encoding="utf-8")
    print(
        f"{len(mine):,} messages by {args.me}, {len(kept):,} usable, "
        f"{len(chosen):,} written to {args.out}."
    )
    print("Read it before annotating: take out names and anything you would not want public.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
