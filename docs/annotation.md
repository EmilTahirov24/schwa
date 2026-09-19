# Building the real-world evaluation set

Wikipedia and news sites are written carefully; chat messages are not. Every number in the
README so far comes from edited text - Wikipedia and a web crawl - which means it describes
how the systems do on prose somebody proofread. This set is how the gap to real messages
gets measured instead of guessed.

## What goes in

About 300 sentences of real, informal Azerbaijani, as they were actually typed — with the
missing letters, the shortcuts, the slang. Use your own messages, or anything public.
Do not put other people's private messages in a file that ends up on GitHub.

Sentences where nothing is missing are still useful: a restorer that "corrects" text that
was already right is making a mistake worth counting.

## How to collect them

1. Copy your own messages out of wherever you write them.
2. Put one sentence per line in `data/real/raw.txt`, exactly as typed.
3. Strip anything you would not want public: names, numbers, addresses.

## How to annotate

```bash
uv run python scripts/annotate.py --annotator emil
```

For each sentence the tool shows a guess. Press Enter to accept it, type the correct sentence
to replace it, `s` to skip, `q` to stop. Progress is saved after every line, so it can be
done in several sittings.

The guess comes from the lexicon, not from the model this set will measure. Accepting the
model's own answers would tilt the reference towards them. The lexicon leaves the ambiguous
words - the ones that matter - as typed, so each of those is a decision you make yourself.

The tool refuses any correction that changes more than diacritics — a different word order or
a fixed typo would make the sentence unusable as a reference, because the restorers are not
allowed to do either.

## Why a second annotator

Have someone else annotate the same sentences into their own file:

```bash
uv run python scripts/annotate.py --annotator <name> --out data/real/annotated-<name>.jsonl
```

Where the two of you disagree, the sentence is genuinely ambiguous even to native speakers,
and no model can be blamed for missing it. Reporting how often that happens is the honest
ceiling for the whole task.
