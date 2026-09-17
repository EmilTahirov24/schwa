/**
 * Same cases as the Python tests: the two ports must not drift apart.
 *
 *   node --test apps/extension/test
 */

import assert from "node:assert/strict";
import { test } from "node:test";

import {
  LABEL_KEEP,
  LABEL_MARK,
  applyLabels,
  azLower,
  azUpper,
  restoreWithLabels,
  stripDiacritics,
  toLabels,
} from "../lib/alphabet.js";

test("lowercase keeps the two i families apart", () => {
  assert.equal(azLower("IŞIQ"), "ışıq");
  assert.equal(azLower("İSTİFADƏ"), "istifadə");
});

test("uppercase keeps the two i families apart", () => {
  assert.equal(azUpper("ışıq"), "IŞIQ");
  assert.equal(azUpper("istifadə"), "İSTİFADƏ");
});

test("the built-in case functions are wrong here", () => {
  assert.equal("IŞIQ".toLowerCase(), "işiq");
  assert.equal("istifadə".toUpperCase(), "ISTIFADƏ");
});

test("stripping turns text into what a plain keyboard produces", () => {
  assert.equal(stripDiacritics("səncə nədən başlayaq"), "sence neden baslayaq");
  assert.equal(stripDiacritics("İSTİFADƏ"), "ISTIFADE");
  assert.equal(stripDiacritics("hello world 123"), "hello world 123");
});

test("stripping preserves length and is idempotent", () => {
  const text = "Şəhərdə işıq söndü, uşaqlar qışqırdı!";
  const once = stripDiacritics(text);
  assert.equal([...once].length, [...text].length);
  assert.equal(stripDiacritics(once), once);
});

test("labels mark only the hidden letters", () => {
  const { typed, labels } = toLabels("səncə");
  assert.equal(typed, "sence");
  assert.deepEqual(labels, [LABEL_KEEP, LABEL_MARK, LABEL_KEEP, LABEL_KEEP, LABEL_MARK]);
});

test("dotless i is a marked lowercase i", () => {
  const { typed, labels } = toLabels("qız");
  assert.equal(typed, "qiz");
  assert.deepEqual(labels, [LABEL_KEEP, LABEL_MARK, LABEL_KEEP]);
});

test("labels rebuild the original", () => {
  for (const text of ["Səncə nədən başlayaq?", "İşıq söndü.", "hello", "123 !?"]) {
    const { typed, labels } = toLabels(text);
    assert.equal(applyLabels(typed, labels), text);
  }
});

test("applying labels rejects a count that does not match", () => {
  assert.throws(() => applyLabels("sence", [LABEL_KEEP]));
});

test("restoration keeps the diacritics the writer typed", () => {
  const text = "mən sence";
  const predicted = new Array([...text].length).fill(LABEL_KEEP);
  assert.equal(restoreWithLabels(text, predicted), "mən sence");
});

test("restoration only ever changes diacritics", () => {
  const text = "sence neden basliyaq";
  const predicted = [...stripDiacritics(text)].map((char) => (char === "e" ? LABEL_MARK : LABEL_KEEP));
  const restored = restoreWithLabels(text, predicted);
  assert.equal(stripDiacritics(restored), text);
  assert.equal([...restored].length, [...text].length);
});
