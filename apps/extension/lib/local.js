/**
 * Load the restorer into the browser itself.
 *
 * When this succeeds nothing talks to a server: the text stays in the tab it was typed in.
 * It is the same combination that scores best in the evaluation - the tagger, overruled by
 * the lexicon on words the training text was unanimous about. If the model was not bundled
 * (`npm run vendor` copies it in), the caller falls back to the service.
 *
 * `base` is where the files live: the extension's own URL inside the extension, the site's
 * path on the demo page. That is the only difference between the two.
 */

import { restoreWithLabels, stripDiacritics } from "./alphabet.js";
import { applyLexicon, explain, parseLexicon } from "./hybrid.js";
import { parseVocabulary, Speller } from "./spelling.js";
import { LocalTagger } from "./tagger.js";

async function loadLexicon(url) {
  const response = await fetch(url);
  if (!response.ok) return null;

  // Shipped gzipped (1.8 MB instead of 7); the browser unpacks it without any library.
  const unpacked = response.body.pipeThrough(new DecompressionStream("gzip"));
  return parseLexicon(await new Response(unpacked).text());
}

async function create(base, runtime) {
  const ort = await import(/* webpackIgnore: true */ /* turbopackIgnore: true */ `${runtime}ort.wasm.min.mjs`);

  // The runtime files sit next to the page, never on a CDN; one thread is all a service
  // worker can have anyway, and it starts faster.
  ort.env.wasm.wasmPaths = runtime;
  ort.env.wasm.numThreads = 1;

  const [meta, session, lexicon] = await Promise.all([
    fetch(`${base}tagger.json`).then((response) => response.json()),
    ort.InferenceSession.create(`${base}tagger.onnx`, {
      executionProviders: ["wasm"],
      graphOptimizationLevel: "all",
    }),
    loadLexicon(`${base}lexicon.tsv.gz`).catch(() => null),
  ]);

  const input = session.inputNames[0];
  const output = session.outputNames[0];
  const run = async (ids, rows, columns) => {
    const result = await session.run({ [input]: new ort.Tensor("int64", ids, [rows, columns]) });
    return result[output].data;
  };

  const tagger = new LocalTagger(run, meta);

  return {
    name: lexicon ? "hybrid" : "tagger",

    async restore(text) {
      const tagged = await tagger.restore(text);
      return lexicon ? applyLexicon(text, tagged, lexicon) : tagged;
    },

    /** The restored text, and for every changed word where it came from and how sure. */
    async restoreDetailed(text) {
      const {
        labels: [labels],
        confidence: [confidence],
      } = await tagger.predictDetailed([stripDiacritics(text)]);
      const tagged = restoreWithLabels(text, labels);
      const restored = lexicon ? applyLexicon(text, tagged, lexicon) : tagged;
      return { text: restored, words: explain(text, restored, confidence, lexicon) };
    },
  };
}

const loading = new Map();

/**
 * The restorer, or null when the files are missing. Loaded once per location, then reused.
 *
 * @param base    URL of the folder holding tagger.onnx, tagger.json and lexicon.tsv.gz
 * @param runtime URL of the folder holding the onnxruntime files
 */
export function localRestorer(base, runtime) {
  const cacheKey = `${base}|${runtime}`;
  if (!loading.has(cacheKey)) {
    loading.set(
      cacheKey,
      create(base, runtime).catch((error) => {
        console.warn("schwa: no local model", error);
        return null;
      }),
    );
  }
  return loading.get(cacheKey);
}

/** Inside the extension, the files are packaged with it. */
export function localTagger() {
  return localRestorer(chrome.runtime.getURL("model/"), chrome.runtime.getURL("vendor/"));
}

const spelling = new Map();

/**
 * The spell checker, or null when the vocabulary is missing. It is optional: diacritic
 * restoration works without it, so a failure here never takes the restorer down with it.
 */
export function localSpeller(base) {
  if (!spelling.has(base)) {
    spelling.set(
      base,
      (async () => {
        const response = await fetch(`${base}vocabulary.tsv.gz`);
        if (!response.ok) return null;
        const unpacked = response.body.pipeThrough(new DecompressionStream("gzip"));
        return new Speller(parseVocabulary(await new Response(unpacked).text()));
      })().catch((error) => {
        console.warn("schwa: no spell checker", error);
        return null;
      }),
    );
  }
  return spelling.get(base);
}
