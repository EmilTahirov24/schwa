"""Measure the spell checker on typos it has never seen, and on text with no typos at all.

There is no corpus of real Azerbaijani typing mistakes, so the typos here are made: a real
word from the split, one or two random edits - a letter dropped, added, replaced or swapped
with its neighbour. That tells us how well the checker undoes mechanical slips. It says
nothing about colloquial spellings like "nembilim" for "nə bilim"; those need the
hand-annotated set of real messages.

The second number matters as much as the first. A checker that flags correct words is worse
than none, so every setting is also run over clean text to count how often it cries wolf.

    uv run python scripts/evaluate_spelling.py --split dev
"""

from __future__ import annotations

import argparse
import itertools
import json
import random
import sys
import time
from pathlib import Path

from results_page import write_section
from schwa.lexicon import Lexicon
from schwa.spelling import LETTERS, Speller
from schwa.tokenize import key_of, words_of

DATA = Path("data/processed")


def typo(key: str, rng: random.Random) -> str:
    """One random mechanical mistake."""
    position = rng.randrange(len(key))
    kind = rng.choice(("delete", "insert", "substitute", "transpose"))
    if kind == "delete":
        return key[:position] + key[position + 1 :]
    if kind == "insert":
        return key[:position] + rng.choice(LETTERS) + key[position:]
    if kind == "substitute":
        options = [letter for letter in LETTERS if letter != key[position]]
        return key[:position] + rng.choice(options) + key[position + 1 :]
    if position == len(key) - 1:
        position -= 1
    return key[:position] + key[position + 1] + key[position] + key[position + 2 :]


def make_typos(words: list[str], speller: Speller, edits: int, size: int, seed: int):
    """(original, typed) pairs where the typed form is not itself a known word."""
    rng = random.Random(seed)
    pairs = []
    while len(pairs) < size:
        original = rng.choice(words)
        typed = original
        for _ in range(edits):
            typed = typo(typed, rng)
        if typed != original and len(typed) >= 2 and not speller.known(typed):
            pairs.append((original, typed))
    return pairs


def score(speller: Speller, pairs: list[tuple[str, str]]) -> dict[str, float]:
    flagged = top1 = top3 = 0
    for original, typed in pairs:
        if not speller.is_suspicious(typed):
            continue
        flagged += 1
        best = [words for _, words in speller.candidates(typed)[:3]]
        top1 += bool(best) and best[0] == (original,)
        top3 += (original,) in best
    total = len(pairs)
    return {"flagged": flagged / total, "top1": top1 / total, "top3": top3 / total}


def false_alarms(speller: Speller, sentences: list[str]) -> tuple[float, int]:
    """Share of words in clean sentences that the reader would see underlined.

    Checked the way the page checks text - whole sentences, with case and position - since
    that is what decides whether a capitalised word is taken for a name.
    """
    words = sum(len(words_of(sentence)) for sentence in sentences)
    flagged = sum(len(speller.check(sentence)) for sentence in sentences)
    return flagged / words, words


def plain_false_alarms(speller: Speller, sentences: list[str]) -> float:
    """The same, for a bare word list: any word of three letters or more it has not seen
    `min_count` times is underlined. The baseline the checker's rules are measured against."""
    keys = [key_of(word) for sentence in sentences for word in words_of(sentence)]
    return sum(1 for key in keys if len(key) >= 3 and not speller.known(key)) / len(keys)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", default="dev", choices=["dev", "test"])
    parser.add_argument("--typos", type=int, default=2000)
    parser.add_argument(
        "--clean", type=int, default=1000, help="clean sentences to check for false alarms"
    )
    parser.add_argument("--min-counts", type=int, nargs="*", default=[5])
    parser.add_argument("--edit-probabilities", type=float, nargs="*", default=[0.05])
    parser.add_argument("--dominances", type=float, nargs="*", default=[100.0])
    parser.add_argument("--rare-ceilings", type=int, nargs="*", default=[20])
    parser.add_argument("--suffix-stems", type=int, nargs="*", default=[1000])
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    lexicon_path = DATA / "lexicon.jsonl"
    split_path = DATA / f"{args.split}.txt"
    for path in (lexicon_path, split_path):
        if not path.exists():
            print(f"missing: {path}", file=sys.stderr)
            return 1

    lexicon = Lexicon.load(lexicon_path)
    base = Speller.from_lexicon(lexicon)

    sentences = split_path.read_text(encoding="utf-8").splitlines()
    rng = random.Random(args.seed)
    rng.shuffle(sentences)
    tokens = [key_of(word) for sentence in sentences[:20000] for word in words_of(sentence)]

    # Typos are made from words that are unambiguously real: long enough, and common.
    real = [key for key in tokens if len(key) >= 3 and base.count(key) >= 20]
    clean = sentences[20000 : 20000 + args.clean]

    rows = []
    suffixes: dict[tuple[int, int], set[str]] = {}
    for min_count, probability, dominance, ceiling, stems in itertools.product(
        args.min_counts,
        args.edit_probabilities,
        args.dominances,
        args.rare_ceilings,
        args.suffix_stems,
    ):
        if (min_count, stems) not in suffixes:
            suffixes[min_count, stems] = Speller.find_suffixes(base.words, min_count, stems)
        speller = Speller(
            base.words,
            suffixes[min_count, stems],
            min_count=min_count,
            rare_ceiling=ceiling,
            dominance=dominance,
            edit_probability=probability,
        )
        started = time.perf_counter()
        one = score(speller, make_typos(real, speller, 1, args.typos, args.seed))
        two = score(speller, make_typos(real, speller, 2, args.typos // 4, args.seed + 1))
        alarms, checked = false_alarms(speller, clean)
        elapsed = time.perf_counter() - started

        row = {
            "min_count": min_count,
            "edit_probability": probability,
            "dominance": dominance,
            "rare_ceiling": ceiling,
            "suffix_stems": stems,
            "suffixes": len(suffixes[min_count, stems]),
            "clean_words": checked,
            "plain_word_list_false_alarms": plain_false_alarms(speller, clean),
            "vocabulary": sum(1 for _, count in base.words.values() if count >= min_count),
            "one_edit": one,
            "two_edits": two,
            "false_alarms": alarms,
            "seconds": round(elapsed, 1),
        }
        rows.append(row)
        print(
            f"min {min_count:>3} p {probability:<6} ceil {ceiling:<3} stems {stems:<4} "
            f"flagged {one['flagged']:.1%}  1 edit: top1 {one['top1']:.1%} top3 {one['top3']:.1%}  "
            f"2 edits: top1 {two['top1']:.1%}  false alarms {alarms:.2%}  ({elapsed:.0f}s)",
            flush=True,
        )

    (DATA / f"spelling_{args.split}.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")

    if len(rows) == 1:
        write_results(args.split, rows[0], args)
    return 0


def write_results(split: str, row: dict, args: argparse.Namespace) -> None:
    section = (
        f"Synthetic typos in real words from the {split} split; {args.typos} with one edit, "
        f"{args.typos // 4} with two. Vocabulary: {row['vocabulary']:,} keys seen at least "
        f"{row['min_count']} times.\n\n"
        "| | Top-1 correct | Top-3 correct |\n|---|---|---|\n"
        f"| One edit | {row['one_edit']['top1']:.1%} | {row['one_edit']['top3']:.1%} |\n"
        f"| Two edits | {row['two_edits']['top1']:.1%} | {row['two_edits']['top3']:.1%} |\n\n"
        f"False alarms on clean text: {row['false_alarms']:.2%} of the "
        f"{row['clean_words']:,} words in {args.clean:,} sentences. A plain word list, "
        f"underlining every word of three letters or more seen fewer than {row['min_count']} "
        f"times, would flag {row['plain_word_list_false_alarms']:.2%} of the same words.\n"
    )
    write_section(f"spelling ({split})", section)


if __name__ == "__main__":
    raise SystemExit(main())
