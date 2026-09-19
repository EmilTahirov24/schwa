/**
 * The Chrome Web Store images, drawn from the packed extension restoring real text.
 *
 * Every sentence shown restored is what the shipped model returned for it here, through the
 * extension's own popup - nothing is typed in by hand. The images go to docs/store.
 *
 *   npm run vendor && npm run pack && npm run store-images
 */

import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import puppeteer from "puppeteer-core";

const extension = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const packed = join(extension, "dist", "schwa-extension");
const out = resolve(extension, "..", "..", "docs", "store");
const chrome = [
  process.env.CHROME,
  "/usr/bin/google-chrome",
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
].find((path) => path && existsSync(path));

if (!chrome || !existsSync(packed)) {
  console.error(chrome ? "run npm run pack first" : "no Chrome found; set CHROME");
  process.exit(1);
}

const browser = await puppeteer.launch({
  executablePath: chrome,
  headless: true,
  pipe: true,
  enableExtensions: true,
  args: ["--no-sandbox"],
});

const id = await browser.installExtension(packed);
const popup = await browser.newPage();
await popup.emulateMediaFeatures([{ name: "prefers-color-scheme", value: "light" }]);
await popup.setViewport({ width: 320, height: 200, deviceScaleFactor: 2 });
await popup.goto(`chrome-extension://${id}/popup.html`);

/** What the extension makes of `typed`, through its popup. */
async function restore(typed) {
  await popup.$eval("#text", (box, value) => (box.value = value), typed);
  await popup.$eval("#status", (status) => (status.textContent = ""));
  await popup.click("#fix");
  await popup.waitForFunction(() => /söz|yoxdur/.test(document.querySelector("#status").textContent), {
    timeout: 60000,
  });
  return [typed, await popup.$eval("#text", (box) => box.value)];
}

const message = await restore("salam, sabah gorusek? men bu gun isde gec qalacam, axsam zeng edecem");
const question = await restore("sence neden basliyaq");
const thanks = await restore("cox sagol, her sey ucun minnetdaram");
// The popup, as the last restoration left it, is the second picture.
const popupPng = (await popup.screenshot({ fullPage: true, encoding: "base64" })).toString();

/** The restored text with every restored letter marked. */
function marked(typed, restored) {
  return [...restored]
    .map((char, i) => (char === [...typed][i] ? char : `<b>${char}</b>`))
    .join("");
}

const style = `
  * { box-sizing: border-box; margin: 0; }
  body { width: 1280px; height: 800px; font-family: "Segoe UI", system-ui, sans-serif;
         background: linear-gradient(135deg, #f0fdf4 0%, #ffffff 55%, #f5f5f4 100%); color: #171717;
         display: flex; flex-direction: column; padding: 64px 80px; gap: 40px; }
  .brand { display: flex; align-items: center; gap: 14px; font-size: 24px; font-weight: 600; }
  .logo { width: 48px; height: 48px; border-radius: 12px; background: #171717; color: #fff;
          display: flex; align-items: center; justify-content: center; font-size: 30px; }
  h1 { font-size: 52px; line-height: 1.1; letter-spacing: -0.02em; }
  h1 span { color: #059669; }
  .lead { font-size: 24px; color: #525252; max-width: 900px; line-height: 1.45; }
  kbd { font: 600 22px "Segoe UI", system-ui; padding: 4px 12px; border: 1px solid #d4d4d4;
        border-bottom-width: 3px; border-radius: 8px; background: #fff; }
  b { color: #047857; background: #d1fae5; border-radius: 4px; font-weight: 600; }
`;

const pages = {
  "1-before-after": `
    <div class="brand"><div class="logo">ə</div>Schwa</div>
    <h1>Hərfsiz yazdın? <span>Ctrl+Shift+E</span> bas.</h1>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:32px;flex:1">
      ${[
        ["Əvvəl", message[0]],
        ["Sonra", marked(message[0], message[1])],
      ]
        .map(
          ([label, text]) => `
        <div style="display:flex;flex-direction:column;gap:14px">
          <div style="font-size:18px;font-weight:600;color:#737373;text-transform:uppercase;letter-spacing:.08em">${label}</div>
          <div style="flex:1;border:1px solid #e5e5e5;border-radius:24px;background:#fafafa;padding:28px;display:flex;flex-direction:column;justify-content:flex-end;gap:18px;box-shadow:0 10px 30px rgba(0,0,0,.06)">
            <div style="align-self:flex-start;max-width:75%;background:#fff;border:1px solid #e5e5e5;border-radius:18px 18px 18px 4px;padding:14px 18px;font-size:20px;color:#404040">Salam! Necəsən?</div>
            <div style="align-self:flex-end;max-width:75%;background:#d1fae5;border-radius:18px 18px 4px 18px;padding:14px 18px;font-size:20px;color:#064e3b">Yaxşıyam, sən necəsən?</div>
            <div style="align-self:flex-start;max-width:75%;background:#fff;border:1px solid #e5e5e5;border-radius:18px 18px 18px 4px;padding:14px 18px;font-size:20px;color:#404040">Sabah boşsan? Görüşək.</div>
            <div style="border:1px solid #d4d4d4;border-radius:18px;background:#fff;padding:18px 20px;font-size:24px;line-height:1.45">${text}</div>
          </div>
        </div>`,
        )
        .join("")}
    </div>`,

  "2-popup": `
    <div class="brand"><div class="logo">ə</div>Schwa</div>
    <div style="display:flex;gap:64px;align-items:center;flex:1">
      <div style="flex:1;display:flex;flex-direction:column;gap:24px">
        <h1>Səhifədə sahə yoxdur?<br><span>Popup-a yapışdır.</span></h1>
        <p class="lead">Mətni yapışdır, <b style="background:none;color:#171717">Düzəlt</b> bas, kopyala. Hansı sözlərin dəyişdiyini də deyir.</p>
      </div>
      <img src="data:image/png;base64,${popupPng}" style="width:480px;border-radius:16px;box-shadow:0 24px 60px rgba(0,0,0,.18);border:1px solid #e5e5e5">
    </div>`,

  "3-private": `
    <div class="brand"><div class="logo">ə</div>Schwa</div>
    <h1>Model <span>brauzerin içindədir.</span></h1>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:28px">
      ${[
        ["🔒", "Heç yerə göndərilmir", "Yazdığın mətn sənin kompüterindən çıxmır: onu görən server yoxdur."],
        ["✈️", "İnternetsiz də işləyir", "2.3 MB-lıq model extension-un özündədir, heç nə yükləmir."],
        ["🛡️", "Heç bir sayta icazə yoxdur", "Yalnız sən çağıranda, yalnız o səhifədə işə düşür."],
      ]
        .map(
          ([icon, title, text]) => `
        <div style="border:1px solid #e5e5e5;border-radius:24px;background:#fff;padding:32px;display:flex;flex-direction:column;gap:14px;box-shadow:0 10px 30px rgba(0,0,0,.05)">
          <div style="font-size:40px">${icon}</div>
          <div style="font-size:26px;font-weight:600">${title}</div>
          <div style="font-size:20px;color:#525252;line-height:1.45">${text}</div>
        </div>`,
        )
        .join("")}
    </div>
    <p class="lead">Veb mətnində çoxmənalı sözlərin 95.7%-ni düzgün bərpa edir. Açıq mənbə: github.com/EmilTahirov24/schwa</p>`,
};

const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 800, deviceScaleFactor: 1 });
for (const [name, body] of Object.entries(pages)) {
  await page.setContent(`<!doctype html><html lang="az"><head><meta charset="utf-8"><style>${style}</style></head><body>${body}</body></html>`);
  await page.screenshot({ path: join(out, `${name}.png`) });
}

// The small promo tile.
await page.setViewport({ width: 440, height: 280, deviceScaleFactor: 1 });
await page.setContent(`<!doctype html><html lang="az"><head><meta charset="utf-8"><style>
  * { box-sizing: border-box; margin: 0; }
  body { width: 440px; height: 280px; font-family: "Segoe UI", system-ui, sans-serif; background: #171717; color: #fff;
         display: flex; flex-direction: column; justify-content: center; padding: 36px; gap: 16px; }
</style></head><body>
  <div style="display:flex;align-items:center;gap:12px;font-size:30px;font-weight:600">
    <div style="width:52px;height:52px;border-radius:12px;background:#fff;color:#171717;display:flex;align-items:center;justify-content:center;font-size:34px">ə</div>Schwa
  </div>
  <div style="font-size:22px;color:#d4d4d4;line-height:1.35">Azərbaycan hərflərini geri qaytarır</div>
  <div style="font-size:23px;font-family:Consolas,monospace;line-height:1.35"><div style="color:#a3a3a3">${question[0]}</div><div style="color:#34d399">→ ${question[1]}</div></div>
</body></html>`);
await page.screenshot({ path: join(out, "promo-small.png") });

await browser.close();
console.log("done");
