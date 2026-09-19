/**
 * The hybrid, ported from `HybridRestorer` in the Python package.
 *
 * The tagger reads letters, so it handles words nothing is known about, but it can still
 * garble a name the training text was unanimous about. The shipped lexicon holds exactly
 * those words - one spelling each, seen at least twice - and overrules the tagger on them and
 * nowhere else. Measured on the Wikipedia test split that is worth 1.5 points of whole-sentence
 * accuracy.
 */

import { azLower, azUpper, isFoldable, stripDiacritics } from "./alphabet.js";

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

/**
 * Every changed word, with where its spelling came from and how sure the model was.
 *
 * A word the lexicon decided is marked "dictionary": the training text only ever spelled it
 * one way. Otherwise it is the model's call, and its confidence is that of its least certain
 * letter - a word is only as sure as its weakest decision.
 *
 * @param text        what was typed
 * @param restored    the final restored text
 * @param confidence  the model's confidence per character of the typed text
 * @param lexicon     the shipped lexicon, or null
 */
export function explain(text, restored, confidence, lexicon) {
  const typed = stripDiacritics(text);
  const words = [];

  for (const match of text.matchAll(WORD)) {
    const start = match.index;
    const end = start + match[0].length;
    const after = restored.slice(start, end);
    if (after === match[0]) continue;

    const fromDictionary = lexicon !== null && lexicon.has(keyOf(match[0]));
    let least = 1;
    if (!fromDictionary) {
      for (let index = start; index < end; index += 1) {
        if (isFoldable(typed[index])) least = Math.min(least, confidence[index] ?? 1);
      }
    }

    words.push({
      start,
      end,
      from: match[0],
      to: after,
      source: fromDictionary ? "dictionary" : "model",
      confidence: fromDictionary ? null : least,
    });
  }

  return words;
}

/**
 * The decision behind every letter that could carry a diacritic, for showing the model at work.
 *
 * One entry per character of `text`; null where no decision was needed. `probability` is how
 * likely the model found the accented reading, whether or not it chose it; `source` says who
 * had the last word: the model, the lexicon, or the person who typed the accent themselves.
 *
 * @param text        what was typed
 * @param restored    the final restored text
 * @param labels      the model's label per character of the typed text (1 = accented)
 * @param confidence  the model's confidence in each of those labels
 * @param lexicon     the shipped lexicon, or null
 */
export function letters(text, restored, labels, confidence, lexicon) {
  const typed = stripDiacritics(text);
  const byLexicon = new Array(text.length).fill(false);
  if (lexicon !== null) {
    for (const match of text.matchAll(WORD)) {
      if (lexicon.has(keyOf(match[0]))) {
        byLexicon.fill(true, match.index, match.index + match[0].length);
      }
    }
  }

  return Array.from({ length: text.length }, (_, index) => {
    if (!isFoldable(typed[index])) return null;
    const chosen = confidence[index] ?? 1;
    let source = "model";
    if (text[index] !== typed[index]) source = "typed";
    else if (byLexicon[index]) source = "dictionary";
    return {
      probability: labels[index] ? chosen : 1 - chosen,
      marked: restored[index] !== typed[index],
      source,
    };
  });
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
