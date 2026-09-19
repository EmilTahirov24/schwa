/** Same cases as the Python hybrid and case-restoration tests. */

import assert from "node:assert/strict";
import { test } from "node:test";

import { stripDiacritics } from "../lib/alphabet.js";
import { applyLexicon, explain, keyOf, letters, parseLexicon, restoreCase } from "../lib/hybrid.js";

const LEXICON = parseLexicon("sulaveri\tşulaveri\t9\nsence\tsəncə\t40\n");

test("keys ignore case and diacritics", () => {
  assert.equal(keyOf("Səncə"), "sence");
  assert.equal(keyOf("İŞIQ"), "isiq");
});

for (const [typed, form, expected] of [
  ["sence", "səncə", "səncə"],
  ["Sence", "səncə", "Səncə"],
  ["SENCE", "səncə", "SƏNCƏ"],
  ["Idman", "idman", "İdman"],
  ["ISIQ", "ışıq", "IŞIQ"],
]) {
  test(`case of ${typed} carries over to ${form}`, () => {
    assert.equal(restoreCase(typed, form), expected);
  });
}

test("the lexicon fixes a name the tagger garbled", () => {
  const typed = "Sulaveri kendi";
  const tagged = "Sulaveri kəndi";
  assert.equal(applyLexicon(typed, tagged, LEXICON), "Şulaveri kəndi");
});

test("words the lexicon does not know keep the tagger's answer", () => {
  assert.equal(applyLexicon("qiz geldi", "qız gəldi", LEXICON), "qız gəldi");
});

test("punctuation and spacing are left exactly as they were", () => {
  const typed = "  sence,   sulaveri!  ";
  const tagged = "  sence,   sulaveri!  ";
  assert.equal(applyLexicon(typed, tagged, LEXICON), "  səncə,   şulaveri!  ");
});

test("a lexicon entry that would change more than diacritics is ignored", () => {
  const broken = parseLexicon("sence\tgetdi\t9\n");
  assert.equal(applyLexicon("sence", "sence", broken), "sence");
});

test("only diacritics ever change", () => {
  for (const text of ["Sulaveri kendi", "SENCE NEDEN", "123 !?", ""]) {
    const restored = applyLexicon(text, text, LEXICON);
    assert.equal(stripDiacritics(restored), stripDiacritics(text));
  }
});

test("the shipped format parses, blank lines and all", () => {
  const lexicon = parseLexicon("a\tə\t2\n\nb\tç\t3");
  assert.equal(lexicon.size, 2);
  assert.equal(lexicon.get("b"), "ç");
});

test("explain says where each changed word came from", () => {
  const text = "Sulaveri kendi";
  const restored = "Şulaveri kəndi";
  const confidence = [...text].map((_, index) => (index === 10 ? 0.62 : 0.99));

  const words = explain(text, restored, confidence, LEXICON);
  assert.deepEqual(
    words.map((word) => [word.from, word.to, word.source]),
    [
      ["Sulaveri", "Şulaveri", "dictionary"],
      ["kendi", "kəndi", "model"],
    ],
  );
  assert.equal(words[0].confidence, null);
  // "kendi" is only as sure as its least certain letter: the "e" at index 10.
  assert.equal(words[1].confidence, 0.62);
});

test("explain leaves unchanged words out", () => {
  assert.deepEqual(explain("salam", "salam", [1, 1, 1, 1, 1], LEXICON), []);
});

test("letters show the model's odds on every letter that needed a decision", () => {
  // "kendi": the model is 62% sure the "e" at index 10 is "ə", and 99% sure of the rest.
  const text = "Sulaveri kendi";
  const restored = "Şulaveri kəndi";
  const labels = [...text].map((_, index) => (index === 0 || index === 10 ? 1 : 0));
  const confidence = [...text].map((_, index) => (index === 10 ? 0.62 : 0.99));

  const view = letters(text, restored, labels, confidence, LEXICON);
  assert.equal(view.length, text.length);
  // Letters with no accented form, and the space, need no decision.
  for (const index of [2, 3, 4, 6, 8, 9, 11, 12]) assert.equal(view[index], null);
  // The model's odds, whichever reading it chose: "ə" at 62%, the plain "i" at 1%.
  assert.deepEqual(view[10], { probability: 0.62, marked: true, source: "model" });
  assert.equal(view[13].marked, false);
  assert.ok(Math.abs(view[13].probability - 0.01) < 1e-9);
  // "Sulaveri" is the lexicon's word, so the lexicon had the last say on its letters.
  assert.equal(view[0].source, "dictionary");
  assert.equal(view[0].marked, true);
});

test("a letter typed with its accent is the typist's, not the model's", () => {
  const view = letters("sən", "sən", [0, 0, 0], [0.9, 0.9, 0.9], null);
  assert.equal(view[1].source, "typed");
  assert.equal(view[0].source, "model");
});
