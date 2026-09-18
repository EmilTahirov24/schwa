# Chrome Web Store listing

Everything the submission form asks for, ready to paste. The store requires a single purpose
statement and a justification for every permission; vague answers are the usual reason a
review stalls, so each one below names the exact feature it serves.

## Name

Schwa — Azerbaijani diacritics

## Short description (132 characters)

Restores Azerbaijani letters in text typed without them: sence neden → səncə nədən. Works
offline, nothing is sent anywhere.

## Detailed description

Azerbaijani has seven letters a plain keyboard cannot produce — ç ə ğ ı ö ş ü — so people
drop them and write "sence" where they mean "səncə". This extension puts them back.

Select text and use the context menu, or press Ctrl+Shift+E in the field you are writing in.
The text is replaced in place, and Ctrl+Z undoes it like any other edit.

Putting the letters back is not a simple lookup. "qiz" can be "qız" or "qiz", and only the
surrounding words decide which. The extension carries a character-level model trained on
2.9 million sentences of Azerbaijani; on held-out text it gets 93.8% of the genuinely
ambiguous words right, against 79.2% for a dictionary that always picks the most common
spelling.

The model runs inside your browser. Your text is not sent to any server, and the extension
works with no connection at all.

Open source: https://github.com/EmilTahirov24/schwa

## Single purpose

Restoring missing Azerbaijani diacritics in text the user selects or is typing.

## Permission justifications

- **activeTab** — the extension reads and replaces text only in the tab the user invoked it
  on, at the moment they invoke it.
- **scripting** — used to inject the two functions that read the selected text and put the
  restored text back. There is no content script, so nothing runs on a page otherwise.
- **contextMenus** — adds the "Azərbaycan hərflərini düzəlt" item on selected or editable
  text, which is one of the two ways to use the extension.
- **storage** — stores two settings: whether to run the model locally, and the address of the
  optional service.
- **Host permission (the service address)** — used only in fallback mode, when the user turns
  local processing off or no model is bundled. In the default configuration it is never
  contacted.

## Data usage disclosures

- Does the extension collect personally identifiable information? **No.**
- Health, financial, authentication, personal communications, location, web history, user
  activity, website content? **No** — text is processed in the browser and is not transmitted
  or stored. In fallback mode the selected text is sent to the configured service for the
  length of one request and is not stored there either.
- Is data sold to third parties? **No.**
- Is data used for purposes unrelated to the single purpose? **No.**
- Is data used to determine creditworthiness or for lending? **No.**

## Privacy policy URL

`<demo domain>/privacy` — the page is in `apps/web/src/app/privacy`.

## Category and language

Category: Productivity. Language: Azerbaijani.

## Screenshots to take (1280×800)

1. The extension fixing a message in a real chat, before and after.
2. The context menu open on selected text.
3. The popup with text restored and "N söz dəyişdi" shown.
4. The options page, with local processing on.

## Before submitting

- `npm run vendor` has copied the model in, and the folder loads unpacked without errors.
- The version in `manifest.json` matches the release tag.
- Icons are in place (16, 32, 48, 128).
- The privacy page is reachable at a public URL.
