# Decisions

Short records of the choices that shaped this project, with the reasoning behind them.

## 1. Restoration is a per-character binary decision, not sequence-to-sequence

**Context.** A restorer could generate the corrected sentence token by token, the way a
translation model does.

**Decision.** The model instead labels every character of the typed text with one of two
labels: keep it, or give it its Azerbaijani form.

**Why.** Exactly seven letter pairs collapse when the diacritics are dropped
(`ç/c`, `ə/e`, `ğ/g`, `ı/i`, `ö/o`, `ş/s`, `ü/u`), and each ASCII form has exactly one
alternative — verified by a test. So the decision space really is binary. This buys three
things a generative model cannot give for free: the output can differ from the input only
in diacritics, the length can never change, and the model stays small enough for CPU and
later for the browser.

## 2. Azerbaijani case functions instead of `str.lower()` and `str.upper()`

**Context.** Azerbaijani has two `i` families: dotted `i`/`İ` and dotless `ı`/`I`.

**Decision.** `az_lower()` and `az_upper()` handle those four letters explicitly.

**Why.** Unicode's default casing gets three of the four cases wrong: `"I".lower()` gives
`"i"` instead of `"ı"`, `"i".upper()` gives `"I"` instead of `"İ"`, and `"İ".lower()`
returns two code points (`i` plus a combining dot above). Any pipeline that lowercases text
before building a lexicon would silently merge words that are not the same. Tests pin all
four directions.

## 3. Wikipedia for training, hand-checked informal text for evaluation

**Context.** The only large, openly licensed Azerbaijani corpus is Wikipedia, but nobody
writes chat messages like an encyclopedia.

**Decision.** Train on Wikipedia, and evaluate on two separate sets: a held-out Wikipedia
split and ~300 real informal sentences annotated by hand and never used for training.

**Why.** Reporting a single number would hide the domain gap. Keeping the two sets apart
turns that gap into a measurement, which is the more honest and more interesting result.

## 4. The headline metric is accuracy on ambiguous words only

**Context.** Most words are unambiguous once the diacritics are dropped, so overall word
accuracy is high before any model exists.

**Decision.** Report overall accuracy, but lead with accuracy on words whose stripped form
maps to more than one real word.

**Why.** That subset is the entire problem. Doing nothing at all already scores 33% on all
words; the same system scores 37% on the ambiguous ones, and that is the number worth
moving.

## 5. The context model sees its neighbours as keys, not as spellings

**Context.** To choose between `qız` and `qiz`, the model looks at the words around it. Those
words could be represented by their spelling or by their typed form.

**Decision.** Neighbours are represented by their key — the form with case and diacritics
removed.

**Why.** When the model runs, the neighbours have not been restored yet either, so their
spelling is exactly what is unknown. Training on spellings would hand the model a feature it
can never have at restoration time. Keys are always observable, on both sides.

## 6. Context probabilities are normalised by the counts that survived pruning

**Context.** The context tables are pruned to keep the model small: rare contexts are
dropped and only the most frequent ones per spelling are kept.

**Decision.** `P(neighbour | form)` divides by the sum of the kept counts, with one
smoothing vocabulary shared by every form.

**Why.** The first version divided by how often the form was seen in total. After pruning
those two numbers differ by orders of magnitude, and they differ *unevenly*: a frequent
spelling loses far more of its table than a rare one, so its contexts came out looking
impossible. The model scored 59.7% on ambiguous words, well below the 79.8% of the plain
lexicon. With the normalisation fixed, the same model and the same data score 85.7%.

## 7. The context model may be given a margin before it overrules the lexicon

**Context.** The most frequent spelling is right about four times out of five, so a model
that answers on its own can lose as much as it gains.

**Decision.** The restorer takes a margin: the context has to score at least that much
higher than the most frequent spelling before its answer is used.

**Why.** It makes the trade-off measurable instead of implicit. On dev, margins of 0, 1 and
3 score 85.7%, 85.4% and 83.6%, so the model is trusted outright — but the knob stays in
the open, and it is the first thing to revisit once the real-world set exists.

## 8. The tagger's loss ignores characters that could not carry a diacritic

**Context.** Only seven letters have an accented form. In running text they are a minority
of the characters; the rest are punctuation, digits, spaces and letters with no alternative.

**Decision.** Those positions are masked out of the loss.

**Why.** Learning to answer "keep" where no other answer exists teaches nothing and buries
the real decisions under easy ones. The same masking makes the training metric honest: the
reported accuracy is the share of correct answers among characters that actually needed one.

## 9. The extension ships with no content script and no site permission

**Context.** The obvious way to build it is a content script on `<all_urls>` that watches
what you type.

**Decision.** Nothing is declared. When you use the context menu or the shortcut, two short
functions are injected into that one tab under `activeTab`, do their work and disappear.

**Why.** It is the smallest permission set that can still do the job, the page cannot be read
at any other moment, and a store reviewer has nothing to question. It also matches what the
service promises: text leaves the browser only on an explicit action and is never stored.

## 10. Restoration runs through the browser's own editing path

**Context.** Replacing text in a field by assigning `value` is simple, but React-based sites
— WhatsApp Web, Instagram, Gmail — keep their own copy of the state and ignore it.

**Decision.** Use `insertText` through the editing command, falling back to assignment plus
a synthetic input event only where that fails.

**Why.** The page sees the same events it would see from a human typing, so its state stays
correct, and the browser's undo stack keeps working: `Ctrl+Z` puts back what you wrote.


## 11. The tagger and the lexicon are combined; the context model is left out of it

**Context.** Once the tagger existed, the obvious move was to stack everything.

**Decision.** The lexicon overrules the tagger where it is unanimous and well attested. The
context model is not part of the combination.

**Why.** Measured, not assumed. The lexicon override is worth 1.4 points of whole-sentence
accuracy, because the tagger garbles rare names the training text is unanimous about
(`Sulaveri` against nine occurrences of `Şulaveri`). Adding the context model on top dragged
accuracy on ambiguous words from 93.8% down to its own 85.1% — the tagger turned out to be
the better judge of exactly the words the context model was built for. The context model
stays in the repository as a measured baseline, not as part of the product.

## 12. The shipped model is quantised to int8

**Context.** The browser extension can only carry the model if the model is small.

**Decision.** Ship the int8 ONNX file, 2.3 MB.

**Why.** It is 3.9× smaller and 1.6× faster than the float version and loses 0.01 points of
accuracy, measured on 3,000 dev sentences. That trade turns "send your text to a server" into
"the model runs in your browser", which is the stronger product and the stronger privacy
claim at once.


## 13. Spelling is suggested, never applied

**Context.** Once diacritics worked, the natural next step was fixing typos too.

**Decision.** Spelling is a separate layer that only suggests. Diacritic restoration stays
automatic.

**Why.** The first layer has a guarantee the second cannot: it only ever adds accents, so the
worst it can do is put one on the wrong letter. Correcting spelling changes letters, and a
wrong correction silently turns a correct rare word - a name, a borrowing, an unusual
inflection - into a common one. With the false alarm rate at 1.4%, applying corrections
automatically would damage roughly one word in seventy. As a suggestion, the same mistake
costs a click.

## 14. Most of the spell checker is about not flagging correct words

**Context.** A plain word-list checker built from Wikipedia flagged 6.6% of the words in clean
Wikipedia text. Nobody keeps using a checker that underlines one word in fifteen.

**Decision.** Three rules, each aimed at a cause found by reading what got flagged:
common words are never suspected just for being near a commoner one; a capitalised word in
mid-sentence is taken for a name; and a known stem followed by an ending seen after at least
1,000 different stems is accepted as a real word.

**Why.** The first cause was words like "ev" (house, 8,895 occurrences) flagged for sitting
one letter from "və". The second was names, half of all unknown words. The third is the
language itself: Azerbaijani stacks suffixes, so correct forms such as "cənazəsiylə" are too
rare for any word list. Together they cut false alarms to 1.7% on dev and 1.4% on test. The
1,000-stem threshold was the knee of a measured trade-off: 30 stems let too many real typos
pass as plausible (84% top-3 recovery), 1,000 recovered 93% for 0.4 points more false alarms,
and 3,000 bought little more at a further cost.

## 15. Personal endings come from the grammar, not the counts

**Context.** Suffixes are otherwise learned from the corpus - an ending counts when it follows
enough known stems.

**Decision.** First- and second-person endings (-m, -am, -n, -san, -q, -iq, -niz, -siniz and
their vowel-harmony variants) are added by hand.

**Why.** Wikipedia is written in the third person. "getmədi" is common in it; "getmədim" - I did
not go - never occurs, and the checker flagged it as a typo. The corpus cannot teach what it
does not contain, and these are exactly the forms people use in messages. On Wikipedia they
cost 0.2 points of typo recall. Their benefit can only be measured on real informal text,
which is what the hand-annotated set is for.
