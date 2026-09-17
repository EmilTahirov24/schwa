/**
 * Load the tagger into the browser itself.
 *
 * When this succeeds the extension stops talking to any server: the text stays in the tab it
 * was typed in. If the model was not bundled — `npm run vendor` copies it in — the caller
 * falls back to the service.
 */

import { LocalTagger } from "./tagger.js";

const MODEL = "model/tagger.onnx";
const META = "model/tagger.json";

let loading = null;

async function create() {
  const ort = await import(chrome.runtime.getURL("vendor/ort.wasm.min.mjs"));

  // The runtime files sit next to the extension, never on a CDN; a service worker cannot
  // use threads anyway, so one is both honest and faster to start.
  ort.env.wasm.wasmPaths = chrome.runtime.getURL("vendor/");
  ort.env.wasm.numThreads = 1;

  const meta = await fetch(chrome.runtime.getURL(META)).then((response) => response.json());
  const session = await ort.InferenceSession.create(chrome.runtime.getURL(MODEL), {
    executionProviders: ["wasm"],
    graphOptimizationLevel: "all",
  });

  const input = session.inputNames[0];
  const output = session.outputNames[0];

  const run = async (ids, rows, columns) => {
    const tensor = new ort.Tensor("int64", ids, [rows, columns]);
    const result = await session.run({ [input]: tensor });
    return result[output].data;
  };

  return new LocalTagger(run, meta);
}

/** The tagger, or null when no model is bundled. Loaded once, then reused. */
export async function localTagger() {
  if (loading === null) {
    loading = create().catch((error) => {
      console.warn("duzelt: no local model, using the service instead", error);
      return null;
    });
  }
  return loading;
}
