/**
 * The spell checker: the same toy cases as the Python tests, then the JavaScript port against
 * the Python package on the real shipped vocabulary.
 */

import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { gunzipSync } from "node:zlib";

import { edits1, parseVocabulary, Speller } from "../lib/spelling.js";

const WORDS = new Map(
  Object.entries({
    xahis: ["xahiş", 1711],
    xalis: ["xalis", 506],
    xayis: ["xayiş", 4],
    ev: ["ev", 8895],
    ve: ["və", 1_084_336],
    ne: ["nə", 12_463],
    nem: ["nəm", 318],
    bilim: ["bilim", 90],
    kitab: ["kitab", 5000],
    mekteb: ["məktəb", 4000],
    men: ["mən", 50_000],
    gedirem: ["gedirəm", 800],
    dunen: ["dünən", 2000],
    geldi: ["gəldi", 9000],
  }),
);

const speller = () => new Speller({ words: WORDS, suffixes: new Set(["lar", "ler", "lari"]) });

test("edits cover the four kinds of slip", () => {
  const edits = new Set(edits1("ab"));
  for (const expected of ["b", "ba", "ac", "abc"]) assert.ok(edits.has(expected), expected);
});

test("a common word is never suspect, however close a bigger one is", () => {
  assert.equal(speller().isSuspicious("ev"), false);
});

test("a known stem with a common ending is plausible", () => {
  assert.equal(speller().isSuspicious("kitablari"), false);
});

test("a missing letter comes back, spelled and capitalised", () => {
  assert.equal(speller().suggest("mektb")[0], "məktəb");
  assert.equal(speller().suggest("Mektb")[0], "Məktəb");
});

test("the more common reading ranks first", () => {
  const options = speller().suggest("xayis");
  assert.equal(options[0], "xahiş");
  assert.ok(options.includes("xalis"));
});

test("words written together can be split", () => {
  assert.ok(speller().suggest("nebilim").includes("nə bilim"));
});

test("a capitalised word mid-sentence is taken for a name", () => {
  assert.deepEqual(speller().check("dünən Mektb gəldi"), []);
});

test("check reports spans into the text", () => {
  const [found] = speller().check("mən mektb gedirəm");
  assert.deepEqual([found.start, found.end, found.typed], [4, 9, "mektb"]);
});

test("the vocabulary format parses, suffix line and all", () => {
  const { words, suffixes } = parseVocabulary("@suffixes\tlar,m\nkitab\tkitab\t5\n");
  assert.deepEqual([...suffixes], ["lar", "m"]);
  assert.deepEqual(words.get("kitab"), ["kitab", 5]);
});

const here = dirname(fileURLToPath(import.meta.url));
const vocabulary = join(here, "..", "model", "vocabulary.tsv.gz");

test(
  "the browser build suggests exactly what the Python package suggests",
  { skip: !existsSync(vocabulary) },
  () => {
    const real = new Speller(parseVocabulary(gunzipSync(readFileSync(vocabulary)).toString("utf8")));
    const cases = JSON.parse(readFileSync(join(here, "fixtures", "python-spelling.json"), "utf8"));

    const mismatches = [];
    for (const { text, expected } of cases) {
      const got = real.check(text).map(({ start, end, typed, options }) => ({ start, end, typed, options }));
      if (JSON.stringify(got) !== JSON.stringify(expected)) mismatches.push({ text, expected, got });
    }
    assert.deepEqual(mismatches, [], `${mismatches.length} of ${cases.length} texts differ`);
  },
);
