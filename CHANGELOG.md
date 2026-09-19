# Changelog

## Unreleased

Nothing yet.

## 0.1.0 — 2026-09-19

The first release.

### What it does

- Restores Azerbaijani diacritics in text typed without them, with a character-level tagger
  corrected by a lexicon of the words its training text always spelled one way. Only
  diacritics can change; nothing else about the text ever does.
- Suggests corrections for words that look misspelt - up to three each - and never applies
  them on its own.
- The Python package `schwa-az` carries the model: `restore()`, `check()` and the `schwa`
  command work with nothing to download. Until it is on PyPI it installs from the repository.
- The Chrome extension fixes the field you are typing in (`Ctrl+Shift+E`) or the text you
  select. It carries the model too, asks for no permission on any website, and the text never
  leaves the browser.
- The demo page restores as you type, shows where each word's spelling came from, and has an
  X-ray view of the model's odds on every letter. It reports the results on both test sets,
  with their intervals.
- An optional HTTP service serves the same model for use from code.

### Measured

- On web text, 268,532 sentences from CC-100 no model read in training: 95.7% of ambiguous
  words and 92.9% of sentences exactly right.
- On Wikipedia's test split, 172,328 sentences: 93.9% of ambiguous words and 88.2% of
  sentences exactly right. Dev agrees within 0.3 points for every model.
- The tagger reads Wikipedia and the web sample together, chosen over four other training
  mixes: against Wikipedia alone it gains 2.5 points on the web's ambiguous words and loses
  nothing measurable on Wikipedia.
- Spell checker, Wikipedia test split: 90.5% of single-letter typos recovered in the top three
  suggestions, with 1.41% of correct words flagged, against 4.03% for a plain word list.
- The int8 model is 2.3 MB — 3.9× smaller and 1.9× faster than the float one — and costs no
  accuracy.

Every number has a 95% interval in [docs/results.md](docs/results.md); `poe reproduce`
rebuilds all of them.

### Known limits

- Both test sets are edited text. Informal forms written as one word, such as `nembilim` for
  `nə bilim`, are still left as typed; the hand-annotated set of real messages will put a
  number on how often.
- Proper nouns the training text never saw cannot be decided from the letters alone.
