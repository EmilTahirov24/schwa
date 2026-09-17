# Düzəlt — browser extension

Restores Azerbaijani letters in whatever you are typing: select the text and use the context
menu, or press `Ctrl+Shift+E` in the field you are writing in.

## Install it while developing

1. Run the service: `uv run uvicorn duzelt_api.main:app` from the repository root.
2. Open `chrome://extensions`, turn on developer mode, choose **Load unpacked**, and pick
   this folder.
3. Set the service address under the extension's options if it is not the default.

## What it is allowed to do

The manifest asks for `contextMenus`, `scripting`, `activeTab` and `storage`, and for one
host — the service address. There is no content script and no permission for any website.

That is deliberate. Nothing runs on a page until you invoke the extension; at that moment
two short functions are injected into that single tab, they read the text you pointed at,
put the restored text back, and are gone. The page cannot be read at any other time, and
text leaves the browser only on that action, only to the service you configured, which does
not store it.

Replacements go through the browser's own editing path, so sites built on React — WhatsApp
Web, Instagram, Gmail — see real input events, and `Ctrl+Z` undoes the change.

## Not here yet

Icons, store listing material, and a Firefox build. The model itself is planned to move into
the extension later so that text never leaves the browser at all.
