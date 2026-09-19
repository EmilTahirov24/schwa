/**
 * What the extension does inside a page, in a real Chrome: find the text, put the restored
 * text back.
 *
 * Chrome grants the extension a tab only after a real gesture - the shortcut or the context
 * menu - which a test cannot make. So these tests run the two page functions the way
 * chrome.scripting does, as source sent into a page, and check the part that can go wrong:
 * which text is taken, what replaces it, what is left alone, and that the page and its undo
 * stack see a real edit.
 *
 * Needs a Chrome: CHROME names one, or the usual install path is tried.
 */

import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { after, before, test } from "node:test";

import { collectText, replaceText } from "../lib/page.js";

const chrome = [
  process.env.CHROME,
  "/usr/bin/google-chrome",
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
].find((path) => path && existsSync(path));

const TYPED = "sence neden basliyaq";
const RESTORED = "səncə nədən başlıyaq";

// Stands in for the model, which these tests are not about.
const WORDS = { sence: "səncə", neden: "nədən", basliyaq: "başlıyaq" };
const restoreWords = (text) => text.replace(/\p{L}+/gu, (word) => WORDS[word] ?? word);

// A one-pixel image, the way Gmail and WhatsApp Web draw an emoji inside what you type.
const EMOJI = `<img alt="🙂" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7">`;

let browser;
let page;

before(async () => {
  if (!chrome) return;
  const { default: puppeteer } = await import("puppeteer-core");
  browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ["--no-sandbox"] });
});

after(async () => {
  await browser?.close();
});

const options = { skip: chrome ? false : "no Chrome found" };

/** A fresh page - nothing a previous test did to it survives - with #box focused. */
async function open(html) {
  await page?.close();
  page = await browser.newPage();
  await page.setContent(`<!doctype html><body>${html}</body>`);
  await page.focus("#box");
}

/** What the shortcut does: take the text, restore it, put it back. */
async function restoreOnPage() {
  const found = await page.evaluate(collectText);
  const outcome = found.editable ? await page.evaluate(replaceText, restoreWords(found.text)) : null;
  return { ...found, outcome };
}

/** Select from one text node to another, each named by a selector and an offset. */
async function select(from, fromOffset, to, toOffset) {
  await page.evaluate(
    (from, fromOffset, to, toOffset) => {
      const text = (selector) => {
        const element = document.querySelector(selector);
        return [...element.childNodes].find((node) => node.nodeType === Node.TEXT_NODE);
      };
      const range = document.createRange();
      range.setStart(text(from), fromOffset);
      range.setEnd(text(to), toOffset);
      window.getSelection().removeAllRanges();
      window.getSelection().addRange(range);
    },
    from,
    fromOffset,
    to,
    toOffset,
  );
}

const html = (selector = "#box") => page.$eval(selector, (element) => element.innerHTML);
const value = () => page.$eval("#box", (box) => box.value);

test("with nothing selected in a field, the whole field is restored", options, async () => {
  await open(`<textarea id="box">${TYPED}</textarea>`);
  await page.evaluate(() => document.querySelector("#box").setSelectionRange(5, 5));

  const { text, outcome } = await restoreOnPage();
  assert.equal(text, TYPED);
  assert.equal(outcome, "done");
  assert.equal(await value(), RESTORED);
});

test("the cursor stays where it was in a field", options, async () => {
  await open(`<textarea id="box">${TYPED}</textarea>`);
  await page.evaluate(() => document.querySelector("#box").setSelectionRange(5, 5));
  await restoreOnPage();
  assert.deepEqual(
    await page.$eval("#box", (box) => [box.selectionStart, box.selectionEnd]),
    [5, 5],
  );
});

test("Ctrl+Z undoes the restoration, as it would any edit", options, async () => {
  await open(`<textarea id="box">${TYPED}</textarea>`);
  await restoreOnPage();
  await page.keyboard.down("Control");
  await page.keyboard.press("KeyZ");
  await page.keyboard.up("Control");
  assert.equal(await value(), TYPED);
});

test("with part of a field selected, only that part is restored", options, async () => {
  await open(`<input id="box" value="${TYPED}">`);
  await page.evaluate(() => document.querySelector("#box").setSelectionRange(6, 11));

  const { text } = await restoreOnPage();
  assert.equal(text, "neden");
  assert.equal(await value(), "sence nədən basliyaq");
});

test("a field the page keeps in its own state hears about the change", options, async () => {
  // What React does: the page's copy of the value moves only when an input event says so.
  await open(`<input id="box" value="${TYPED}">
    <script>
      window.state = document.querySelector("#box").value;
      document.querySelector("#box").addEventListener("input", (event) => {
        window.state = event.target.value;
      });
    </script>`);
  await restoreOnPage();
  assert.equal(await page.evaluate(() => window.state), RESTORED);
});

test("where the editing command is refused, the fallback still replaces the whole field", options, async () => {
  await open(`<textarea id="box">${TYPED}</textarea>
    <script>
      window.heard = false;
      document.querySelector("#box").addEventListener("input", () => (window.heard = true));
    </script>`);
  await page.evaluate(() => {
    document.querySelector("#box").setSelectionRange(5, 5);
    document.execCommand = () => false;
  });
  assert.equal((await restoreOnPage()).outcome, "done");
  assert.equal(await value(), RESTORED);
  assert.equal(await page.evaluate(() => window.heard), true);
});

test("a password is never read", options, async () => {
  await open(`<input id="box" type="password" value="${TYPED}">`);
  assert.deepEqual(await page.evaluate(collectText), { text: "", editable: false });
});

test("text that cannot be edited is read but never changed", options, async () => {
  await open(`<textarea id="box" readonly>${TYPED}</textarea>`);
  assert.deepEqual(await restoreOnPage(), { text: TYPED, editable: false, outcome: null });
  assert.equal(await page.evaluate(replaceText, RESTORED), "refused");
  assert.equal(await value(), TYPED);

  await open(`<p id="words">${TYPED}</p><button id="box">ok</button>`);
  await select("#words", 0, "#words", 5);
  assert.deepEqual(await restoreOnPage(), { text: "sence", editable: false, outcome: null });
});

test("with nothing selected in a chat-style editor, everything typed there is restored", options, async () => {
  await open(`<div id="box" contenteditable="true">${TYPED}</div>`);

  const { text, outcome } = await restoreOnPage();
  assert.equal(text, TYPED);
  assert.equal(outcome, "done");
  assert.equal(await html(), RESTORED);
});

test("Ctrl+Z undoes the restoration in an editor too", options, async () => {
  await open(`<div id="box" contenteditable="true">${TYPED}</div>`);
  await restoreOnPage();
  await page.keyboard.down("Control");
  await page.keyboard.press("KeyZ");
  await page.keyboard.up("Control");
  assert.equal(await html(), TYPED);
});

test("the cursor stays where it was in an editor", options, async () => {
  await open(`<div id="box" contenteditable="true">${TYPED}</div>`);
  await select("#box", 5, "#box", 5);
  await restoreOnPage();
  const caret = await page.evaluate(() => {
    const selection = window.getSelection();
    return { collapsed: selection.isCollapsed, text: selection.anchorNode.data, offset: selection.anchorOffset };
  });
  assert.deepEqual(caret, { collapsed: true, text: RESTORED, offset: 5 });
});

test("formatting and links around the words stay exactly as they were", options, async () => {
  await open(`<div id="box" contenteditable="true">sence <b>neden</b> <a href="#x">basliyaq</a></div>`);
  await restoreOnPage();
  assert.equal(await html(), `səncə <b>nədən</b> <a href="#x">başlıyaq</a>`);
});

test("an emoji drawn as an image is kept, and words either side of it stay apart", options, async () => {
  await open(`<div id="box" contenteditable="true">sence${EMOJI}neden</div>`);
  const { text } = await restoreOnPage();
  assert.equal(text, "sence\nneden");
  assert.equal(await html(), `səncə${EMOJI}nədən`);
});

test("words on different lines are read apart and each line stays a line", options, async () => {
  await open(`<div id="box" contenteditable="true"><p>sence</p><p>neden<br>basliyaq</p></div>`);
  const { text } = await restoreOnPage();
  assert.equal(text, "sence\nneden\nbasliyaq");
  assert.equal(await html(), `<p>səncə</p><p>nədən<br>başlıyaq</p>`);
});

test("hidden text, and parts the editor locks, are left alone", options, async () => {
  const hidden = `<span style="display:none">neden</span><span contenteditable="false">neden</span>`;
  await open(`<div id="box" contenteditable="true">sence ${hidden} basliyaq</div>`);
  const { text } = await restoreOnPage();
  assert.equal(text, "sence  basliyaq");
  assert.equal(await html(), `səncə ${hidden} başlıyaq`);
});

test("an editor that redraws its text after every edit still gets every word", options, async () => {
  // Editors that keep their own model - Lexical, which WhatsApp Web uses, among them - may
  // put fresh nodes in place of the ones an edit touched.
  await open(`<div id="box" contenteditable="true">sence <b>neden</b> <i>basliyaq</i></div>
    <script>
      const box = document.querySelector("#box");
      box.addEventListener("input", () => (box.innerHTML = box.innerHTML));
    </script>`);
  assert.equal((await restoreOnPage()).outcome, "done");
  assert.equal(await html(), `səncə <b>nədən</b> <i>başlıyaq</i>`);
});

test("with part of an editor selected, only that part is restored and stays selected", options, async () => {
  await open(`<div id="box" contenteditable="true">sence <b>neden</b> basliyaq</div>`);
  await select("#box", 0, "#box b", 5);

  const { text } = await restoreOnPage();
  assert.equal(text, "sence neden");
  assert.equal(await html(), `səncə <b>nədən</b> basliyaq`);
  assert.equal(await page.evaluate(() => window.getSelection().toString()), "səncə nədən");
});

test("text that changed while the model was working is not overwritten", options, async () => {
  await open(`<div id="box" contenteditable="true">${TYPED}</div>`);
  const { text } = await page.evaluate(collectText);
  await page.evaluate(() => (document.querySelector("#box").firstChild.data = "sence neden gelirem"));

  assert.equal(await page.evaluate(replaceText, restoreWords(text)), "changed");
  assert.equal(await html(), "sence neden gelirem");
});

test("an editor that refuses the edit is reported, not silently ignored", options, async () => {
  await open(`<div id="box" contenteditable="true">${TYPED}</div>`);
  await page.evaluate(() => {
    document.execCommand = () => false;
  });
  assert.equal((await restoreOnPage()).outcome, "refused");
});

test("a restoration that is not the same length as the text is refused", options, async () => {
  await open(`<div id="box" contenteditable="true">${TYPED}</div>`);
  await page.evaluate(collectText);
  assert.equal(await page.evaluate(replaceText, "səncə"), "refused");
  assert.equal(await html(), TYPED);
});

test("with no field in focus and nothing selected, there is nothing to take", options, async () => {
  await open(`<p>${TYPED}</p><span id="box"></span>`);
  assert.deepEqual(await page.evaluate(collectText), { text: "", editable: false });
});
