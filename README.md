# duzelt

Restore Azerbaijani diacritics in text typed without them.

```
sence neden basliyaq   ->   səncə nədən başlayaq
```

Azerbaijani has seven letters a plain keyboard cannot produce — `ç ə ğ ı ö ş ü` — so people
drop them and type `sence` for `səncə`. Putting them back is not a lookup: `qiz` is either
`qız` ("girl") or `qiz`, and only the surrounding words decide which.

**Status:** in development. The data pipeline and two restorers are measured and reproducible;
the character-level model, the API, the web demo and the browser extension are next.

## How it works

Restoration is a per-character binary decision, not a rewrite of the sentence. Each of the
seven letter pairs collapses to exactly one ASCII letter, and every collapsed form has
exactly one alternative, so for each character there is a single question: does it carry a
diacritic? Two things follow. The text cannot be changed in any other way — a property test
pins it — and the models stay small enough to run on a CPU.

```
Wikipedia dump ──► articles ──► sentences ──► lexicon ──► context model
                                     │             │            │
                                     └─────────────┴────► evaluation
```

Three systems are compared on the same data:

| System | What it does |
| --- | --- |
| `identity` | changes nothing; the floor |
| `lexicon` | always picks the spelling seen most often in training |
| `context` | scores each candidate spelling by the words around it |

## What I measured

Dev split, 172,034 sentences from articles never seen in training:

| System | Ambiguous word accuracy | Word accuracy | CER | Sentence accuracy | ms / sentence |
| --- | --- | --- | --- | --- | --- |
| identity | 41.0% | 36.5% | 14.56% | 3.7% | 0.00 |
| lexicon | 79.2% | 97.1% | 0.60% | 72.1% | 0.05 |
| context | **83.9%** | 97.3% | 0.57% | 73.7% | 0.06 |

Corpus: 187,969 articles → 2,947,943 sentences. The lexicon holds 486,374 typed forms, of
which 2,184 are genuinely ambiguous; those account for 96,077 of the 2,202,231 words in the
dev split, or 4.4%. Another 3.2% of the words were never seen in training at all. The
context model is 1.3 MB and costs 0.01 ms per sentence on top of the lexicon.

Accuracy on **ambiguous words** is the number that matters. Most words are unambiguous once
the diacritics are gone, so overall word accuracy is already high before any model exists.

Two details behind the numbers:

- A rival spelling only counts as a real second reading when it reaches 5% of a word's
  occurrences. Wikipedia writes `bir` 286k times and `bır` 39 times — that is a typo, and
  counting it as an ambiguity would have filled the score with unwinnable words.
- Sentences are split into train, dev and test **per article**, so near-copies inside one
  article cannot land on both sides of the split.

## Where it still fails

Most remaining errors are words the lexicon has never seen — rare proper nouns like
`Uşqulidəki` or `Argonavtların` are left exactly as typed. A character-level model does not
need to have seen a word before, which is why it is the next step.

## Run it locally

```bash
uv sync
uv run poe test                # 95 tests
uv run poe reproduce           # dump -> corpus -> lexicon -> model -> results
uv run duzelt --lexicon data/processed/lexicon.jsonl "sence neden basliyaq"
```

`reproduce` downloads nothing on its own: put the Azerbaijani Wikipedia dump into
`data/raw/` first. Every number in this README comes out of that run.

## Data and licensing

Training text comes from the Azerbaijani Wikipedia dump (CC BY-SA). The evaluation set of
real, informal sentences is annotated by hand with `scripts/annotate.py` and is never used
for training.

## License

MIT
