"""Stream a MediaWiki XML dump into one JSON object per article.

The dump is a single compressed XML file of several gigabytes once expanded, so it is
parsed incrementally and each finished page is dropped from memory. Only main-namespace
pages are kept, and redirects are skipped.

    uv run python scripts/extract_wiki.py --limit 100    # quick look
    uv run python scripts/extract_wiki.py                # the whole dump
"""

from __future__ import annotations

import argparse
import bz2
import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from xml.etree import ElementTree as ET

import mwparserfromhell

DEFAULT_DUMP = Path("data/raw/azwiki-latest-pages-articles.xml.bz2")
DEFAULT_OUT = Path("data/processed/articles.jsonl")

# Markup that strip_code() leaves behind or mangles.
_TABLE = re.compile(r"\{\|.*?\|\}", re.DOTALL)
_REF = re.compile(r"<ref[^>]*?/>|<ref[^>]*?>.*?</ref>", re.DOTALL | re.IGNORECASE)
_HTML_TAG = re.compile(r"<[^>]+>")
_LEFTOVER_MARKUP = re.compile(r"^[\s|!{}*#:;=-]+$", re.MULTILINE)
_BLANK_LINES = re.compile(r"\n{3,}")
_SPACES = re.compile(r"[ \t ]+")
# Image placement options that survive as "thumb|294x294px|" in front of a caption.
_CAPTION_OPTIONS = re.compile(
    r"^(?:\s*(?:thumb|thumbnail|mini|left|right|center|centre|none|upright|border|frameless"
    r"|frame|\d+\s*x?\s*\d*\s*px)\s*\|)+",
    re.IGNORECASE | re.MULTILINE,
)
_SPACE_BEFORE_PUNCTUATION = re.compile(r"\s+([,;.!?])")


def local_name(tag: str) -> str:
    """Return an XML tag without its namespace."""
    return tag.rsplit("}", 1)[-1]


def iter_pages(dump: Path) -> Iterator[tuple[str, str, str]]:
    """Yield (page_id, title, wikitext) for every main-namespace, non-redirect page."""
    with bz2.open(dump, "rb") as raw:
        for _event, element in ET.iterparse(raw, events=("end",)):
            if local_name(element.tag) != "page":
                continue

            fields = {local_name(child.tag): child for child in element}
            namespace = fields.get("ns")
            is_article = namespace is not None and namespace.text == "0"
            is_redirect = "redirect" in fields

            if is_article and not is_redirect:
                revision = fields.get("revision")
                text_node = revision.find("{*}text") if revision is not None else None
                page_id = fields["id"].text or ""
                title = fields["title"].text or ""
                if text_node is not None and text_node.text:
                    yield page_id, title, text_node.text

            element.clear()


def clean(wikitext: str) -> str:
    """Turn wikitext into plain prose."""
    text = _REF.sub(" ", wikitext)
    text = _TABLE.sub(" ", text)
    text = mwparserfromhell.parse(text).strip_code(normalize=True, collapse=True)
    text = _HTML_TAG.sub(" ", text)
    text = _CAPTION_OPTIONS.sub("", text)
    text = _LEFTOVER_MARKUP.sub("", text)
    text = _SPACES.sub(" ", text)
    text = _SPACE_BEFORE_PUNCTUATION.sub(r"\1", text)
    text = _BLANK_LINES.sub("\n\n", text)
    return text.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dump", type=Path, default=DEFAULT_DUMP)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--limit", type=int, default=0, help="stop after N articles")
    parser.add_argument("--min-chars", type=int, default=200, help="skip stubs")
    args = parser.parse_args()

    if not args.dump.exists():
        print(f"dump not found: {args.dump}", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    kept = skipped = 0

    with args.out.open("w", encoding="utf-8") as out:
        for page_id, title, wikitext in iter_pages(args.dump):
            text = clean(wikitext)
            if len(text) < args.min_chars:
                skipped += 1
                continue

            out.write(
                json.dumps({"id": page_id, "title": title, "text": text}, ensure_ascii=False) + "\n"
            )
            kept += 1

            if kept % 5000 == 0:
                print(f"{kept:>7} articles kept, {skipped} skipped", file=sys.stderr, flush=True)
            if args.limit and kept >= args.limit:
                break

    print(f"done: {kept} articles kept, {skipped} too short -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
