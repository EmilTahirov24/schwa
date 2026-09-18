/**
 * The restorer, running in the visitor's browser.
 *
 * The code is the extension's (see scripts/sync.mjs): the model and the lexicon are fetched
 * once, and every restoration after that happens on this machine. Nothing the visitor types
 * is sent anywhere.
 */

import { localRestorer } from "@/lib/schwa/local.js";

/** One changed word, with where its spelling came from and how sure the model was. */
export type Word = {
  start: number;
  end: number;
  from: string;
  to: string;
  source: "model" | "dictionary";
  /** Probability of the least certain letter in the word; null for dictionary words. */
  confidence: number | null;
};

export type Restored = {
  text: string;
  words: Word[];
};

export type Restorer = {
  name: string;
  restore: (text: string) => Promise<string>;
  restoreDetailed: (text: string) => Promise<Restored>;
};

const base = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

/** Load the model and the lexicon; resolves to null if they could not be loaded. */
export function loadRestorer(): Promise<Restorer | null> {
  return localRestorer(`${base}/model/`, `${base}/ort/`) as Promise<Restorer | null>;
}

/**
 * Rebuild the text with some words turned back to what was typed.
 *
 * Every word covers the same span in both versions - a restorer may only swap letters for
 * their accented forms - so a rejected word is just the original slice put back.
 */
export function withRejected(typed: string, words: Word[], rejected: ReadonlySet<string>): string {
  let result = "";
  let cursor = 0;

  for (const word of words) {
    result += typed.slice(cursor, word.start);
    result += rejected.has(wordKey(word)) ? word.from : word.to;
    cursor = word.end;
  }

  return result + typed.slice(cursor);
}

/** A word's identity across re-renders: where it starts and what was typed there. */
export function wordKey(word: Pick<Word, "start" | "from">): string {
  return `${word.start}:${word.from}`;
}
