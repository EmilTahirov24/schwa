/**
 * The extension's only long-lived piece.
 *
 * Nothing runs on any page until you ask for it. There is no content script in the
 * manifest and no permission for any site: when you pick the context menu item or press
 * the shortcut, the two small functions below are injected into that one tab under
 * activeTab, they do their work, and they are gone. The model is packaged with the
 * extension, so the text is restored right here and never leaves the browser.
 */

import { changesBetween } from "./lib/changes.js";
import { localTagger } from "./lib/local.js";
import { collectText, replaceText, showToast } from "./lib/page.js";
// The self-contained build: a service worker may not import() anything at run time.
import * as ort from "./vendor/ort.wasm.bundle.min.mjs";

const MENU_ID = "schwa-fix-selection";

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: MENU_ID,
    title: "Azərbaycan hərflərini düzəlt",
    contexts: ["selection", "editable"],
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === MENU_ID && tab?.id !== undefined) {
    void fixTab(tab.id);
  }
});

chrome.commands.onCommand.addListener((command, tab) => {
  if (command === "fix-field" && tab?.id !== undefined) {
    void fixTab(tab.id);
  }
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "restore") {
    restore(message.text)
      .then((result) => sendResponse({ ok: true, ...result }))
      .catch((error) => sendResponse({ ok: false, error: String(error.message ?? error) }));
    return true; // keep the channel open for the async reply
  }
  return false;
});

/** Restore text with the model packaged in the extension. */
async function restore(text) {
  const restorer = await localTagger(ort);
  if (!restorer) throw new Error("model yüklənmədi");
  const restored = await restorer.restore(text);
  return { text: restored, changes: changesBetween(text, restored) };
}

async function fixTab(tabId) {
  const [collected] = await chrome.scripting.executeScript({
    target: { tabId },
    func: collectText,
  });

  const text = collected?.result;
  if (!text) {
    await flash(tabId, "Seçilmiş mətn yoxdur");
    return;
  }

  let restored;
  try {
    restored = (await restore(text)).text;
  } catch (error) {
    await flash(tabId, `Xəta: ${error.message ?? error}`);
    return;
  }

  if (restored === text) {
    await flash(tabId, "Dəyişiklik yoxdur");
    return;
  }

  const [replaced] = await chrome.scripting.executeScript({
    target: { tabId },
    func: replaceText,
    args: [restored],
  });
  if (!replaced?.result) {
    await flash(tabId, "Bu redaktor dəyişikliyi qəbul etmədi");
  }
}

async function flash(tabId, message) {
  await chrome.scripting.executeScript({ target: { tabId }, func: showToast, args: [message] });
}
