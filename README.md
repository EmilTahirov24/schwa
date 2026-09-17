# duzelt

Restore Azerbaijani diacritics in text typed without them.

```
sence neden basliyaq   ->   səncə nədən başlayaq
```

Azerbaijani has seven letters that a plain keyboard cannot produce — `ç ə ğ ı ö ş ü` — so
people drop them and type `sence` for `səncə`. Putting them back is not a lookup: `qiz` is
either `qız` ("girl") or `qiz`, and only the surrounding words decide which.

**Status:** in development. The alphabet layer and its tests are in place; data pipeline,
models and measurements are next. Numbers will appear here only once they are measured.

## Planned pieces

| Piece | What it is |
| --- | --- |
| `duzelt` | Python library and CLI |
| API | FastAPI service behind the web demo and the extension |
| Web | Paste text, see every change highlighted, reject the ones you disagree with |
| Extension | Chrome: select text, fix it in place |

## How it will work

Restoration is treated as a per-character binary decision rather than as rewriting the
sentence. Each of the seven letter pairs collapses to exactly one ASCII letter, so for
every character the model only answers: *does this one carry a diacritic?* Two consequences
matter — the text cannot be altered in any other way, and the model stays small enough to
run on a CPU.

Three systems will be compared on the same test sets: a dictionary that always picks the
most frequent form, an n-gram model with Viterbi decoding, and a character-level tagger.

## Run it locally

```bash
uv sync
uv run pytest
```

## Data and licensing

Training text comes from the Azerbaijani Wikipedia dump (CC BY-SA). The evaluation set of
real, informal sentences is annotated by hand and kept out of training.

## License

MIT
