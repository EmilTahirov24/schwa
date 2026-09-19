/**
 * Copy the runtime and the model into the extension folder.
 *
 * onnxruntime is 14 MB of third-party build output, fetched by npm, so it is copied here
 * rather than committed. The model comes from the Python package's bundle
 * (packages/core/schwa/data, written by scripts/build_bundle.py): the package, the
 * extension and the demo page all ship those same four files. `vendor/` and `model/` are
 * ignored by git.
 *
 *   npm run vendor
 */

import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const extension = resolve(here, "..");
const bundle = resolve(extension, "..", "..", "packages", "core", "schwa", "data");

const RUNTIME = [
  // The page loads this one when it needs it...
  "ort.wasm.min.mjs",
  // ...the extension's service worker imports this one, which carries its own loader.
  "ort.wasm.bundle.min.mjs",
  "ort-wasm-simd-threaded.mjs",
  "ort-wasm-simd-threaded.wasm",
];

const MODEL = [
  // The int8 tagger and its sidecar: alphabet and window settings.
  "tagger.onnx",
  "tagger.json",
  // The words the training text was unanimous about.
  "lexicon.tsv.gz",
  // The spell checker: every common word, and the endings that make rare forms plausible.
  "vocabulary.tsv.gz",
];

function copy(from, to) {
  mkdirSync(dirname(to), { recursive: true });
  copyFileSync(from, to);
}

for (const name of RUNTIME) {
  const from = join(extension, "node_modules", "onnxruntime-web", "dist", name);
  if (!existsSync(from)) {
    console.error(`missing ${name}; run npm install first`);
    process.exit(1);
  }
  copy(from, join(extension, "vendor", name));
}

for (const name of MODEL) {
  const from = join(bundle, name);
  if (!existsSync(from)) {
    console.error(`missing ${from}; run scripts/build_bundle.py in the repository root`);
    process.exit(1);
  }
  copy(from, join(extension, "model", name));
}

console.log(`${RUNTIME.length + MODEL.length} files copied`);
