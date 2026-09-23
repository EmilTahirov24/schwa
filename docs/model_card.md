# Model card: Schwa's diacritic tagger

What the shipped model is, what it was trained and tested on, and where it should not be
trusted. Every number here comes from `docs/results.json` or `docs/results.md`, written by the
scripts; a test fails if the tables below disagree with them.

## The model

- **Task.** Put back the diacritics of Azerbaijani text typed without them: for every
  character that could carry one (`c e g i o s u` and their capitals), decide whether it
  does. Nothing else about the text can change.
- **Architecture.** A character-level bidirectional LSTM: 96-dimensional character
  embeddings, two layers of 256 units in each direction, a two-way decision per character;
  2.31M parameters. Text longer than 256 characters is read in overlapping windows.
- **What ships.** The network quantised to int8 and exported to ONNX, 2.3 MB, plus a lexicon
  of the words the training text always spelled one way, which overrules the network on
  exactly those words. The Python package, the browser extension and the demo page carry
  the same four files and run them locally.
- **Training.** Two epochs, batch 512, AdamW with a one-cycle schedule peaking at 3e-3,
  seed 0; the checkpoint with the best accuracy on the decisions of both dev splits is kept.
  `uv run --group train poe tagger` rebuilds it.
- **Licence.** MIT for the code and the model.

## Data

- **Training:** 4,306,000 sentences - Azerbaijani Wikipedia (CC BY-SA), 2,603,581, and the
  training split of a CC-100 web sample, 1,702,419. Both are split from their dev and test
  sets by article or document. Reading the web as well was chosen over four alternatives,
  measured; see [decision 19](decisions.md).
- **Lexicon:** from the Wikipedia training split only.
- **Wikipedia test:** 172,328 sentences from 10,429 articles never seen in training.
- **Web test:** 268,532 sentences from 21,797 documents of CC-100, text crawled from the open
  web - news, interviews, blogs - with every sentence that also occurs in Wikipedia removed.

## How well it works

The shipped system is the hybrid, the network corrected by the lexicon. Accuracy on
ambiguous words - words whose typed form stands for more than one real word - is the number
that says how good a restorer is; almost every other word is easy.

Wikipedia test:

<!-- results: test -->
| System | Ambiguous word accuracy | Word accuracy | CER | Sentence accuracy |
| --- | --- | --- | --- | --- |
| tagger | 93.9% | 98.7% | 0.19% | 86.7% |
| hybrid | 93.9% | 98.9% | 0.17% | 88.2% |

Web test:

<!-- results: web_test -->
| System | Ambiguous word accuracy | Word accuracy | CER | Sentence accuracy |
| --- | --- | --- | --- | --- |
| tagger | 95.7% | 99.3% | 0.10% | 92.8% |
| hybrid | 95.7% | 99.4% | 0.10% | 92.9% |

95% intervals, from a bootstrap over whole articles or documents, are under a point wide;
they are in [results.md](results.md) with the baselines and the paired comparisons.

## Where it fails

- **Names.** A capital letter in mid-sentence marks 15% of Wikipedia's words and 47% of the
  errors. Whether `Gurcan` is `Gürcan` depends on the person, not the sentence. A list of
  names from Wikipedia's titles was measured and does not help: one typed form stands for
  different people ([decision 21](decisions.md)).
- **Genuinely ambiguous words.** `yeni` (new) and `yəni` (that is), `səhər` (morning) and
  `şəhər` (city), `ölüb` (died) and `olub` (was): the errors that change what a sentence
  says, and the ones a reader should check.
- **Capitals.** Words written entirely in capitals - headlines, mostly - are wrong 4.9% of
  the time on web text, more than ten times as often as lowercase words: in capitals a plain
  `I` is usually a dotted `İ`, the reverse of lowercase.
- **Chat.** Both test sets are edited text. Everyday forms the web taught it come out right
  (`deyesen gec qalacam` → `deyəsən gec qalacam`), but informal forms written as one word,
  such as `nembilim` for `nə bilim`, are left as typed; how often that happens in real
  messages, nobody has measured yet.

## Use it for

Restoring text a person typed without an Azerbaijani layout, with that person reading the
result: messages, notes, search queries, text that was stripped of its diacritics by some
system on the way.

## Do not use it for

- Text in other languages. Turkish shares most of these letters and uses them differently.
- Correcting spelling. Restoration only ever adds diacritics; the separate spell checker
  suggests corrections and never applies them.
- Official records - names in documents, legal or medical text - without a person checking
  every change. A wrong diacritic in a name makes it a different name.

## Privacy

The model runs where the text is: in the browser tab, the extension, or the Python process.
Nothing typed into the demo page or the extension is sent anywhere.
