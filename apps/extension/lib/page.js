/**
 * The functions the extension runs inside a page, and nowhere else.
 *
 * chrome.scripting sends each one to the tab as source text, so every function here has to
 * stand on its own: no imports, no outer variables, only the page's own DOM. What collectText
 * finds, it leaves on the global object for replaceText. Under chrome.scripting that is the
 * extension's own isolated world, which the page cannot see.
 *
 * Both follow what the person is doing. With text selected, they work on the selection.
 * With nothing selected, they work on the whole field being typed in - a plain input or
 * textarea, or an editor built on contenteditable, which is what WhatsApp Web, Gmail and most
 * chat boxes are.
 */

/**
 * The text to restore - the selection, or all of the field in focus - and whether it can be
 * put back. Password fields are never read.
 */
export function collectText() {
  // An editor's text as the model should read it: its visible, editable text nodes in order,
  // with a line break wherever a new line or an image comes between two of them, so that
  // words the reader sees apart are never read as one. `at` is where each node's text
  // starts in `text`.
  function walk(root) {
    const blocks = new Map();
    const blockOf = (element) => {
      if (!blocks.has(element)) {
        const display = getComputedStyle(element).display;
        const inline = display.startsWith("inline") || display === "contents";
        blocks.set(element, element === root || !inline ? element : blockOf(element.parentElement));
      }
      return blocks.get(element);
    };

    const pieces = [];
    let text = "";
    let block = null;
    let broken = false;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      if (node.nodeType === Node.ELEMENT_NODE) {
        broken ||= node.tagName === "BR" || node.tagName === "IMG";
        continue;
      }
      const parent = node.parentElement;
      if (!node.data || !parent.isContentEditable || parent.getClientRects().length === 0) continue;
      if (pieces.length && (broken || blockOf(parent) !== block)) text += "\n";
      pieces.push({ node, at: text.length });
      text += node.data;
      block = blockOf(parent);
      broken = false;
    }
    return { pieces, text };
  }

  // Where a point in the page falls in the walked text.
  function offsetIn({ pieces, text }, container, offset) {
    const piece = pieces.find((candidate) => candidate.node === container);
    if (piece) return piece.at + offset;
    const point = document.createRange();
    point.setStart(container, offset);
    const next = pieces.find((candidate) => point.comparePoint(candidate.node, 0) >= 0);
    return next ? next.at : text.length;
  }

  delete globalThis.__schwa;
  const nothing = { text: "", editable: false };
  const active = document.activeElement;

  const isField =
    active instanceof HTMLTextAreaElement ||
    (active instanceof HTMLInputElement && (active.type === "text" || active.type === "search"));
  if (isField) {
    const { selectionStart, selectionEnd, value } = active;
    const whole = selectionStart === selectionEnd;
    const start = whole ? 0 : selectionStart;
    const end = whole ? value.length : selectionEnd;
    const target = {
      field: active,
      value,
      start,
      end,
      caret: whole ? selectionStart : null,
      text: value.slice(start, end),
      editable: !active.readOnly && !active.disabled,
    };
    globalThis.__schwa = target;
    return { text: target.text, editable: target.editable };
  }

  const selection = window.getSelection();
  const selected = Boolean(selection && !selection.isCollapsed);
  let root;
  if (selected) {
    const common = selection.getRangeAt(0).commonAncestorContainer;
    root = common.nodeType === Node.ELEMENT_NODE ? common : common.parentElement;
    if (!root?.isContentEditable) return { text: selection.toString(), editable: false };
    while (root.parentElement?.isContentEditable) root = root.parentElement;
  } else if (active instanceof HTMLElement && active.isContentEditable) {
    root = active;
  } else {
    return nothing;
  }

  const found = walk(root);
  let start = 0;
  let end = found.text.length;
  let caret = null;
  if (selected) {
    const range = selection.getRangeAt(0);
    start = offsetIn(found, range.startContainer, range.startOffset);
    end = offsetIn(found, range.endContainer, range.endOffset);
  } else if (selection?.rangeCount && root.contains(selection.anchorNode)) {
    caret = offsetIn(found, selection.anchorNode, selection.anchorOffset);
  }

  const text = found.text.slice(start, end);
  globalThis.__schwa = { root, walk, start, selected, caret, text, editable: true };
  return { text, editable: true };
}

/**
 * Put the restored text where collectText found the original: "done", "changed" if the text
 * changed in the meantime, or "refused" if the page would not take the edit.
 */
export function replaceText(restored) {
  const target = globalThis.__schwa;
  delete globalThis.__schwa;
  if (!target?.editable || restored.length !== target.text.length) return "refused";

  if (target.field) {
    const { field, value, start, end, caret } = target;
    if (!field.isConnected || field.value !== value) return "changed";
    field.setSelectionRange(start, end);
    // insertText goes through the browser's own editing path, so the page sees real input
    // events and Ctrl+Z still undoes the change.
    if (!document.execCommand("insertText", false, restored)) {
      field.value = value.slice(0, start) + restored + value.slice(end);
      field.dispatchEvent(new Event("input", { bubbles: true }));
    }
    if (caret === null) field.setSelectionRange(start, end);
    else field.setSelectionRange(caret, caret);
    return "done";
  }

  const { root, walk, start, selected, caret, text } = target;
  let found = walk(root);
  if (!root.isConnected || found.text.slice(start, start + text.length) !== text) return "changed";
  const pieceAt = (offset) => found.pieces.findLast((piece) => piece.at <= offset);

  // One edit per text node, from its first changed letter to its last. A text node has one
  // format throughout, so nothing is lost inside it, and nothing between the nodes -
  // formatting, links, emoji drawn as images, the lines themselves - is touched at all.
  const edits = [];
  for (const { node, at } of found.pieces) {
    const from = Math.max(at, start) - start;
    const to = Math.min(at + node.data.length, start + text.length) - start;
    let first = -1;
    let last = -1;
    for (let i = from; i < to; i += 1) {
      if (restored[i] === text[i]) continue;
      if (first < 0) first = i;
      last = i + 1;
    }
    if (first >= 0) edits.push([first, last]);
  }

  const selection = window.getSelection();
  for (const [first, last] of edits) {
    // An editor may redraw its text after an edit; the offsets still hold, because a
    // restoration never changes the length of anything.
    if (!pieceAt(start + first).node.isConnected) found = walk(root);
    const { node, at } = pieceAt(start + first);
    const offset = start + first - at;
    if (node.data.slice(offset, offset + last - first) !== text.slice(first, last)) return "changed";

    const range = document.createRange();
    range.setStart(node, offset);
    range.setEnd(node, offset + last - first);
    selection.removeAllRanges();
    selection.addRange(range);
    // The same editing path as a person typing over a selected word: the editor sees real
    // input events, and Ctrl+Z undoes it.
    if (!document.execCommand("insertText", false, restored.slice(first, last))) return "refused";
  }

  // Leave the cursor, or the selection, where it was.
  found = walk(root);
  const point = (offset) => {
    const { node, at } = pieceAt(offset);
    return [node, Math.min(offset - at, node.data.length)];
  };
  if (found.pieces.length && (selected || caret !== null)) {
    const range = document.createRange();
    range.setStart(...point(selected ? start : caret));
    if (selected) range.setEnd(...point(start + text.length));
    selection.removeAllRanges();
    selection.addRange(range);
  }
  return "done";
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
