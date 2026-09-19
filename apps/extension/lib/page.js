/**
 * The functions the extension runs inside a page, and nowhere else.
 *
 * chrome.scripting sends each one to the tab as source text, so every function here has to
 * stand on its own: no imports, no outer variables, only the page's own DOM.
 *
 * Both follow what the person is doing. With text selected, they work on the selection.
 * With nothing selected, they work on the whole field being typed in - a plain input or
 * textarea, or an editor built on contenteditable, which is what WhatsApp Web, Gmail and most
 * chat boxes are.
 */

/** The text to restore: the selection, or all of the field in focus. */
export function collectText() {
  const active = document.activeElement;
  const isField = active instanceof HTMLInputElement || active instanceof HTMLTextAreaElement;

  if (isField) {
    const { selectionStart, selectionEnd, value } = active;
    const hasSelection = selectionStart !== selectionEnd;
    return hasSelection ? value.slice(selectionStart, selectionEnd) : value;
  }

  const selection = window.getSelection();
  if (selection && !selection.isCollapsed) return selection.toString();
  if (active instanceof HTMLElement && active.isContentEditable) return active.innerText;
  return "";
}

/** Put the restored text where collectText found the original; false if the page refused. */
export function replaceText(restored) {
  const active = document.activeElement;
  const isField = active instanceof HTMLInputElement || active instanceof HTMLTextAreaElement;

  if (isField) {
    const { selectionStart, selectionEnd, value } = active;
    const whole = selectionStart === selectionEnd;
    const start = whole ? 0 : selectionStart;
    const end = whole ? value.length : selectionEnd;
    active.setSelectionRange(start, end);
    // insertText goes through the browser's own editing path, so the page sees real input
    // events and Ctrl+Z still undoes the change.
    if (!document.execCommand("insertText", false, restored)) {
      active.value = value.slice(0, start) + restored + value.slice(end);
      active.dispatchEvent(new Event("input", { bubbles: true }));
    }
    return true;
  }

  const selection = window.getSelection();
  if (!selection) return false;
  if (selection.isCollapsed) {
    if (!(active instanceof HTMLElement && active.isContentEditable)) return false;
    // Nothing selected in an editor: take in everything typed there, as a field would.
    const range = document.createRange();
    range.selectNodeContents(active);
    selection.removeAllRanges();
    selection.addRange(range);
  }
  // An editor's text lives in its own model as well as in the page, so it is changed only
  // through the editing command, never behind the editor's back. If the editor refuses the
  // command, the refusal is reported rather than worked around.
  return document.execCommand("insertText", false, restored);
}

/** A short note in the corner of the page, gone after two seconds. */
export function showToast(message) {
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
