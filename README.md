# Schwa

[![CI](https://github.com/EmilTahirov24/schwa/actions/workflows/ci.yml/badge.svg)](https://github.com/EmilTahirov24/schwa/actions/workflows/ci.yml)
[![Demo](https://img.shields.io/badge/demo-live-10b981)](https://emiltahirov24.github.io/schwa/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Restore Azerbaijani diacritics in text typed without them.

```
sence neden basliyaq   ->   səncə nədən başlıyaq
```

**Try it: [emiltahirov24.github.io/schwa](https://emiltahirov24.github.io/schwa/)** — type
without the letters and watch them come back, or switch on *X-ray* to see how sure the model
was of every letter. The model runs in your browser, so nothing you type is sent anywhere.

The name is the letter: *schwa* is what linguists call **ə**. It is the third most common
letter in Azerbaijani text, and on its own more common than the other six letters a plain
keyboard lacks put together — 8.8% of all letters against 8.5%, counted on the dev split.

Azerbaijani has seven letters a plain keyboard cannot produce — `ç ə ğ ı ö ş ü` — so people
drop them and type `sence` for `səncə`. Putting them back is not a lookup: `qiz` is either
`qız` ("girl") or `qiz`, and only the surrounding words decide which.

**Status:** working, and measured on two kinds of text it never saw in training: it gets
93.9% of the genuinely ambiguous words right on Wikipedia and 95.7% on the open web. The
demo page, the browser extension and the Python package all carry the model and run it
locally. Still to come: an evaluation set of real chat messages, and the
extension's store release.

## What is in here

| Piece | What it is |
| --- | --- |
| `packages/core` | the library: alphabet, lexicon, context model, character tagger, CLI |
| `packages/api` | FastAPI service, `POST /v1/restore` |
| `apps/web` | the demo page: see each change, click one to keep what you typed, or X-ray the model's odds on every letter |
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
                                            ├──► character tagger ◄──┐
                                            └──► test split          │
CC-100 web crawl ─► documents ─► sentences ─┬────────────────────────┘
                                            └──► test split
```

Every system is scored on both test splits, which no model has read.

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
and nowhere else, is worth 1.5 points of whole-sentence accuracy on Wikipedia, and 0.1 on
the web.

The [model card](docs/model_card.md) sums up the one that ships: its data, its numbers, and
where not to trust it.

## What I measured

Two test sets, each scored once, both made of text no model saw in training:

- **Wikipedia**: 172,328 sentences from 10,429 articles held out of training.
- **The web**: 268,532 sentences from 21,797 documents of
  [CC-100](https://data.statmt.org/cc-100/), text crawled from the open web: news,
  interviews, blogs. Every sentence that also occurs in Wikipedia was taken out first.

Wikipedia:

<!-- results: test -->
| System | Ambiguous word accuracy | Word accuracy | CER | Sentence accuracy |
| --- | --- | --- | --- | --- |
| identity | 40.1% | 36.0% | 14.71% | 3.5% |
| lexicon | 79.3% | 97.1% | 0.60% | 71.9% |
| context | 85.1% | 97.4% | 0.56% | 74.0% |
| tagger | 93.9% | 98.7% | 0.19% | 86.7% |
| **hybrid** | **93.9%** | **98.9%** | **0.17%** | **88.2%** |

The web:

<!-- results: web_test -->
| System | Ambiguous word accuracy | Word accuracy | CER | Sentence accuracy |
| --- | --- | --- | --- | --- |
| identity | 27.9% | 33.4% | 15.59% | 0.2% |
| lexicon | 79.2% | 97.0% | 0.74% | 70.1% |
| context | 87.6% | 97.3% | 0.68% | 73.3% |
| tagger | 95.7% | 99.3% | 0.10% | 92.8% |
| **hybrid** | **95.7%** | **99.4%** | **0.10%** | **92.9%** |

Every number has a 95% interval in [docs/results.md](docs/results.md). They come from a
bootstrap over whole articles, because sentences from one article are not independent: a name
that recurs through it is restored right every time or wrong every time. For every model the
intervals are under a point wide. Each system also beats the one above it on the same
resamples, clear of zero, with one exception: on ambiguous words the hybrid and the tagger are
identical by construction, since the lexicon only overrules words the training text was
unanimous about and an ambiguous word never is.

For every model, dev comes out within 0.3 points of the Wikipedia test split, which is the
point of having kept the two apart: nothing here was tuned against the split it is reported on.

Corpus: 187,969 articles → 2,947,943 sentences. The lexicon holds 486,374 typed forms, of
which 2,184 are genuinely ambiguous; those account for 4.4% of the words in the dev split.
Another 3.2% were never seen in training at all — that is where the tagger pulls ahead of
the word models, because it reads letters rather than vocabulary.

The tagger is a 2.3M-parameter BiLSTM trained for two epochs over Wikipedia and a sample of
the web together, 4.3 million sentences. Quantised to int8 it is **2.3 MB**, 3.9× smaller and
1.9× faster than the float version, and loses no accuracy — which is what lets the browser
extension carry the model instead of sending your text anywhere.

Accuracy on **ambiguous words** is the number that matters. Most words are unambiguous once
the diacritics are gone, so overall word accuracy is already high before any model exists.

Two details behind the numbers:

- A rival spelling only counts as a real second reading when it reaches 5% of a word's
  occurrences. Wikipedia writes `bir` 286k times and `bır` 39 times — that is a typo, and
  counting it as an ambiguity would have filled the score with unwinnable words.
- Sentences are split into train, dev and test **per article**, so near-copies inside one
  article cannot land on both sides of the split.

### Wikipedia against the web

A tagger that has read only Wikipedia loses half a point on ambiguous words when it moves to
the web — 93.8% against 93.2%, intervals 93.5–94.1 and 93.0–93.4, which do not overlap.
Whole sentences go the other way: 88.4% come out exactly right on the web against 86.7% on
Wikipedia, although web sentences are no shorter (13.0 words against 12.9). They hold fewer
of the words the model finds hard — 2.4% never seen in training against 3.1%, and 11.8%
capitalised mid-sentence, mostly names, against 15.0%.

### What the tagger read

The first tagger read Wikipedia and nothing else. Five of them, the same in everything but
their training text, scored alone on both test sets — accuracy on ambiguous words, and on
the web's words written entirely in capitals; whole sentences and every interval are in
[results.md](docs/results.md):

| Trained on | Wikipedia test | Web test | Web, words in capitals |
| --- | --- | --- | --- |
| Wikipedia | 93.8% | 93.2% | 83.5% |
| the web | 89.8% | 96.1% | 94.8% |
| **both — the one that ships** | **93.9%** | **95.7%** | **94.4%** |
| Wikipedia, some of it put in capitals | 93.6% | 93.2% | 91.1% |
| both, some of it put in capitals | 93.8% | 95.6% | 95.4% |

Reading the web as well gains 2.5 points on the web's ambiguous words and 4.4 on its whole
sentences, and costs nothing measurable on Wikipedia, so that is the model that ships. On
the web it makes a third fewer mistakes: 22,545 wrong words, where the Wikipedia-only model
made 34,114.
Capitals — headlines, mostly — were the web's worst words. Putting training text into
capitals artificially fixed some of them but cost 0.2 points on Wikipedia; the real
headlines in web text fixed more on their own. The rule for what would ship was set before
the runs; [decision 19](docs/decisions.md) has the rest.

## Spelling

Diacritics are only half of what goes wrong when typing fast. Schwa also points out words
that look misspelt — `xayis` → *xahiş*, `mektbe` → *məktəb, məktəbə* — but it never applies
those on its own. Restoring accents can only add accents; correcting spelling changes
letters, and a wrong correction turns a correct rare word into a common one. So typos are
**suggested** (a wavy amber underline in the demo) and diacritics are **applied**.

It is a noisy-channel spell checker over the same Wikipedia vocabulary: candidates one or two
edits away, and two words run together, ranked by frequency against the chance of that many
slips. Test split, typos made by dropping, adding, swapping or replacing letters in real words:

| | Top-1 correct | Top-3 correct |
| --- | --- | --- |
| One slip | 84.8% | 90.5% |
| Two slips | 54.0% | 66.0% |

**False alarms: 1.41%** of 12,674 correct words — where a plain word list, underlining every
word seen fewer than five times, would flag 4.03%. The checker does more than the list: it
also suspects rare real words one letter from a much commoner one. Keeping that from
flagging correct words took three rules, each found by reading what got flagged: a common
word is never suspected for sitting next to a commoner one (`ev`, *house*, is one letter
from `və`); a capitalised word mid-sentence is taken for a name; and since Azerbaijani stacks
suffixes, a known stem plus an ending seen after a thousand other stems counts as a word.

Wikipedia is third person, so *getmədim* (I did not go) never appears in it and was flagged.
Personal endings are therefore added from the grammar rather than learned from counts. How
much that helps can only be measured on the kind of text people actually write.

## Where it still fails

The shipped model gets 25,995 words wrong on the Wikipedia test split, out of 2,120,093 that
could be wrong. `scripts/error_analysis.py` sorts them by kind of word (the kinds overlap):

| Words | Share of words | Share of errors |
| --- | --- | --- |
| capitalised in mid-sentence, mostly names | 15.0% | 46.8% |
| never seen in training | 3.2% | 36.6% |
| ambiguous | 4.6% | 22.7% |
| lowercase | 76.8% | 36.5% |

**Names** are the largest part. Whether `Gurcan` is meant to be `Gürcan` is not decidable
from the letters — you have to know the person. A dictionary of names would move this;
nothing about the sentence will.

**Ambiguous words** are the part a better model could still win: `yeni` (new) against `yəni`
(that is), `səhər` (morning) against `şəhər` (city), `ölüb` (died) against `olub` (was) —
the kind of mistake that changes what a sentence says.

**The reference is not always right.** In 20.1% of the errors the model wrote the spelling
the training text uses at least 95% of the time, and the reference disagrees. Some of those
are rare readings the model could not know about; others are typos it is scored wrong for
correcting — `ve` where `və` was meant is among the most frequent. So 93.9% is a floor, not
a ceiling.

**Capitals.** On web text, words written entirely in capitals, mostly headlines, are 1.0% of
the words. In capitals a plain `I` is usually a dotted `İ`, the reverse of lowercase, and
the model that had read only Wikipedia got 13.4% of them wrong. Reading the web as well
brought that to 4.9% — still more than ten times the rate for lowercase words.

**And the gap still unmeasured.** Web text is closer to how people write than an
encyclopedia, but it is still edited. Everyday forms come out right — `deyesen gec qalacam`
becomes `deyəsən gec qalacam` — but informal forms written as one word, such as `nembilim`
for `nə bilim`, are left as typed. [docs/annotation.md](docs/annotation.md) describes the
hand-annotated set of real messages that will put a number on that gap.

## Use it

```bash
pip install "schwa-az[onnx] @ git+https://github.com/EmilTahirov24/schwa#subdirectory=packages/core"
```

It is not on PyPI yet; that installs it straight from this repository, model included.

```python
from schwa import restore

restore("sence neden basliyaq")  # 'səncə nədən başlıyaq'
```

```bash
schwa "sence neden basliyaq"
cat notes.txt | schwa
schwa --spell "xayis edirem, mektbe gec qalmisam"   # xayis -> xahiş, xalis, mayıs ...
```

```python
from schwa import check

for suggestion in check("xayis edirem"):
    print(suggestion.typed, suggestion.options)  # xayis ('xahiş', 'xalis', 'mayıs')
```

The model travels with the package — a 5.3 MB wheel, no downloads, no configuration. Without
the `[onnx]` extra the package still installs and falls back to the lexicon alone.

## Run it locally

```bash
uv sync
uv run poe test                     # the test suite
uv run poe serve                    # the service on :8000
uv run --group train poe reproduce  # every model and every number, from the raw text (GPU)
```

`reproduce` starts from the Azerbaijani Wikipedia dump in `data/raw/`, fetches the web sample
itself, trains the models and writes [docs/results.md](docs/results.md) and
`docs/results.json`. Every number in this README comes out of that run, and a test fails if
the tables here disagree with it. The CLI and the demo page:

```bash
uv run schwa --lexicon data/processed/lexicon.jsonl "sence neden basliyaq"
cd apps/extension && npm install && npm run vendor   # the runtime and model the page uses
cd ../web && npm install && npm run dev
```

### Compare your own system

The test sets double as a benchmark. Write out a split the way a system receives it, restore
it with anything you like, and score it exactly as every number here is scored — same
metrics, same intervals; a prediction that changes more than diacritics is rejected:

```bash
uv run python scripts/score.py --split web_test --typed > typed.txt
your-system < typed.txt > restored.txt
uv run python scripts/score.py --split web_test restored.txt
```

## Privacy

The demo page and the extension run the model in the browser: the text never leaves the
machine it was typed on. The extension also declares no permission for any website and runs
nothing on a page until you invoke it. The optional HTTP service holds text in memory for the
length of one request and writes it nowhere. Details:
[privacy](https://emiltahirov24.github.io/schwa/privacy/).

The browser and the Python package run the same model through different code, so an
integration test runs the shipped model through onnxruntime-web and checks that every answer
matches the Python package exactly; CI runs it on every push. It is what caught the two
cutting long text differently.

## Data and licensing

Training text comes from the Azerbaijani Wikipedia dump (CC BY-SA). The web test set is a
sample of [CC-100](https://data.statmt.org/cc-100/) (Conneau et al., 2020; Wenzek et al.,
2020), fetched by the script rather than redistributed. The evaluation set of real, informal
sentences is annotated by hand and never used for training.

## License

MIT
