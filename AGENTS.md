# Working in this repository

## Commands

```bash
uv sync                             # Python environment
uv run poe ci                       # exactly what CI runs: lint, format check, tests - run before pushing
uv run poe test                     # tests (torch-dependent ones skip without the train group)
uv run poe lint && uv run poe fmt
uv run --group train poe reproduce  # everything: data, models, every number in the docs (GPU)
uv run --group train poe tagger     # train the character tagger (GPU)
uv run --group train poe eval       # re-measure; rewrites docs/results.md and results.json
uv run poe serve                    # the service on :8000
cd apps/web && npm run dev          # the demo page
```

The Wikipedia dump belongs in `data/raw/`; nothing under `data/` or `models/` is committed.
The model the package ships, `packages/core/schwa/data`, is: it is what the extension and
the demo page copy, and what CI tests them against. After changing it, run
`scripts/make_fixtures.py` and `poe eval`.

## Layout

- `packages/core` — the library. No heavy dependency at import time: torch and onnxruntime are
  imported inside the functions that need them, so `pip install schwa-az` stays small.
- `packages/api` — FastAPI service.
- `apps/web`, `apps/extension` — demo page and Chrome extension.
- `scripts` — the pipeline, one step per file, each runnable on its own.
- `docs/decisions.md` — why things are the way they are. Add to it when a choice was not
  obvious; `docs/results.md` is generated, never hand-edited.

## Invariants

These are the things tests exist to protect. Breaking one is a bug, not a trade-off.

1. A restorer may change diacritics and nothing else. Same length, same case, same
   punctuation. `strip_diacritics(restored) == strip_diacritics(input)`.
2. Azerbaijani casing goes through `az_lower` / `az_upper`. Python's own `lower()` and
   `upper()` are wrong for `i`, `ı`, `İ` and `I`, and a lexicon built on them silently merges
   different words.
3. Train, dev and test are split per article, never per sentence.
4. The lexicon is built from the training split only.
5. Numbers in the README and in `docs/results.md` come from a run of the scripts. If a number
   cannot be reproduced by a command, it does not belong in the repository.

## Conventions

- English for code, comments, commits and documentation. The product's interface is
  Azerbaijani first.
- Commit messages say what changed and why, in the imperative. One concern per commit.
- Tests name the behaviour they protect, not the function they call.
- Measurements are reported with the setup that produced them: which split, how many
  sentences, which model file.
