# Building the real-world evaluation set

Wikipedia is written carefully; chat messages are not. Every number in the README so far
comes from Wikipedia text, which means it describes how the systems do on prose nobody types
in practice. This set is how that gap gets measured instead of guessed.

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

For each sentence the current restorer shows its guess. Press Enter to accept it, type the
correct sentence to replace it, `s` to skip, `q` to stop. Progress is saved after every line,
so it can be done in several sittings.

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
