# Changelog

## Unreleased

### Added

- A second test set: 268,532 sentences of web text from CC-100 - news, interviews, blogs -
  so the numbers no longer describe Wikipedia alone.
- A 95% interval on every result, from a bootstrap over whole articles, and a paired
  comparison of each system with the one before it.
- A breakdown of the remaining errors by kind of word: names, words never seen in training,
  ambiguous words, words in capitals.
- CI runs the browser-against-Python parity tests on the committed model, and builds the demo
  page. `poe reproduce` now rebuilds every number in the docs.
- The demo page shows the results on both kinds of text, with their intervals, and an X-ray
  view: every letter that needed a decision, with the model's odds on it, and the ones it
  hesitated over lit up.

- Spelling suggestions: words that look misspelt get up to three corrections, shown as
  suggestions and never applied on their own. `schwa --spell`, `schwa.check()`, and a wavy
  amber underline on the demo page.
- Renamed to Schwa; the Python distribution is `schwa-az`, the import and command `schwa`.
- The demo page restores as you type, with each restored letter animated into place and a
  per-word note on where its spelling came from.
- The Python package carries the model: `pip install "schwa-az[onnx]"` and `restore()` works
  with nothing to download and no flags to pass.
- The browser extension carries it too, so text is restored inside the browser and is not
  sent anywhere. The service remains as a fallback.
- `schwa` command line tool, FastAPI service, demo page, Chrome extension.
- Four restorers, measured against each other: lexicon, context model, character tagger, and
  the hybrid of the tagger and the lexicon.

### Measured

- The shipped tagger now reads the web sample as well as Wikipedia. On web text, 268,532
  sentences, that lifted the hybrid from 93.2% to 95.7% on ambiguous words and from 89.5% to
  92.9% of sentences exactly right; on Wikipedia it changed nothing measurable. Four other
  training mixes were measured against it, including capitals added artificially, which did
  not ship.
- Spell checker, test split: 90.5% of single-letter typos recovered in the top three
  suggestions, with 1.41% of correct words flagged, against 4.03% for a plain word list.
- Wikipedia test split, 172,328 sentences: 93.9% on ambiguous words, 98.9% of all words,
  88.2% of sentences exactly right. Dev agrees within 0.3 points for every model.
- Quantising the tagger to int8 makes it 2.3 MB — 3.9× smaller and 1.9× faster — and costs
  no accuracy.

### Fixed

- Numbers in the README that no script produced or that had drifted from the results page:
  four CERs in their last digit, the plain word-list baseline (quoted as 6.6%, measured at
  4.03%), the context model's tuning figures, and the claim that almost every remaining
  error is a name - names are 46% of the errors. A test now holds the README's tables to
  the results.

### Known limits

- Both test sets are edited text. Informal forms written as one word, such as `nembilim` for
  `nə bilim`, are still left as typed; the hand-annotated set of real messages will put a
  number on how often.
- Proper nouns the training text never saw cannot be decided from the letters alone.
