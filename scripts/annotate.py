"""Annotate real, informal sentences to build the evaluation set people actually write.

Wikipedia is formal prose; chat messages are not. This set is the only way to see how far
that gap goes, so it is annotated by hand and never used for training.

Put the sentences as they were typed - one per line - into data/real/raw.txt, then:

    uv run python scripts/annotate.py --annotator emil

For each sentence a guess is shown. Press Enter to accept it. If a word in it is wrong, type
just that word, correctly spelled - or several, or the whole sentence. "s" skips a sentence,
"q" stops. Progress is saved after every line, so the file can be worked through in several
sittings.

The guess comes from the lexicon, never from the model being measured. A reference built by
accepting the model's own answers would lean towards them, and the model would be scored
against itself; the lexicon saves typing without that pull. Without the full training
lexicon in data/processed, the smaller one shipped in the package is used.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from schwa import bundled
from schwa.alphabet import az_lower, az_upper, strip_diacritics
from schwa.lexicon import Lexicon
from schwa.restore import IdentityRestorer, LexiconRestorer, Restorer
from schwa.tokenize import iter_words, key_of

DEFAULT_RAW = Path("data/real/raw.txt")
DEFAULT_OUT = Path("data/real/annotated.jsonl")
DEFAULT_LEXICON = Path("data/processed/lexicon.jsonl")


def in_case_of(original: str, word: str) -> str:
    """`word`, capitalised the way `original` is: yəni in place of Yeni is Yəni."""
    if len(original) > 1 and original.isupper():
        return az_upper(word)
    if original[:1].isupper():
        return az_upper(word[:1]) + az_lower(word[1:])
    return az_lower(word)


def apply_answer(typed: str, suggestion: str, answer: str) -> str | None:
    """The sentence an answer stands for, or None if it cannot be read as one.

    An empty answer keeps the suggestion, and the whole sentence replaces it. Anything else is
    taken as words to put right: each replaces the one word of the suggestion that is spelled
    the same without its diacritics, so a single wrong word costs one word of typing. A word
    that matches nothing, or more than one word, is refused rather than guessed at.
    """
    if not answer:
        return suggestion
    if strip_diacritics(answer) == strip_diacritics(typed):
        return answer

    correct = suggestion
    spans = iter_words(suggestion)
    for start, end in iter_words(answer):
        word = answer[start:end]
        matches = [span for span in spans if key_of(suggestion[slice(*span)]) == key_of(word)]
        if len(matches) != 1:
            return None
        left, right = matches[0]
        # A diacritic never changes a word's length, so the other spans still hold.
        correct = correct[:left] + in_case_of(suggestion[left:right], word) + correct[right:]
    return correct if strip_diacritics(correct) == strip_diacritics(typed) else None


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
    elif bundled.is_bundled():
        restorer = LexiconRestorer(bundled.bundled_lexicon())
    else:
        restorer = IdentityRestorer()

    done = load_done(args.out)
    args.out.parent.mkdir(parents=True, exist_ok=True)

    lines = [line.strip() for line in args.raw.read_text(encoding="utf-8").splitlines()]
    pending = [line for line in lines if line and line not in done]
    print(f"{len(done)} annotated, {len(pending)} to go\n")

    print("Enter accepts. A wrong word: type just that word, spelled right. s skips, q stops.\n")
    with args.out.open("a", encoding="utf-8") as out:
        for index, typed in enumerate(pending, start=1):
            suggestion = restorer.restore(typed)
            print(f"[{index}/{len(pending)}] typed:      {typed}")
            print(f"              suggestion: {suggestion}")

            # Word fixes add up on the sentence shown, until Enter accepts it.
            current, correct = suggestion, None
            while correct is None:
                answer = input("              correct:    ").strip()
                if answer.lower() in ("q", "s"):
                    break
                fixed = apply_answer(typed, current, answer)
                if fixed is None:
                    print(
                        "              ! that is not one of these words with other letters - "
                        "type the word as it appears here, or the whole sentence"
                    )
                elif not answer or fixed == answer:
                    correct = fixed
                else:
                    current = fixed
                    print(f"              now:        {current}")

            if answer.lower() == "q":
                break
            if correct is None:
                print()
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
