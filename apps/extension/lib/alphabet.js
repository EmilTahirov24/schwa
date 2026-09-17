/**
 * The alphabet layer, ported from the Python package.
 *
 * It has to exist twice because the model runs in two places: on the server and, when the
 * extension carries the model itself, inside the browser. The rules are the same in both,
 * and the tests in `test/alphabet.test.js` check the same cases as the Python ones.
 *
 * JavaScript's own case functions are wrong for Azerbaijani in exactly the way Python's are:
 * "I".toLowerCase() gives "i" where the language wants "ı".
 */

/** ASCII form a typist produces -> the Azerbaijani letter it may stand for. */
export const FOLD_PAIRS = {
  c: "ç",
  e: "ə",
  g: "ğ",
  i: "ı",
  o: "ö",
  s: "ş",
  u: "ü",
  C: "Ç",
  E: "Ə",
  G: "Ğ",
  I: "İ",
  O: "Ö",
  S: "Ş",
  U: "Ü",
};

/** Azerbaijani letter -> the ASCII form typing without the layout produces. */
export const STRIP_MAP = Object.fromEntries(
  Object.entries(FOLD_PAIRS).map(([ascii, letter]) => [letter, ascii]),
);

export const LABEL_KEEP = 0;
export const LABEL_MARK = 1;

const LOWER_SPECIAL = { I: "ı", İ: "i" };
const UPPER_SPECIAL = { i: "İ", ı: "I" };

/** Lowercase using Azerbaijani rules: I -> ı, İ -> i. */
export function azLower(text) {
  let result = "";
  for (const char of text) {
    result += LOWER_SPECIAL[char] ?? char.toLowerCase();
  }
  return result;
}

/** Uppercase using Azerbaijani rules: i -> İ, ı -> I. */
export function azUpper(text) {
  let result = "";
  for (const char of text) {
    result += UPPER_SPECIAL[char] ?? char.toUpperCase();
  }
  return result;
}

/** Return the text as someone would type it without an Azerbaijani keyboard. */
export function stripDiacritics(text) {
  let result = "";
  for (const char of text) {
    result += STRIP_MAP[char] ?? char;
  }
  return result;
}

/** True if this ASCII letter may hide an Azerbaijani one. */
export function isFoldable(char) {
  return Object.hasOwn(FOLD_PAIRS, char);
}

/** Split correct text into its typed form and one label per character. */
export function toLabels(text) {
  const typed = stripDiacritics(text);
  const characters = [...text];
  const labels = [...typed].map((char, index) =>
    isFoldable(char) && characters[index] !== char ? LABEL_MARK : LABEL_KEEP,
  );
  return { typed, labels };
}

/** Rebuild text from its typed form and per-character labels. */
export function applyLabels(typed, labels) {
  const characters = [...typed];
  if (characters.length !== labels.length) {
    throw new Error(`expected ${characters.length} labels, got ${labels.length}`);
  }

  return characters
    .map((char, index) => (labels[index] === LABEL_MARK ? (FOLD_PAIRS[char] ?? char) : char))
    .join("");
}

/**
 * Apply predicted labels while keeping the diacritics the writer already typed.
 *
 * Someone who wrote "mən sence" has told us about the first word; only the plain ASCII
 * characters are the model's to decide.
 */
export function restoreWithLabels(text, predicted) {
  const { typed, labels } = toLabels(text);
  const merged = labels.map((written, index) =>
    written === LABEL_MARK ? LABEL_MARK : predicted[index],
  );
  return applyLabels(typed, merged);
}
