# Releasing

Three things ship separately and can move at their own pace: the Python package, the browser
extension, and the demo. What they must never do is disagree about the model — the numbers in
the README belong to a specific model file, so a release starts by rebuilding it.

## The model

```bash
uv run --group train poe tagger      # only when the model itself changed
uv run --group train poe ship        # ONNX (refuses if answers differ), int8, bundle
cd apps/extension && npm run vendor  # into the extension
```

`packages/core/schwa/data` is committed: it is the one copy of the model that everything
else is built from, and CI runs the browser-against-Python parity tests on it. Regenerate
the fixtures those tests compare against whenever it changes. Then re-run the evaluation,
which rewrites `docs/results.md`, and copy what changed into the README:

```bash
uv run --group train poe eval
```

The test splits are scored once per released model, not during development.

## The Python package

1. Bump `version` in `packages/core/pyproject.toml`.
2. `uv build --package schwa-az --out-dir dist`
3. Check the wheel in a clean environment:
   ```bash
   uv run --no-project --with "dist/schwa_az-<version>-py3-none-any.whl[onnx]" \
     python -c "from schwa import restore; print(restore('sence neden'))"
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

The demo is a static site: the model runs in the visitor's browser, so there is nothing to
host but files. It lives on GitHub Pages, served from the `gh-pages` branch.

```bash
cd apps/extension && npm run vendor           # model + runtime, if not already there
cd ../web && NEXT_PUBLIC_BASE_PATH=/schwa npm run build
# publish apps/web/out, plus an empty .nojekyll, as the gh-pages branch
```

`.nojekyll` matters: without it Pages runs Jekyll, which drops every folder starting with an
underscore — including `_next`, where all the page's code lives.

After publishing, check that the model files come back at their full size
(`model/tagger.onnx` is 2,345,956 bytes). A binary mangled on the way would load, fail
quietly, and leave the page stuck on "loading the model".

## The service

The optional HTTP service picks its restorer from `SCHWA_TAGGER` and `SCHWA_LEXICON`.
`/v1/info` reports which one is loaded, so after every deployment that endpoint is the check:
if it says `lexicon` where it should say `hybrid`, the model did not make it into the image.

## After releasing

- Tag the commit: `git tag v<version> && git push --tags`.
- Note what changed in `CHANGELOG.md`, in a sentence a user would care about.
