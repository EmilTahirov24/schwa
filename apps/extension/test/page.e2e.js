/**
 * What the extension does inside a page, in a real Chrome: find the text, put the restored
 * text back.
 *
 * Chrome grants the extension a tab only after a real gesture - the shortcut or the context
 * menu - which a test cannot make. So these tests run the two page functions the way
 * chrome.scripting does, as source sent into a page, and check the part that can go wrong:
 * which text is taken, what replaces it, and that the page and its undo stack see a real
 * edit.
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

test("with nothing selected in a field, the whole field is restored", options, async () => {
  await open(`<textarea id="box">${TYPED}</textarea>`);
  await page.evaluate(() => document.querySelector("#box").setSelectionRange(5, 5));

  assert.equal(await page.evaluate(collectText), TYPED);
  await page.evaluate(replaceText, RESTORED);
  assert.equal(await page.$eval("#box", (box) => box.value), RESTORED);
});

test("Ctrl+Z undoes the restoration, as it would any edit", options, async () => {
  await open(`<textarea id="box">${TYPED}</textarea>`);
  await page.evaluate(replaceText, RESTORED);
  await page.keyboard.down("Control");
  await page.keyboard.press("KeyZ");
  await page.keyboard.up("Control");
  assert.equal(await page.$eval("#box", (box) => box.value), TYPED);
});

test("with part of a field selected, only that part is restored", options, async () => {
  await open(`<input id="box" value="${TYPED}">`);
  await page.evaluate(() => document.querySelector("#box").setSelectionRange(6, 11));

  assert.equal(await page.evaluate(collectText), "neden");
  await page.evaluate(replaceText, "nədən");
  assert.equal(await page.$eval("#box", (box) => box.value), "sence nədən basliyaq");
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
  await page.evaluate(replaceText, RESTORED);
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
  await page.evaluate(replaceText, RESTORED);
  assert.equal(await page.$eval("#box", (box) => box.value), RESTORED);
  assert.equal(await page.evaluate(() => window.heard), true);
});

test("with nothing selected in a chat-style editor, everything typed there is restored", options, async () => {
  await open(`<div id="box" contenteditable="true">${TYPED}</div>`);

  assert.equal(await page.evaluate(collectText), TYPED);
  await page.evaluate(replaceText, RESTORED);
  assert.equal(await page.$eval("#box", (box) => box.innerText), RESTORED);
});

test("with part of an editor selected, only that part is restored", options, async () => {
  await open(`<div id="box" contenteditable="true">${TYPED}</div>`);
  await page.evaluate(() => {
    const text = document.querySelector("#box").firstChild;
    const range = document.createRange();
    range.setStart(text, 6);
    range.setEnd(text, 11);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
  });

  assert.equal(await page.evaluate(collectText), "neden");
  await page.evaluate(replaceText, "nədən");
  assert.equal(await page.$eval("#box", (box) => box.innerText), "sence nədən basliyaq");
});

test("an editor that refuses the edit is reported, not silently ignored", options, async () => {
  await open(`<div id="box" contenteditable="true">${TYPED}</div>`);
  await page.evaluate(() => {
    document.execCommand = () => false;
  });
  assert.equal(await page.evaluate(replaceText, RESTORED), false);
});

test("a successful replacement says so", options, async () => {
  await open(`<div id="box" contenteditable="true">${TYPED}</div>`);
  assert.equal(await page.evaluate(replaceText, RESTORED), true);
});

test("with no field in focus and nothing selected, there is nothing to take", options, async () => {
  await open(`<p>${TYPED}</p><span id="box"></span>`);
  assert.equal(await page.evaluate(collectText), "");
});
