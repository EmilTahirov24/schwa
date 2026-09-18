/**
 * The words a restorer changed, as spans - the same list the service returns, so the demo page
 * and the extension can highlight or report changes without asking a server.
 */

const WORD = /[\p{L}\p{M}]+(?:['’][\p{L}\p{M}]+)*/gu;

export function changesBetween(typed, restored) {
  if (typed.length !== restored.length) {
    throw new Error("restored text must have the same length as the input");
  }

  const changes = [];
  for (const match of typed.matchAll(WORD)) {
    const start = match.index;
    const end = start + match[0].length;
    const after = restored.slice(start, end);
    if (after !== match[0]) {
      changes.push({ start, end, from: match[0], to: after });
    }
  }
  return changes;
}

/** The [start, end) span of every word, by the same rule the rest of the code uses. */
export function wordSpans(text) {
  return [...text.matchAll(WORD)].map((match) => [match.index, match.index + match[0].length]);
}
