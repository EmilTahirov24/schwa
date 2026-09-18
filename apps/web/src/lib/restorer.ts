/**
 * The restorer, running in the visitor's browser.
 *
 * The code is the extension's (see scripts/sync.mjs): the model and the lexicon are fetched
 * once, and every restoration after that happens on this machine. Nothing the visitor types
 * is sent anywhere.
 */

import { changesBetween } from "@/lib/duzelt/changes.js";
import { localRestorer } from "@/lib/duzelt/local.js";

export type Change = {
  start: number;
  end: number;
  from: string;
  to: string;
};

export type RestoreResult = {
  text: string;
  changes: Change[];
};

export type Restorer = {
  name: string;
  restore: (text: string) => Promise<string>;
};

const base = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

/** Load the model and the lexicon; resolves to null if they could not be loaded. */
export function loadRestorer(): Promise<Restorer | null> {
  return localRestorer(`${base}/model/`, `${base}/ort/`) as Promise<Restorer | null>;
}

export async function restore(restorer: Restorer, text: string): Promise<RestoreResult> {
  const restored = await restorer.restore(text);
  return { text: restored, changes: changesBetween(text, restored) as Change[] };
}

/**
 * Rebuild the text with some changes turned down.
 *
 * Every change covers the same span in both versions - a restorer may only swap letters for
 * their accented forms - so a rejected change is just the original slice put back.
 */
export function applyChanges(
  typed: string,
  changes: Change[],
  rejected: ReadonlySet<number>,
): string {
  let result = "";
  let cursor = 0;

  changes.forEach((change, index) => {
    result += typed.slice(cursor, change.start);
    result += rejected.has(index) ? change.from : change.to;
    cursor = change.end;
  });

  return result + typed.slice(cursor);
}
