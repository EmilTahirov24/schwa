# duzelt

Restore Azerbaijani diacritics in text typed without them.

```
sence neden basliyaq   ->   səncə nədən başlayaq
```

Azerbaijani has seven letters a plain keyboard cannot produce — `ç ə ğ ı ö ş ü` — so people
drop them and type `sence` for `səncə`. Putting them back is not a lookup: `qiz` is either
`qız` ("girl") or `qiz`, and only the surrounding words decide which.

**Status:** in development. The pipeline, three restorers, the service, the demo page and the
browser extension work and are measured. Still to come: the evaluation set of real informal
sentences, in-browser inference, and the store release.

## What is in here

| Piece | What it is |
| --- | --- |
| `packages/core` | the library: alphabet, lexicon, context model, character tagger, CLI |
| `packages/api` | FastAPI service, `POST /v1/restore` |
| `apps/web` | the demo page: paste text, see each change, click one to keep what you typed |
| `apps/extension` | Chrome extension: fix the field you are typing in with `Ctrl+Shift+E` |
| `scripts` | dump → corpus → lexicon → models → results |

## How it works

Restoration is a per-character binary decision, not a rewrite of the sentence. Each of the
seven letter pairs collapses to exactly one ASCII letter, and every collapsed form has
exactly one alternative, so for each character there is a single question: does it carry a
diacritic? Two things follow. The text cannot be changed in any other way — a property test
pins it — and the models stay small enough to run on a CPU.

```
Wikipedia dump ──► articles ──► sentences ──┬──► lexicon ──► context model
                                            │        │            │
                                            └────────┴────────────┴──► character tagger
                                                                              │
                                                       evaluation ◄───────────┘
```

Three systems, measured the same way:

| System | What it does |
| --- | --- |
| `lexicon` | always picks the spelling seen most often in training |
| `context` | scores each candidate spelling by the words around it |
| `tagger` | a character-level BiLSTM; it does not need to have seen the word before |

## What I measured

Dev split, 172,034 sentences from articles never seen in training:

| System | Ambiguous word accuracy | Word accuracy | CER | Sentence accuracy | ms / sentence |
| --- | --- | --- | --- | --- | --- |
| identity | 41.0% | 36.5% | 14.56% | 3.7% | 0.00 |
| lexicon | 79.2% | 97.1% | 0.60% | 72.1% | 0.05 |
| context | 85.0% | 97.4% | 0.56% | 74.2% | 0.06 |
| **tagger** | **93.8%** | **98.7%** | **0.20%** | **86.4%** | 0.31 |

Corpus: 187,969 articles → 2,947,943 sentences. The lexicon holds 486,374 typed forms, of
which 2,184 are genuinely ambiguous; those account for 96,077 of the 2,202,231 words in the
dev split, or 4.4%. Another 3.2% of the words were never seen in training at all — the gap
between the word models and the tagger is largely those.

The tagger is a 2.3M-parameter BiLSTM trained for two epochs over the full corpus, 9 MB as
a checkpoint and the same as ONNX. It answers 0.3 ms per sentence on a CPU.

Accuracy on **ambiguous words** is the number that matters. Most words are unambiguous once
the diacritics are gone, so overall word accuracy is already high before any model exists.

Two details behind the numbers:

- A rival spelling only counts as a real second reading when it reaches 5% of a word's
  occurrences. Wikipedia writes `bir` 286k times and `bır` 39 times — that is a typo, and
  counting it as an ambiguity would have filled the score with unwinnable words.
- Sentences are split into train, dev and test **per article**, so near-copies inside one
  article cannot land on both sides of the split.

## Where it still fails

Two different things, worth keeping apart.

**Names.** Almost everything the tagger gets wrong now is a proper noun: `Şulaveri`,
`Klarçetinin`, `Burcanadze`, `Tsxenitskali`. Whether `Gurcan` is meant to be `Gürcan` is not
decidable from the letters — you have to know the person. A dictionary of names would move
this; nothing about the sentence will.

**The reference is not always right.** `ve` appears in Wikipedia where `və` was meant, and
the tagger is scored wrong for restoring it. So 93.8% is a floor, not a ceiling.

**And the gap nobody has measured yet.** Every number here comes from Wikipedia, which is not
how people write to each other. `basliyaq` — ordinary in a message, absent from an
encyclopedia — is restored correctly by the tagger and left alone by the word models, which
hints at the size of that gap without measuring it.
[docs/annotation.md](docs/annotation.md) describes the hand-annotated set of real sentences
that will put a number on it.

## Run it locally

```bash
uv sync
uv run poe test                  # the test suite
uv run poe reproduce             # corpus, lexicon, context model, results
uv run --group train poe tagger  # the character tagger, on a GPU
uv run poe serve                 # the service on :8000
```

`reproduce` starts from the Azerbaijani Wikipedia dump in `data/raw/`; every number in this
README comes out of that run. The CLI and the demo page:

```bash
uv run duzelt --lexicon data/processed/lexicon.jsonl "sence neden basliyaq"
cd apps/web && npm install && npm run dev
```

## Privacy

The service holds text in memory for the length of one request and writes it nowhere — not
to disk, not to the logs. The extension declares no permission for any website and runs
nothing on a page until you invoke it. Details: [privacy](apps/web/src/app/privacy/page.tsx).

## Data and licensing

Training text comes from the Azerbaijani Wikipedia dump (CC BY-SA). The evaluation set of
real, informal sentences is annotated by hand and never used for training.

## License

MIT
