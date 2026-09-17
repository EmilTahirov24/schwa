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

**Why.** That subset is the entire problem. A metric that is already at 90% without a model
cannot show whether the model helps.
