/**
 * The packed extension, in a real Chrome, restoring text with its own model.
 *
 * Every other test checks the pieces. This one checks that they come together where it
 * counts: the service worker has to load onnxruntime, open the model and answer. It once
 * could not - a service worker may not import() at run time - and nothing else noticed,
 * because the extension quietly fell back to a service nobody was running.
 *
 * Needs a Chrome: CHROME names one, or the usual install path is tried. Run with
 * `npm run vendor && npm run pack && npm run e2e`.
 */

import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const packed = join(here, "..", "dist", "schwa-extension");

const chrome = [
  process.env.CHROME,
  "/usr/bin/google-chrome",
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
].find((path) => path && existsSync(path));

test(
  "the packed extension restores text in Chrome with its own model",
  { skip: !chrome ? "no Chrome found" : !existsSync(packed) ? "run npm run pack" : false },
  async () => {
    const { default: puppeteer } = await import("puppeteer-core");
    const browser = await puppeteer.launch({
      executablePath: chrome,
      headless: true,
      pipe: true,
      enableExtensions: true,
      args: ["--no-sandbox"],
    });

    try {
      const id = await browser.installExtension(packed);
      const page = await browser.newPage();
      await page.goto(`chrome-extension://${id}/popup.html`);
      await page.type("#text", "sence neden basliyaq, TEBRIK EDIREM");
      await page.click("#fix");
      await page.waitForFunction(
        () => !["", "…"].includes(document.querySelector("#status").textContent),
        { timeout: 60000 },
      );

      const status = await page.$eval("#status", (element) => element.textContent);
      const restored = await page.$eval("#text", (element) => element.value);
      assert.equal(restored, "səncə nədən başlıyaq, TƏBRİK EDİRƏM", `status: ${status}`);
    } finally {
      await browser.close();
    }
  },
);
