/** Tests for the change list, including the bug the first version had. */

import assert from "node:assert/strict";
import { test } from "node:test";

import { changesBetween } from "../lib/changes.js";

test("words with Azerbaijani letters are one word each", () => {
  // The first version matched words with [^\W\d_], and in JavaScript \W is ASCII-only even
  // with the u flag - so "səncə" fell apart at every accented letter and the popup counted
  // changes wrongly. \p{L} is the letter class that actually means letters.
  const changes = changesBetween("sence neden", "səncə nədən");
  assert.deepEqual(
    changes.map((change) => [change.from, change.to]),
    [
      ["sence", "səncə"],
      ["neden", "nədən"],
    ],
  );
});

test("spans index back into the typed text", () => {
  const typed = "bu isiq sondu";
  const [change] = changesBetween(typed, "bu işıq söndü");
  assert.equal(typed.slice(change.start, change.end), "isiq");
  assert.equal(change.start, 3);
});

test("unchanged words are left out", () => {
  const changes = changesBetween("men gelmedim", "mən gelmedim");
  assert.equal(changes.length, 1);
  assert.equal(changes[0].from, "men");
});

test("identical texts have no changes", () => {
  assert.deepEqual(changesBetween("hər şey yerindədir", "hər şey yerindədir"), []);
});

test("texts of different length are refused", () => {
  assert.throws(() => changesBetween("sence", "səncə dedi"));
});
