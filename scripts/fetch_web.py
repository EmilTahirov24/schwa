"""Take a sample of Azerbaijani web text, to measure what Wikipedia cannot tell us.

Every number so far comes from Wikipedia, which is edited, formal and third person. CC-100
(Conneau et al., 2020; built with CCNet, Wenzek et al., 2020) is Azerbaijani text crawled
from the open web. Most of it is news, and news quotes people, in the first and second person
Wikipedia never uses. It is still written with its diacritics, so it can serve as a
reference.

The file is 1.3 GB compressed, so it is streamed and only the start is read. Three filters
decide what may serve as a reference, and each one's effect is counted and reported:

* the same prose filter as the Wikipedia corpus;
* a sentence of 25 letters or more must contain "ə". Much of the web is typed without
  diacritics, and some of CC-100's "Azerbaijani" is Turkish, which has no "ə" at all. Either
  would make a wrong reference. The cost is a bias: a genuine Azerbaijani sentence of that
  length lacks "ə" only a few percent of the time, and those are dropped;
* any sentence that also appears in the Wikipedia corpus is removed, so the model is never
  tested on something it was trained on.

Documents, not sentences, are split into train, dev and test, for the same reason as before.
Next to each split goes a `.groups` file naming the document of every sentence: the
confidence intervals in evaluate.py resample documents, not sentences. The text is not
redistributed; it stays in data/, which is not committed.

    uv run python scripts/fetch_web.py --megabytes 400
"""

from __future__ import annotations

import argparse
import codecs
import hashlib
import json
import lzma
import sys
import urllib.request
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_corpus import is_usable, normalize  # noqa: E402
from schwa.alphabet import az_lower  # noqa: E402
from schwa.segment import split_sentences  # noqa: E402

URL = "https://data.statmt.org/cc-100/az.txt.xz"
DATA = Path("data/processed")
MIN_LETTERS_FOR_SCHWA = 25


def documents(url: str, max_bytes: int) -> Iterator[list[str]]:
    """Stream CC-100, yielding documents (lists of lines) until `max_bytes` of text is read."""
    decompressor = lzma.LZMADecompressor()
    # A letter like "ə" is two bytes and may straddle two chunks; an incremental decoder
    # holds the first half back instead of dropping it.
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    buffer = ""
    document: list[str] = []
    read = 0

    with urllib.request.urlopen(url) as response:
        while read < max_bytes:
            chunk = response.read(1 << 20)
            if not chunk:
                break
            text = decoder.decode(decompressor.decompress(chunk))
            read += len(text.encode("utf-8"))
            buffer += text
            *lines, buffer = buffer.split("\n")
            for line in lines:
                if line.strip():
                    document.append(line.strip())
                elif document:
                    yield document
                    document = []
    if document:
        yield document


def fingerprint(sentence: str) -> bytes:
    return hashlib.blake2b(az_lower(sentence).encode("utf-8"), digest_size=8).digest()


def wikipedia_fingerprints() -> set[bytes]:
    seen: set[bytes] = set()
    for name in ("train", "dev", "test"):
        with (DATA / f"{name}.txt").open(encoding="utf-8") as source:
            seen.update(fingerprint(line.rstrip("\n")) for line in source)
    return seen


def split_name(document_index: int) -> str:
    bucket = hashlib.sha1(str(document_index).encode()).digest()[0] % 100
    if bucket < 10:
        return "dev"
    if bucket < 20:
        return "test"
    return "train"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--megabytes", type=int, default=400, help="text to read from the start")
    args = parser.parse_args()

    print("indexing the Wikipedia corpus to keep it out of the web sample", flush=True)
    wikipedia = wikipedia_fingerprints()

    splits = ("train", "dev", "test")
    files = {name: (DATA / f"web_{name}.txt").open("w", encoding="utf-8") for name in splits}
    groups = {name: (DATA / f"web_{name}.groups").open("w", encoding="utf-8") for name in splits}
    counts: Counter[str] = Counter()
    seen: set[bytes] = set()

    for index, document in enumerate(documents(URL, args.megabytes * 1_000_000)):
        counts["documents"] += 1
        target = split_name(index)
        for line in document:
            for raw in split_sentences(line):
                sentence = normalize(raw)
                counts["sentences_read"] += 1
                if not is_usable(sentence):
                    counts["dropped_prose_filter"] += 1
                    continue
                letters = sum(char.isalpha() for char in sentence)
                if letters >= MIN_LETTERS_FOR_SCHWA and "ə" not in az_lower(sentence):
                    counts["dropped_no_schwa"] += 1
                    continue
                mark = fingerprint(sentence)
                if mark in wikipedia:
                    counts["dropped_in_wikipedia"] += 1
                    continue
                if mark in seen:
                    counts["dropped_duplicate"] += 1
                    continue
                seen.add(mark)
                files[target].write(sentence + "\n")
                groups[target].write(f"{index}\n")
                counts[f"kept_{target}"] += 1
        if counts["documents"] % 20000 == 0:
            print(f"{counts['documents']:>8} documents, {len(seen)} sentences kept", flush=True)

    for handle in (*files.values(), *groups.values()):
        handle.close()

    stats = dict(counts)
    (DATA / "web_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
