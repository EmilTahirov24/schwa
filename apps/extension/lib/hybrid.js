/**
 * The hybrid, ported from `HybridRestorer` in the Python package.
 *
 * The tagger reads letters, so it handles words nothing is known about, but it can still
 * garble a name the training text was unanimous about. The shipped lexicon holds exactly
 * those words - one spelling each, seen at least twice - and overrules the tagger on them and
 * nowhere else. Measured on the test split that is worth 1.4 points of whole-sentence accuracy.
 */

import { azLower, azUpper, stripDiacritics } from "./alphabet.js";

/** Letters, with apostrophes inside a word - the same rule as the Python tokenizer. */
const WORD = /[\p{L}\p{M}]+(?:['’][\p{L}\p{M}]+)*/gu;

/** The case- and diacritic-free form a word is looked up by. */
export function keyOf(word) {
  return stripDiacritics(azLower(word));
}

/** Give `form` the capitalisation of `typed`. */
export function restoreCase(typed, form) {
  const isAllUpper = typed === azUpper(typed) && typed !== azLower(typed);
  if (isAllUpper && [...typed].length > 1) return azUpper(form);

  const first = [...typed][0] ?? "";
  if (first && first !== azLower(first)) {
    const [head, ...rest] = [...form];
    return azUpper(head) + rest.join("");
  }
  return form;
}

/**
 * Overrule the tagger's output wherever the lexicon knows the word.
 *
 * `typed` and `tagged` have the same length - the tagger may only swap letters for their
 * accented forms - so a word's span in one is its span in the other.
 */
export function applyLexicon(typed, tagged, lexicon) {
  let result = "";
  let cursor = 0;

  for (const match of typed.matchAll(WORD)) {
    const start = match.index;
    const end = start + match[0].length;
    result += tagged.slice(cursor, start);

    const form = lexicon.get(keyOf(match[0]));
    const candidate = form === undefined ? null : restoreCase(match[0], form);
    // The same guard as the Python side: a suggestion may only put diacritics back.
    const safe = candidate !== null && stripDiacritics(candidate) === stripDiacritics(match[0]);
    result += safe ? candidate : tagged.slice(start, end);

    cursor = end;
  }

  return result + tagged.slice(cursor);
}

/** Parse the shipped lexicon: one `key<TAB>form<TAB>count` line per entry. */
export function parseLexicon(text) {
  const lexicon = new Map();
  for (const line of text.split("\n")) {
    if (!line) continue;
    const [key, form] = line.split("\t");
    lexicon.set(key, form);
  }
  return lexicon;
}
