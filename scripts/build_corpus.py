"""Turn extracted articles into clean sentence files split into train, dev and test.

The split is decided per article, never per sentence: two sentences from the same article
can be near-copies of each other, and letting them fall on both sides of the split would
quietly inflate every score. For the same reason each split gets a `.groups` file naming the
article of every sentence, and the confidence intervals resample articles, not sentences.

    uv run python scripts/build_corpus.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path

from schwa.alphabet import az_lower, is_foldable
from schwa.segment import split_sentences

DEFAULT_IN = Path("data/processed/articles.jsonl")
DEFAULT_OUT_DIR = Path("data/processed")

AZ_LETTERS = set("abcçdeəfgğhxıijkqlmnoöprsştuüvyzABCÇDEƏFGĞHXIİJKQLMNOÖPRSŞTUÜVYZ")
ASCII_LETTERS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
ALLOWED_LETTERS = AZ_LETTERS | ASCII_LETTERS
MARKUP_CHARS = set("|={}[]<>")

MIN_CHARS = 20
MAX_CHARS = 300
MIN_WORDS = 4
MIN_LETTER_RATIO = 0.6

DEV_BUCKETS = range(0, 5)  # 5% of articles
TEST_BUCKETS = range(5, 10)  # 5% of articles


def bucket_of(article_id: str) -> int:
    """Stable 0-99 bucket for an article, so reruns keep the same split."""
    digest = hashlib.sha1(article_id.encode("utf-8")).digest()
    return digest[0] % 100


def split_name(article_id: str) -> str:
    bucket = bucket_of(article_id)
    if bucket in DEV_BUCKETS:
        return "dev"
    if bucket in TEST_BUCKETS:
        return "test"
    return "train"


def is_usable(sentence: str) -> bool:
    """Keep prose that a person could have written, drop leftovers of the markup."""
    if not (MIN_CHARS <= len(sentence) <= MAX_CHARS):
        return False
    if len(sentence.split()) < MIN_WORDS:
        return False
    if MARKUP_CHARS & set(sentence):
        return False
    if not sentence[0].isalpha():
        return False

    letters = [char for char in sentence if char.isalpha()]
    if not letters or len(letters) / len(sentence) < MIN_LETTER_RATIO:
        return False
    # Any letter outside the Azerbaijani alphabet means another script or language.
    return all(char in ALLOWED_LETTERS for char in letters)


def normalize(sentence: str) -> str:
    """NFC form with collapsed whitespace, the form written to the corpus files."""
    return unicodedata.normalize("NFC", " ".join(sentence.split()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--articles", type=Path, default=DEFAULT_IN)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    if not args.articles.exists():
        print(f"articles not found: {args.articles}", file=sys.stderr)
        return 1

    args.out_dir.mkdir(parents=True, exist_ok=True)
    splits = ("train", "dev", "test")
    files = {name: (args.out_dir / f"{name}.txt").open("w", encoding="utf-8") for name in splits}
    groups = {
        name: (args.out_dir / f"{name}.groups").open("w", encoding="utf-8") for name in splits
    }

    seen: set[str] = set()
    kept = Counter()
    articles = 0
    dropped_filter = 0
    dropped_duplicate = 0
    with_foldable = 0

    with args.articles.open(encoding="utf-8") as source:
        for line in source:
            article = json.loads(line)
            articles += 1
            target = split_name(article["id"])

            for raw in split_sentences(article["text"]):
                sentence = normalize(raw)
                if not is_usable(sentence):
                    dropped_filter += 1
                    continue

                fingerprint = az_lower(sentence)
                if fingerprint in seen:
                    dropped_duplicate += 1
                    continue
                seen.add(fingerprint)

                files[target].write(sentence + "\n")
                groups[target].write(f"{article['id']}\n")
                kept[target] += 1
                if any(is_foldable(char) for char in sentence):
                    with_foldable += 1

            if articles % 20000 == 0:
                print(
                    f"{articles:>7} articles -> {sum(kept.values())} sentences",
                    file=sys.stderr,
                    flush=True,
                )

    for handle in (*files.values(), *groups.values()):
        handle.close()

    total = sum(kept.values())
    stats = {
        "articles": articles,
        "sentences": dict(kept),
        "sentences_total": total,
        "dropped_by_filter": dropped_filter,
        "dropped_as_duplicate": dropped_duplicate,
        "sentences_with_foldable_characters": with_foldable,
    }
    (args.out_dir / "corpus_stats.json").write_text(
        json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(json.dumps(stats, indent=2, ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
