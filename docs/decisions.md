# Decisions

Short records of the choices that shaped this project, with the reasoning behind them. A
number in a record is the one measured when the decision was made, with the code of that
day; the current numbers are in [results.md](results.md).

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

*Later:* web text became a second test set (18) and then part of the training text (19); the
hand-annotated set is still the one measurement of chat.

## 4. The headline metric is accuracy on ambiguous words only

**Context.** Most words are unambiguous once the diacritics are dropped, so overall word
accuracy is high before any model exists.

**Decision.** Report overall accuracy, but lead with accuracy on words whose stripped form
maps to more than one real word.

**Why.** That subset is the entire problem. On the dev split, always writing the commonest
spelling already gets 97.1% of all words right, but only 79.2% of the ambiguous ones; the
character tagger, trained on Wikipedia alone, gets 98.7% and 93.8%. Over all words the two
systems are 1.6 points apart, over ambiguous words 14.5. Only the second number says how
much better one of them is.

*Later:* which words count as ambiguous rests on a threshold - a rival spelling has to reach
5% of a form's occurrences - and that is a judgement, so it was measured instead of argued
(`poe threshold`, the table in [results.md](results.md)). Scoring the same predictions at 1%,
2%, 5%, 10% and 20% changes how many words are in the set, from 7.8% of all words down to
1.5%, and it moves both systems the same way: the lower the threshold, the more easy words
join the set and the better the lexicon looks. The shipped model leads at every one of them,
from +8.51 points (+8.24 to +8.78) at 1% to +25.89 (+24.94 to +26.81) at 20%. 5% sits in the
middle, and no threshold in that range changes what the comparison says.

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

*Later:* once the model shipped inside the extension, the fallback to the service went, and
with it the one host permission and the `storage` permission its settings needed. Text now
never leaves the browser at all.

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
(`Sulaveri` against nine occurrences of `Şulaveri`). Letting the context model decide the
ambiguous words drags the hybrid's accuracy on them from 93.8% down to the context model's
own 85.0%, and whole sentences from 87.9% to 84.0% (dev split, with the tagger trained on
Wikipedia alone; `evaluate.py --split dev --hybrid-context --no-report`) — the tagger turned
out to be the better judge of exactly the words the context model was built for. The context
model stays in the repository as a measured baseline, not as part of the product.

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

**Context.** The first version of the checker - a word list that also suspected rare words
one letter from much commoner ones - flagged 6.8% of the words in clean dev text. Nobody keeps
using a checker that underlines one word in fifteen. (A bare word list, which does not look
for such mistakes at all, flags 4.5%.)

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

## 16. Confidence intervals resample articles, not sentences

**Context.** A number from 172,328 sentences looks exact, and two systems 0.3 points apart
look different. Whether they are depends on how much the number would move on other text of
the same kind.

**Decision.** Every rate in `docs/results.md` carries a 95% bootstrap interval, and every
system is compared with the one above it on the same resamples. The unit of resampling is
the article (the document, for web text), never the sentence.

**Why.** Sentences from one article share its names and its topic, and a name that recurs
through an article is restored right every time or wrong every time. Resampling sentences
one by one treats those repeats as independent evidence and reports intervals narrower than
the truth; a test pins that grouped resampling widens them when errors cluster. The
comparison is paired because two intervals that overlap can still hide a consistent
difference: scoring both systems on the same resamples and taking the interval of their
difference answers "is the hybrid better than the tagger?" directly.

## 17. The bundled model is committed

**Context.** The model files were generated artefacts and ignored by git, like the data. CI
therefore never saw them, and the tests that check the browser build against the Python
package - the ones that exist because the two once disagreed - were skipped on every push.

**Decision.** `packages/core/schwa/data`, the four files the package ships (5.7 MB), is
committed. The extension and the demo page copy their model from it.

**Why.** It is the one copy everything else is built from, so committing it makes every
distribution provably the same model, lets CI run the parity tests, and makes
`pip install` from the repository work before any release. The training data and the float
checkpoints stay out: they are large, and a command rebuilds them.

## 18. Web text is a second test set, measured as it comes

**Context.** Every number described Wikipedia. The hand-annotated set of real messages is
still to be made, and will be small; a large sample of text that is not an encyclopedia was
needed first.

**Decision.** Stream the first 400 MB of CC-100's Azerbaijani text, drop every sentence that
also occurs in Wikipedia, and split the rest by document into train, dev and test. In train
and dev a sentence of 25 letters or more must also contain ə; the test split is kept as it
comes.

**Why.** The ə filter was meant to keep out text typed without diacritics, and Turkish
labelled as Azerbaijani: either would make a wrong reference. Read, what it dropped was
mostly genuine sentences that simply have no ə - as 5.8% of the long sentences in
Wikipedia's dev split do. On the test split that made it a bias rather than a safeguard, so
it was taken off there: 3,828 sentences came back, and the hybrid's accuracy on ambiguous
words moved from 93.25% to 93.22%, far inside its interval. In train and dev it stays, where
losing a few good sentences costs nothing. What web text cannot stand in for is chat: it is
still edited, which is why the hand-annotated set remains the last missing measurement.

## 19. The shipped tagger reads the web as well as Wikipedia; artificial capitals do not ship

**Context.** The tagger had only read Wikipedia. On the web test set it lost half a point on
ambiguous words, and the error analysis found words written entirely in capitals -
headlines, mostly - wrong 13% of the time: in capitals a plain `I` is usually a dotted `İ`,
the reverse of lowercase, and Wikipedia has few capitals to learn that from.

**Decision.** Train on Wikipedia and the web sample's training split together, 4,306,000
sentences. Do not put training text into capitals artificially.

**Why.** Five taggers, the same in everything but what they read, were scored alone on both
test sets, each against the Wikipedia-only model on the same resamples. The rule was set
before the runs: a candidate ships only if it is no worse on either test set, on ambiguous
words or on whole sentences. Reading the web as well raised the web's ambiguous words from
93.2% to 95.7% and its whole sentences from 88.4% to 92.8% (+2.50 and +4.42 points, intervals
well clear of zero) and left Wikipedia where it was (+0.15 and -0.02, both intervals spanning
zero). It also fixed most of the capitals by itself - on the web they went from 83.5% right
to 94.4% - because the web has real headlines to learn from. Capitals made artificially did
the same job worse: on Wikipedia text they lifted the web's capitals only to 91.1%, and cost
0.20 and 0.23 points on Wikipedia, intervals clear of zero, so they failed the rule; added to
the combined text they bought one more point on the web's capitals and lost 0.4 on
Wikipedia's. The web alone made the best model for the web's ambiguous words and one four
points worse on Wikipedia's. What a model reads is what it is good at, and the numbers say
read both.

*Later:* this choice was made on the test splits, which is choosing on what is reported. The
same five taggers were therefore scored again on the dev splits, where a choice between
models belongs — `poe domain-dev`, the table in [results.md](results.md) — and nothing about
the decision changes. Reading both texts gains 2.51 points on the web's ambiguous words
(+2.39 to +2.64) and 4.56 on its whole sentences, and is level on Wikipedia (-0.05, -0.20 to
+0.10, and -0.00, -0.17 to +0.16). Artificial capitals still fail on Wikipedia's ambiguous
words (-0.18, -0.31 to -0.06). Added to the combined text they still pass the rule and still
trade Wikipedia's capitals for the web's (94.1% against 94.5%, and 95.3% against 94.6%), so
the model that ships is still the one trained on the two texts as they are. One difference
between the tables is worth knowing: the web dev split keeps the ə filter that the web test
split does not (18).

## 20. The extension edits only the letters that change

**Context.** Restoring a whole editor the simple way - select everything, insert the restored
text - works in a plain box. In an editor like Gmail's or WhatsApp Web's it flattened what
was there: in Chrome, a two-line message lost its bold, its link and an emoji drawn as an
image, and gained a blank line.

**Decision.** The page side reads the editor's visible, editable text nodes and puts back
only the stretch of each node from its first changed letter to its last, each through the
browser's editing command.

**Why.** A restoration never changes the length of anything, so every letter's place is
known before and after, and a text node has one format throughout: an edit inside it cannot
lose formatting, and nothing between nodes is touched. A line break is read wherever a new
line or an image separates two nodes, so words the reader sees apart are never read as one.
The cost is undo: every changed node is its own edit, so in formatted text `Ctrl+Z` may take
several presses.
