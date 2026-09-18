/**
 * Running the character tagger inside the browser.
 *
 * The session is injected rather than created here, so this file can be tested without
 * onnxruntime and so the same code works in a service worker, in a page, or in a test.
 *
 * Long text is cut into overlapping windows: the model reads a whole window but only the
 * middle of it is kept, so no character is ever decided without context on both sides. The
 * bounds are the same ones the Python side computes.
 */

import { restoreWithLabels, stripDiacritics } from "./alphabet.js";

const PAD_ID = 0;
const UNKNOWN_ID = 1;

/** Split a length into windows, with the part of each window that is actually used. */
export function windowBounds(length, window, overlap) {
  if (length <= window) {
    return [{ start: 0, end: length, commitStart: 0, commitEnd: length }];
  }

  const stride = window - overlap;
  const half = Math.floor(overlap / 2);
  const bounds = [];

  for (let start = 0; start < length; start += stride) {
    const end = Math.min(start + window, length);
    bounds.push({
      start,
      end,
      commitStart: start === 0 ? start : start + half,
      commitEnd: end === length ? end : end - half,
    });
    if (end === length) break;
  }

  return bounds;
}

export class LocalTagger {
  /**
   * @param run  async (ids: BigInt64Array, rows: number, columns: number) => Float32Array
   *             of shape [rows, columns, 2]; the model's two scores per character.
   * @param meta {characters: string[], config: {window: number, overlap: number}}
   */
  constructor(run, meta) {
    this.run = run;
    this.config = meta.config;
    this.ids = new Map();
    meta.characters.forEach((char, index) => this.ids.set(char, index + 2));
  }

  encode(text) {
    return [...text].map((char) => this.ids.get(char) ?? UNKNOWN_ID);
  }

  /** One label per character, for each text. */
  async predict(texts) {
    return (await this.predictDetailed(texts)).labels;
  }

  /**
   * Labels plus how sure the model was of each one.
   *
   * The two scores per character are turned into a probability with a softmax; the
   * confidence of a character is the probability of the label that was chosen, so it is
   * always at least one half.
   */
  async predictDetailed(texts) {
    const pieces = [];
    texts.forEach((text, index) => {
      const characters = [...text];
      for (const bound of windowBounds(characters.length, this.config.window, this.config.overlap)) {
        pieces.push({
          index,
          text: characters.slice(bound.start, bound.end).join(""),
          from: bound.commitStart - bound.start,
          to: bound.commitEnd - bound.start,
        });
      }
    });

    const labels = texts.map(() => []);
    const confidence = texts.map(() => []);
    if (pieces.length === 0) return { labels, confidence };

    const columns = Math.max(...pieces.map((piece) => [...piece.text].length), 1);
    const ids = new BigInt64Array(pieces.length * columns).fill(BigInt(PAD_ID));

    pieces.forEach((piece, row) => {
      this.encode(piece.text).forEach((id, column) => {
        ids[row * columns + column] = BigInt(id);
      });
    });

    const scores = await this.run(ids, pieces.length, columns);

    pieces.forEach((piece, row) => {
      for (let column = piece.from; column < piece.to; column += 1) {
        const at = (row * columns + column) * 2;
        const mark = 1 / (1 + Math.exp(scores[at] - scores[at + 1]));
        const label = mark > 0.5 ? 1 : 0;
        labels[piece.index].push(label);
        confidence[piece.index].push(label ? mark : 1 - mark);
      }
    });

    return { labels, confidence };
  }

  /** Restore one text. */
  async restore(text) {
    const [restored] = await this.restoreMany([text]);
    return restored;
  }

  /** Restore a batch; batching is what keeps this fast enough to feel instant. */
  async restoreMany(texts) {
    if (texts.length === 0) return [];
    const predictions = await this.predict(texts.map((text) => stripDiacritics(text)));
    return texts.map((text, index) => restoreWithLabels(text, predictions[index]));
  }
}
