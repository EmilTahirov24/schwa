/**
 * Put together the extension as it ships: the files Chrome loads, and nothing else.
 *
 * The development folder also holds node_modules, tests and scripts, and Chrome refuses to
 * load a folder with names that start with "_" in it. The release zip, the store upload and
 * the browser test all start from dist/schwa-extension instead.
 *
 *   npm run vendor && npm run pack
 */

import { cpSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const extension = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const out = join(extension, "dist", "schwa-extension");

const SHIPPED = [
  "manifest.json",
  "background.js",
  "popup.html",
  "popup.js",
  "lib",
  "icons",
  "vendor",
  "model",
];

for (const name of ["vendor", "model"]) {
  if (!existsSync(join(extension, name))) {
    console.error(`missing ${name}/; run npm run vendor first`);
    process.exit(1);
  }
}

rmSync(out, { recursive: true, force: true });
mkdirSync(out, { recursive: true });
for (const name of SHIPPED) {
  cpSync(join(extension, name), join(out, name), { recursive: true });
}
console.log(`packed -> ${out}`);
