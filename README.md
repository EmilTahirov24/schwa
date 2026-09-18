# duzelt

Restore Azerbaijani diacritics in text typed without them.

```
sence neden basliyaq   ->   səncə nədən başlayaq
```

**Try it: [emiltahirov24.github.io/duzelt](https://emiltahirov24.github.io/duzelt/)** — the model
runs in your browser, so nothing you type is sent anywhere.

Azerbaijani has seven letters a plain keyboard cannot produce — `ç ə ğ ı ö ş ü` — so people
drop them and type `sence` for `səncə`. Putting them back is not a lookup: `qiz` is either
`qız` ("girl") or `qiz`, and only the surrounding words decide which.

**Status:** working and measured on Wikipedia. The demo page, the browser extension and the
Python package all carry the model and run it locally. Still to come: the evaluation set of
real informal sentences, and the extension's store release.

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

Four systems, measured the same way:

| System | What it does |
| --- | --- |
| `lexicon` | always picks the spelling seen most often in training |
| `context` | scores each candidate spelling by the words around it |
| `tagger` | a character-level BiLSTM; it does not need to have seen the word before |
| `hybrid` | the tagger, overruled where the training text was unanimous about a word |

The last one exists because the first and the third fail in opposite places. The tagger reads
letters rather than vocabulary, so it handles words nothing is known about — but it still
garbled names it had seen only a few times, writing `Sulaveri` where the training text says
`Şulaveri` nine times out of nine. Letting the lexicon overrule it on exactly those words,
and nowhere else, is worth 1.4 points of whole-sentence accuracy.

## What I measured

Test split, 172,328 sentences, scored once, from articles never seen in training:

| System | Ambiguous word accuracy | Word accuracy | CER | Sentence accuracy |
| --- | --- | --- | --- | --- |
| identity | 40.1% | 36.0% | 14.72% | 3.5% |
| lexicon | 79.3% | 97.1% | 0.59% | 71.9% |
| context | 85.1% | 97.4% | 0.55% | 74.0% |
| tagger | 93.8% | 98.7% | 0.19% | 86.7% |
| **hybrid** | **93.8%** | **98.9%** | **0.16%** | **88.1%** |

Dev comes out within 0.2 points of this everywhere, which is the point of having kept the two
apart: nothing here was tuned against the split it is reported on.

Corpus: 187,969 articles → 2,947,943 sentences. The lexicon holds 486,374 typed forms, of
which 2,184 are genuinely ambiguous; those account for 4.4% of the words in the dev split.
Another 3.2% were never seen in training at all — that is where the tagger pulls ahead of
the word models, because it reads letters rather than vocabulary.

The tagger is a 2.3M-parameter BiLSTM trained for two epochs over the full corpus. Quantised
to int8 it is **2.3 MB**, 3.9× smaller and 1.6× faster than the float version, and loses 0.01
points of accuracy — which is what lets the browser extension carry the model instead of
sending your text anywhere.

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

## Use it

```bash
pip install "duzelt[onnx]"
```

```python
from duzelt import restore

restore("sence neden basliyaq")  # 'səncə nədən başlayaq'
```

```bash
duzelt "sence neden basliyaq"
cat notes.txt | duzelt
```

The model travels with the package — 3.5 MB, no downloads, no configuration. Without the
`[onnx]` extra the package still installs and falls back to the lexicon alone.

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

The demo page and the extension run the model in the browser: the text never leaves the
machine it was typed on. The extension also declares no permission for any website and runs
nothing on a page until you invoke it. The optional HTTP service holds text in memory for the
length of one request and writes it nowhere. Details:
[privacy](https://emiltahirov24.github.io/duzelt/privacy/).

The browser and the Python package run the same model through different code, so an
integration test runs the shipped model through onnxruntime-web and checks that every answer
matches the Python package exactly. It is what caught the two cutting long text differently.

## Data and licensing

Training text comes from the Azerbaijani Wikipedia dump (CC BY-SA). The evaluation set of
real, informal sentences is annotated by hand and never used for training.

## License

MIT
