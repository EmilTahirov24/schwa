/**
 * Bring the in-browser restorer into the site.
 *
 * The page runs the same code the browser extension runs, so there is one implementation to
 * test instead of two. The extension owns it - its tests live there - and this copies it in,
 * together with the runtime and the model the extension's `npm run vendor` prepared.
 *
 * Nothing copied here is committed; it is all regenerated before every dev run and build.
 */

import { copyFileSync, existsSync, mkdirSync, readdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const web = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const extension = resolve(web, "..", "extension");

const COPIES = [
  [join(extension, "lib"), join(web, "src", "lib", "schwa"), (name) => name.endsWith(".js")],
  [join(extension, "vendor"), join(web, "public", "ort"), () => true],
  [join(extension, "model"), join(web, "public", "model"), () => true],
];

let copied = 0;

for (const [from, to, keep] of COPIES) {
  if (!existsSync(from)) {
    console.error(`missing ${from}\nrun "npm install && npm run vendor" in apps/extension first`);
    process.exit(1);
  }

  mkdirSync(to, { recursive: true });
  for (const name of readdirSync(from).filter(keep)) {
    copyFileSync(join(from, name), join(to, name));
    copied += 1;
  }
}

console.log(`${copied} files synced from the extension`);
