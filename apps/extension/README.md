# Schwa — browser extension

Restores Azerbaijani letters in whatever you are typing: select the text and use the context
menu, or press `Ctrl+Shift+E` in the field you are writing in.

## Where the work happens

By default, inside your browser. The extension carries the model, so the text you are
writing never leaves the tab — no server sees it, and it works with no connection at all.

If the model was not bundled, the extension falls back to the service, and the setting under
options lets you switch deliberately. The popup says which one answered.

## Install it while developing

```bash
cd apps/extension
npm install
npm run vendor     # copies onnxruntime and the model into the extension
npm test
```

`npm run vendor` looks for `models/tagger.int8.onnx` in the repository root — produced by
`scripts/export_onnx.py` and `scripts/quantize_onnx.py`. Without it the extension still
works, through the service.

Then open `chrome://extensions`, turn on developer mode, choose **Load unpacked**, and pick
this folder.

## What it is allowed to do

The manifest asks for `contextMenus`, `scripting`, `activeTab` and `storage`, and for one
host — the service address, used only in fallback mode. There is no content script and no
permission for any website.

That is deliberate. Nothing runs on a page until you invoke the extension; at that moment two
short functions are injected into that single tab, they read the text you pointed at, put the
restored text back, and are gone. The page cannot be read at any other time.

Replacements go through the browser's own editing path, so sites built on React — WhatsApp
Web, Instagram, Gmail — see real input events, and `Ctrl+Z` undoes the change.

## Why the alphabet code exists twice

`lib/alphabet.js` is a port of the Python module of the same name, because the model runs in
both places and the rules have to match exactly. The tests in `test/` check the same cases as
the Python tests, so the two cannot quietly drift apart — including the casing of `i`, `ı`,
`İ` and `I`, which JavaScript gets wrong for the same reason Python does.

## Not here yet

Icons, store listing material, and a Firefox build.
