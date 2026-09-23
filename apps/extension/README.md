# Schwa — browser extension

Restores Azerbaijani letters in whatever you are typing: select the text and use the context
menu, or press `Ctrl+Shift+E` in the field you are writing in.

With text selected, only the selection is restored. With nothing selected, everything in the
field is - a plain input, or an editor like WhatsApp Web's or Gmail's. Only the letters that
change are touched: bold, links, emoji and line breaks stay as they were, and so does the
cursor. Password fields are never read.

## Where the work happens

Inside your browser. The extension carries the model, so the text you are writing never
leaves the tab — no server sees it, and it works with no connection at all.

## Install it while developing

```bash
cd apps/extension
npm install
npm run vendor     # copies onnxruntime and the model into the extension
npm test
npm run pack       # the shipped files alone, in dist/schwa-extension
npm run e2e        # that folder in a real Chrome, restoring text with its own model
```

The model comes from the Python package's bundle in `packages/core/schwa/data`, which is
committed, so the package, the extension and the demo page always carry the same four files.
The integration test then checks that this folder answers exactly as the Python package does.

Then open `chrome://extensions`, turn on developer mode, choose **Load unpacked**, and pick
`dist/schwa-extension`.

## What it is allowed to do

The manifest asks for `contextMenus`, `scripting` and `activeTab`, and for nothing else: no
host, no storage, no content script, no permission for any website.

That is deliberate. Nothing runs on a page until you invoke the extension; at that moment two
short functions are injected into that single tab, they read the text you pointed at, put the
restored text back, and are gone. The page cannot be read at any other time.

Replacements go through the browser's own editing path, so sites built on React — WhatsApp
Web, Instagram, Gmail — see real input events, and `Ctrl+Z` undoes the change. In an editor,
each differently formatted stretch of text is its own edit, so there it may take a few
presses.

## Why the alphabet code exists twice

`lib/alphabet.js` is a port of the Python module of the same name, because the model runs in
both places and the rules have to match exactly. The tests in `test/` check the same cases as
the Python tests, so the two cannot quietly drift apart — including the casing of `i`, `ı`,
`İ` and `I`, which JavaScript gets wrong for the same reason Python does.

## Not here yet

- **Editors inside a frame.** Both functions are sent to the page's main frame, so an editor
  the site puts in its own `<iframe>` is not reached: the shortcut reports that there is
  nothing to restore. The context menu knows which frame was clicked, which is where a fix
  would start; a frame from another site would need a permission this extension does not ask
  for.
- The Chrome Web Store release — the listing text is in
  [docs/store-listing.md](../../docs/store-listing.md) — and a Firefox build.
