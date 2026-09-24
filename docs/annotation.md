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

The quick way is a chat export. In WhatsApp, open a chat you write a lot in, then **More →
Export chat → Without media**. In Telegram Desktop, **Export chat history**, with JSON as the
format. Save it in `data/exports/`: git ignores that folder, and it has to, because an export
holds the other side of every conversation. Then:

```bash
uv run python scripts/import_chat.py data/exports/chat.txt            # who wrote how much
uv run python scripts/import_chat.py data/exports/chat.txt --me Emil  # your name, as spelled there
```

It keeps only your messages - never the other person's - and drops links, email addresses,
phone numbers, media placeholders, deleted and forwarded messages, and anything under three
words. Then it samples 300 into `data/real/raw.txt`. Several exports can go in one command,
and `--append` adds to a file that is already there.

It cannot find names. Read `data/real/raw.txt` before annotating and take out anything you
would not want public: unlike the exports, this folder is meant to be published once the set
is done, and git will offer it.

By hand works too: one sentence per line in `data/real/raw.txt`, exactly as typed.

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
