# Changelog

## Unreleased

### Added

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

- Spell checker, test split: 90.5% of single-letter typos recovered in the top three
  suggestions, with 1.41% of correct words flagged.

- Test split, 172,328 sentences, scored once: 93.8% on ambiguous words, 98.9% of all words,
  88.1% of sentences exactly right. Dev agrees within 0.2 points.
- Quantising the tagger to int8 makes it 2.3 MB — 3.9× smaller and 1.6× faster — for 0.01
  points of accuracy.

### Known limits

- Everything is measured on Wikipedia. Informal words it never contains, such as `hərşey`,
  are still restored wrongly. The hand-annotated set of real sentences will put a number on
  that; until then the reported accuracy describes encyclopedic prose, not chat.
- Proper nouns the training text never saw cannot be decided from the letters alone.
