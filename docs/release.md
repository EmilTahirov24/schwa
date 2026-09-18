# Releasing

Three things ship separately and can move at their own pace: the Python package, the browser
extension, and the demo. What they must never do is disagree about the model — the numbers in
the README belong to a specific model file, so a release starts by rebuilding it.

## The model

```bash
uv run --group train poe tagger      # only when the model itself changed
uv run --group train poe export      # checkpoint -> ONNX, refuses if answers differ
uv run --group train poe quantize    # int8, reports what it costs
uv run --group train poe bundle      # into the Python package
cd apps/extension && npm run vendor  # into the extension
```

Then re-run the evaluation and update the tables:

```bash
uv run --group train poe eval
uv run --group train python scripts/evaluate.py --split test
```

The test split is scored once per released model, not during development.

## The Python package

1. Bump `version` in `packages/core/pyproject.toml`.
2. `uv build --package duzelt --out-dir dist`
3. Check the wheel in a clean environment:
   ```bash
   uv run --no-project --with "dist/duzelt-<version>-py3-none-any.whl[onnx]" \
     python -c "from duzelt import restore; print(restore('sence neden'))"
   ```
4. `uv publish --token <pypi token>`

The wheel carries the model, so step 3 is the one that catches a build which forgot it: the
restorer reports `lexicon` instead of `hybrid`.

## The extension

1. Bump `version` in `apps/extension/manifest.json`.
2. `npm install && npm run vendor && npm test`
3. Load it unpacked once and use it on a real page — the parts that talk to Chrome have no
   automated coverage.
4. Zip the folder without `node_modules` and upload it.
5. The listing text is in [store-listing.md](store-listing.md); screenshots have to be retaken
   whenever the interface changes.

## The demo

The site reads the service address from `NEXT_PUBLIC_API_URL`, and the service picks its
restorer from `DUZELT_TAGGER` and `DUZELT_LEXICON`. `/v1/info` reports which one is loaded, so
after every deployment that endpoint is the check: if it says `lexicon` where it should say
`hybrid`, the model did not make it into the image.

## After releasing

- Tag the commit: `git tag v<version> && git push --tags`.
- Note what changed in `CHANGELOG.md`, in a sentence a user would care about.
