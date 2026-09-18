/**
 * The spell checker, ported from `schwa/spelling.py`.
 *
 * It only suggests: restoring diacritics can only put accents back and is applied
 * automatically, while a spelling correction changes letters and a wrong one is worse than
 * none. See the Python module for how each rule was measured; the integration test checks
 * that this port answers exactly as the Python one does, on the shipped vocabulary.
 */

import { azLower } from "./alphabet.js";
import { keyOf, restoreCase } from "./hybrid.js";

const LETTERS = "abcdefghijklmnopqrstuvxyz";
const MIN_STEM = 4;
const WORD = /[\p{L}\p{M}]+(?:['’][\p{L}\p{M}]+)*/gu;
const SENTENCE_END = /[.!?…]\s*$/u;

/** Every string one deletion, transposition, substitution or insertion away. */
export function* edits1(key) {
  for (let i = 0; i <= key.length; i += 1) {
    const left = key.slice(0, i);
    const right = key.slice(i);
    if (right) yield left + right.slice(1);
    if (right.length > 1) yield left + right[1] + right[0] + right.slice(2);
    for (const letter of LETTERS) {
      if (right && letter !== right[0]) yield left + letter + right.slice(1);
      yield left + letter + right;
    }
  }
}

/** Parse the shipped vocabulary: an `@suffixes` line, then `key<TAB>form<TAB>count` lines. */
export function parseVocabulary(text) {
  const words = new Map();
  let suffixes = [];
  for (const line of text.split("\n")) {
    if (!line) continue;
    if (line.startsWith("@suffixes\t")) {
      suffixes = line.slice("@suffixes\t".length).split(",").filter(Boolean);
      continue;
    }
    const [key, form, count] = line.split("\t");
    words.set(key, [form, Number(count)]);
  }
  return { words, suffixes: new Set(suffixes) };
}

export class Speller {
  constructor(
    { words, suffixes },
    { minCount = 5, rareCeiling = 20, dominance = 100, editProbability = 0.05, maxDistance = 2 } = {},
  ) {
    this.words = words;
    this.suffixes = suffixes;
    this.minCount = minCount;
    this.rareCeiling = rareCeiling;
    this.dominance = dominance;
    this.editCost = Math.log(editProbability);
    this.maxDistance = maxDistance;
    this.total = 0;
    for (const [, count] of words.values()) this.total += count;
    this.total ||= 1;
    // Live checking asks about the same words on every keystroke.
    this.memo = new Map();
  }

  count(key) {
    return this.words.get(key)?.[1] ?? 0;
  }

  known(key) {
    return this.count(key) >= this.minCount;
  }

  plausible(key) {
    for (let cut = MIN_STEM; cut < key.length; cut += 1) {
      if (this.suffixes.has(key.slice(cut)) && this.known(key.slice(0, cut))) return true;
    }
    return false;
  }

  isSuspicious(key) {
    if (key.length < 3) return false;
    if (this.known(key)) {
      const count = this.count(key);
      if (count >= this.rareCeiling) return false;
      for (const near of edits1(key)) {
        if (this.count(near) >= count * this.dominance) return true;
      }
      return false;
    }
    return !this.plausible(key);
  }

  score(frequency, distance) {
    return Math.log(frequency / this.total) + distance * this.editCost;
  }

  /** Scored corrections for `key`, best first; each is one word or a split into two. */
  candidates(key) {
    const scored = new Map(); // joined words -> score
    const keep = (parts, value) => {
      const id = parts.join(" ");
      if (!scored.has(id) || scored.get(id).score < value) scored.set(id, { parts, score: value });
    };

    let frontier = new Set([key]);
    let foundAt = 0;
    for (let distance = 1; distance <= this.maxDistance; distance += 1) {
      const next = new Set();
      for (const word of frontier) for (const edit of edits1(word)) next.add(edit);
      frontier = next;
      for (const candidate of frontier) {
        if (candidate !== key && this.known(candidate)) {
          keep([candidate], this.score(this.count(candidate), distance));
        }
      }
      if (scored.size) {
        foundAt = distance;
        break;
      }
    }

    // Splits one edit away only when no single word was one edit away - see the Python side.
    const joined = [[0, key]];
    if (foundAt !== 1) for (const edit of new Set(edits1(key))) joined.push([1, edit]);

    for (const [distance, form] of joined) {
      for (let i = 2; i < form.length - 1; i += 1) {
        const first = form.slice(0, i);
        const second = form.slice(i);
        if (this.known(first) && this.known(second)) {
          const frequency = (this.count(first) * this.count(second)) / this.total;
          keep([first, second], this.score(frequency, distance));
        }
      }
    }

    // Ties break the way Python's sort does: higher score first, then the larger tuple.
    return [...scored.values()].sort(
      (a, b) => b.score - a.score || compareParts(b.parts, a.parts),
    );
  }

  /** Corrections for one word, with diacritics and its capitalisation; empty if it looks fine. */
  suggest(word, limit = 3, sentenceStart = true) {
    const first = [...word][0] ?? "";
    if (first && first !== azLower(first) && !sentenceStart) return [];

    const key = keyOf(word);
    const cacheKey = `${key}|${limit}`;
    if (!this.memo.has(cacheKey)) {
      const options = this.isSuspicious(key)
        ? this.candidates(key)
            .slice(0, limit)
            .map(({ parts }) => parts.map((part) => this.words.get(part)[0]))
        : [];
      this.memo.set(cacheKey, options);
    }

    return this.memo.get(cacheKey).map((forms) => {
      const [head, ...rest] = forms;
      return [restoreCase(word, head), ...rest].join(" ");
    });
  }

  /** Every word in `text` that looks misspelt, with its suggestions. */
  check(text, limit = 3) {
    const found = [];
    for (const match of text.matchAll(WORD)) {
      const before = text.slice(0, match.index);
      const sentenceStart = !before.trim() || SENTENCE_END.test(before);
      const options = this.suggest(match[0], limit, sentenceStart);
      if (options.length) {
        found.push({ start: match.index, end: match.index + match[0].length, typed: match[0], options });
      }
    }
    return found;
  }
}

function compareParts(a, b) {
  for (let i = 0; i < Math.min(a.length, b.length); i += 1) {
    if (a[i] !== b[i]) return a[i] < b[i] ? -1 : 1;
  }
  return a.length - b.length;
}
