/**
 * The JavaScript port against the Python package, on the real model.
 *
 * The browser runs its own copy of the alphabet, the windowing and the hybrid, plus a
 * different ONNX runtime. Any one of those drifting from the Python side would change what
 * users get without changing any number in the README. So this loads the shipped int8 model
 * with onnxruntime-web and checks it gives exactly the answers the Python package recorded
 * in fixtures/python-hybrid.json.
 *
 * Skipped until `npm run vendor` has copied the model in.
 */

import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { gunzipSync } from "node:zlib";

import { applyLexicon, parseLexicon } from "../lib/hybrid.js";
import { LocalTagger } from "../lib/tagger.js";

const here = dirname(fileURLToPath(import.meta.url));
const model = join(here, "..", "model");
const present = ["tagger.onnx", "tagger.json", "lexicon.tsv.gz"].every((name) =>
  existsSync(join(model, name)),
);

test("the browser build answers exactly like the Python package", { skip: !present }, async () => {
  const ort = await import("onnxruntime-web");
  ort.env.wasm.numThreads = 1;

  const session = await ort.InferenceSession.create(readFileSync(join(model, "tagger.onnx")));
  const meta = JSON.parse(readFileSync(join(model, "tagger.json"), "utf8"));
  const lexicon = parseLexicon(gunzipSync(readFileSync(join(model, "lexicon.tsv.gz"))).toString("utf8"));

  const [input] = session.inputNames;
  const [output] = session.outputNames;
  const tagger = new LocalTagger(async (ids, rows, columns) => {
    const result = await session.run({ [input]: new ort.Tensor("int64", ids, [rows, columns]) });
    return result[output].data;
  }, meta);

  const cases = JSON.parse(readFileSync(join(here, "fixtures", "python-hybrid.json"), "utf8"));
  const mismatches = [];

  for (const { typed, expected } of cases) {
    const restored = applyLexicon(typed, await tagger.restore(typed), lexicon);
    if (restored !== expected) mismatches.push({ typed, expected, restored });
  }

  assert.deepEqual(mismatches, [], `${mismatches.length} of ${cases.length} cases differ`);
});
