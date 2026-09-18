/** Same cases as the Python hybrid and case-restoration tests. */

import assert from "node:assert/strict";
import { test } from "node:test";

import { stripDiacritics } from "../lib/alphabet.js";
import { applyLexicon, explain, keyOf, parseLexicon, restoreCase } from "../lib/hybrid.js";

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
