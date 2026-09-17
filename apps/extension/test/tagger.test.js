/** Tests for the in-browser tagger, with a fake session standing in for onnxruntime. */

import assert from "node:assert/strict";
import { test } from "node:test";

import { stripDiacritics } from "../lib/alphabet.js";
import { LocalTagger, windowBounds } from "../lib/tagger.js";

const META = {
  characters: [..." abcdefghijklmnopqrstuvwxyz.,?!"],
  config: { window: 16, overlap: 4 },
};

/** A session that marks every "e" and leaves everything else alone. */
function markEveryE(tagger) {
  return async (ids, rows, columns) => {
    const scores = new Float32Array(rows * columns * 2);
    const eId = tagger.ids.get("e");
    for (let index = 0; index < rows * columns; index += 1) {
      const isE = ids[index] === BigInt(eId);
      scores[index * 2] = isE ? 0 : 1;
      scores[index * 2 + 1] = isE ? 1 : 0;
    }
    return scores;
  };
}

function build() {
  const tagger = new LocalTagger(() => {}, META);
  tagger.run = markEveryE(tagger);
  return tagger;
}

test("a short text is one window", () => {
  assert.deepEqual(windowBounds(10, 16, 4), [
    { start: 0, end: 10, commitStart: 0, commitEnd: 10 },
  ]);
});

test("windows cover every character exactly once", () => {
  for (const length of [17, 40, 99, 256]) {
    const covered = [];
    for (const bound of windowBounds(length, 16, 4)) {
      for (let index = bound.commitStart; index < bound.commitEnd; index += 1) covered.push(index);
    }
    assert.deepEqual(
      covered,
      Array.from({ length }, (_, index) => index),
    );
  }
});

test("every committed part sits inside its window", () => {
  for (const bound of windowBounds(99, 16, 4)) {
    assert.ok(bound.start <= bound.commitStart);
    assert.ok(bound.commitStart < bound.commitEnd);
    assert.ok(bound.commitEnd <= bound.end);
  }
});

test("unknown characters fall back to one shared id", () => {
  const tagger = build();
  assert.deepEqual(tagger.encode("§§"), [1, 1]);
  assert.notEqual(tagger.encode("a")[0], 1);
});

test("it returns one label per character", async () => {
  const tagger = build();
  const texts = ["sence neden", "a", "x".repeat(60)];
  const labels = await tagger.predict(texts);
  assert.deepEqual(
    labels.map((row) => row.length),
    texts.map((text) => [...text].length),
  );
});

test("it restores the letters the model marked", async () => {
  const tagger = build();
  assert.equal(await tagger.restore("sence neden"), "səncə nədən");
});

test("it restores a batch in one call", async () => {
  const tagger = build();
  assert.deepEqual(await tagger.restoreMany(["sence", "neden"]), ["səncə", "nədən"]);
});

test("an empty batch is allowed", async () => {
  assert.deepEqual(await build().restoreMany([]), []);
});

test("long text crossing several windows keeps its length", async () => {
  const tagger = build();
  const text = "sence neden basliyaq ".repeat(6).trim();
  const restored = await tagger.restore(text);
  assert.equal(stripDiacritics(restored), text);
  assert.equal([...restored].length, [...text].length);
});

test("it only ever changes diacritics", async () => {
  const tagger = build();
  for (const text of ["mən sence", "QIZ MEKTEBE", "123 !?", "salam"]) {
    const restored = await tagger.restore(text);
    assert.equal(stripDiacritics(restored), stripDiacritics(text));
  }
});
