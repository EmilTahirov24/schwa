/**
 * The extension's only long-lived piece.
 *
 * Nothing runs on any page until you ask for it. There is no content script in the
 * manifest and no permission for any site: when you pick the context menu item or press
 * the shortcut, the two small functions below are injected into that one tab under
 * activeTab, they do their work, and they are gone. Text leaves the browser only at that
 * moment, and only to the service you configured.
 */

const DEFAULT_API = "http://127.0.0.1:8000";
const MENU_ID = "duzelt-fix-selection";

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

async function settings() {
  const stored = await chrome.storage.sync.get({ apiUrl: DEFAULT_API });
  return { apiUrl: stored.apiUrl.replace(/\/$/, "") };
}

async function restore(text) {
  const { apiUrl } = await settings();
  const response = await fetch(`${apiUrl}/v1/restore`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });

  if (!response.ok) {
    throw new Error(response.status === 429 ? "too many requests" : `service said ${response.status}`);
  }

  return response.json();
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

  await chrome.scripting.executeScript({
    target: { tabId },
    func: replaceText,
    args: [restored],
  });
}

async function flash(tabId, message) {
  await chrome.scripting.executeScript({ target: { tabId }, func: showToast, args: [message] });
}

/* The three functions below run inside the page, not here. */

function collectText() {
  const active = document.activeElement;
  const isField =
    active instanceof HTMLInputElement || active instanceof HTMLTextAreaElement;

  if (isField) {
    const { selectionStart, selectionEnd, value } = active;
    const hasSelection = selectionStart !== selectionEnd;
    return hasSelection ? value.slice(selectionStart, selectionEnd) : value;
  }

  return window.getSelection()?.toString() ?? "";
}

function replaceText(restored) {
  const active = document.activeElement;
  const isField =
    active instanceof HTMLInputElement || active instanceof HTMLTextAreaElement;

  if (isField) {
    const { selectionStart, selectionEnd, value } = active;
    if (selectionStart === selectionEnd) active.setSelectionRange(0, value.length);
    // insertText goes through the browser's own editing path, so the page sees real
    // input events and Ctrl+Z still undoes the change.
    if (!document.execCommand("insertText", false, restored)) {
      const start = selectionStart ?? 0;
      const end = selectionEnd ?? value.length;
      active.value = value.slice(0, start) + restored + value.slice(end);
      active.dispatchEvent(new Event("input", { bubbles: true }));
    }
    return;
  }

  const selection = window.getSelection();
  if (selection && selection.rangeCount > 0 && !selection.isCollapsed) {
    document.execCommand("insertText", false, restored);
  }
}

function showToast(message) {
  const toast = document.createElement("div");
  toast.textContent = message;
  toast.style.cssText = [
    "position:fixed",
    "bottom:20px",
    "right:20px",
    "z-index:2147483647",
    "padding:10px 14px",
    "border-radius:8px",
    "background:#171717",
    "color:#fafafa",
    "font:14px system-ui,sans-serif",
    "box-shadow:0 4px 16px rgba(0,0,0,.25)",
  ].join(";");

  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 2200);
}
