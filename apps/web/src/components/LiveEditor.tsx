"use client";

import { useEffect, useMemo, useState } from "react";

import {
  withRejected,
  wordKey,
  wordSpans,
  type Restored,
  type Suggestion,
  type Word,
} from "@/lib/restorer";
import { EXAMPLES, type Strings } from "@/lib/strings";
import { megabytes, useRestorer } from "@/lib/useRestorer";

const DEBOUNCE = 120;

type Result = { typed: string; restored: Restored; spelling: Suggestion[] };

/**
 * Type on the left, read the restored text as you go. There is no button: the model is
 * fast enough to answer between keystrokes, and watching the letters change is the point.
 *
 * Two kinds of mark, deliberately different. Green is a diacritic put back - applied, because
 * that can only ever add accents. Amber is a word that may be misspelt - only suggested,
 * because fixing it changes letters, and the reader is the one who knows.
 */
export function LiveEditor({ text }: { text: Strings }) {
  const model = useRestorer();
  const [input, setInput] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [rejected, setRejected] = useState<ReadonlySet<string>>(new Set());
  const [ignored, setIgnored] = useState<ReadonlySet<string>>(new Set());
  const [open, setOpen] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (model.status !== "ready" || !input) return;

    let current = true;
    const timer = setTimeout(async () => {
      const restored = await model.restorer.restoreDetailed(input);
      const spelling = model.speller ? model.speller.check(input) : [];
      if (current) setResult({ typed: input, restored, spelling });
    }, DEBOUNCE);

    return () => {
      current = false;
      clearTimeout(timer);
    };
  }, [input, model]);

  // Clearing the box clears the result: derived here rather than reset in an effect.
  const visible = input ? result : null;
  const spelling = useMemo(
    () => (visible ? visible.spelling.filter((s) => !ignored.has(s.typed.toLowerCase())) : []),
    [visible, ignored],
  );

  const output = useMemo(
    () => (visible ? withRejected(visible.typed, visible.restored.words, rejected) : ""),
    [visible, rejected],
  );

  const restoredLetters = useMemo(() => {
    if (!visible) return 0;
    return visible.restored.words
      .filter((word) => !rejected.has(wordKey(word)))
      .reduce((sum, word) => sum + [...word.from].filter((char, i) => char !== word.to[i]).length, 0);
  }, [visible, rejected]);

  const edit = (next: string) => {
    setInput(next);
    setOpen(null);
    setCopied(false);
  };

  const toggle = (word: Word) => {
    setRejected((current) => {
      const next = new Set(current);
      const key = wordKey(word);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
    setCopied(false);
  };

  /** Accepting a suggestion edits what was typed; the diacritics then restore themselves. */
  const accept = (suggestion: Suggestion, option: string) => {
    if (!visible || input !== visible.typed) return;
    edit(input.slice(0, suggestion.start) + option + input.slice(suggestion.end));
  };

  const ignore = (suggestion: Suggestion) => {
    setIgnored((current) => new Set(current).add(suggestion.typed.toLowerCase()));
    setOpen(null);
  };

  const copy = async () => {
    await navigator.clipboard.writeText(output);
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  };

  return (
    <section className="flex flex-col gap-4" aria-labelledby="editor-title">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 id="editor-title" className="text-2xl font-semibold tracking-tight">
          {text.editorTitle}
        </h2>
        <ModelStatus model={model} text={text} />
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <textarea
          value={input}
          onChange={(event) => edit(event.target.value)}
          placeholder={text.placeholder}
          spellCheck={false}
          rows={7}
          className="min-h-44 w-full resize-y rounded-2xl border border-neutral-300 bg-white px-5 py-4 text-lg leading-relaxed outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-500/15 dark:border-neutral-700 dark:bg-neutral-900"
        />

        <div className="relative min-h-44 rounded-2xl border border-neutral-200 bg-neutral-50 px-5 py-4 text-lg leading-relaxed dark:border-neutral-800 dark:bg-neutral-900/60">
          {visible ? (
            <output className="whitespace-pre-wrap break-words" aria-live="polite">
              <Rendered
                typed={visible.typed}
                words={visible.restored.words}
                spelling={spelling}
                rejected={rejected}
                open={open}
                onToggle={toggle}
                onOpen={setOpen}
                onAccept={accept}
                onIgnore={ignore}
                text={text}
              />
            </output>
          ) : (
            <p className="text-neutral-400 dark:text-neutral-500">{text.nothingYet}</p>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-neutral-500 dark:text-neutral-400">{text.examples}:</span>
          {EXAMPLES.map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => {
                edit(example);
                setRejected(new Set());
              }}
              className="rounded-full border border-neutral-300 px-3 py-1 text-sm text-neutral-700 transition hover:border-emerald-500 hover:text-emerald-700 dark:border-neutral-700 dark:text-neutral-300 dark:hover:border-emerald-400 dark:hover:text-emerald-300"
            >
              {example.length > 28 ? `${example.slice(0, 26)}…` : example}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {visible && visible.restored.words.length > 0 && (
            <span className="text-sm tabular-nums text-emerald-700 dark:text-emerald-400">
              {text.restoredLetters(restoredLetters)}
            </span>
          )}
          {spelling.length > 0 && (
            <span className="text-sm tabular-nums text-amber-700 dark:text-amber-400">
              {text.possibleTypos(spelling.length)}
            </span>
          )}
          {input && (
            <button
              type="button"
              onClick={() => {
                edit("");
                setRejected(new Set());
              }}
              className="rounded-lg px-3 py-1.5 text-sm text-neutral-500 transition hover:text-neutral-900 dark:hover:text-neutral-100"
            >
              {text.clear}
            </button>
          )}
          <button
            type="button"
            onClick={() => void copy()}
            disabled={!output}
            className="rounded-lg bg-neutral-900 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-neutral-700 disabled:cursor-not-allowed disabled:opacity-30 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200"
          >
            {copied ? text.copied : text.copy}
          </button>
        </div>
      </div>
    </section>
  );
}

function ModelStatus({ model, text }: { model: ReturnType<typeof useRestorer>; text: Strings }) {
  if (model.status === "ready") return null;

  if (model.status === "failed") {
    return <p className="text-sm text-amber-700 dark:text-amber-400">{text.failed}</p>;
  }

  const share = model.total ? model.loaded / model.total : 0;
  return (
    <div className="flex min-w-56 flex-col gap-1.5">
      <p className="text-sm text-neutral-500 dark:text-neutral-400">
        {model.total ? text.loading(megabytes(model.loaded), megabytes(model.total)) : text.loadingSimple}
      </p>
      <div className="h-1.5 overflow-hidden rounded-full bg-neutral-200 dark:bg-neutral-800">
        {model.total ? (
          <div
            className="h-full rounded-full bg-emerald-500 transition-[width] duration-150"
            style={{ width: `${Math.round(share * 100)}%` }}
          />
        ) : (
          <div className="shimmer h-full w-full" />
        )}
      </div>
    </div>
  );
}

/**
 * The restored text, word by word. A letter that changed carries a key made of its position
 * and its new value, so React mounts it afresh - and the arrival animation plays - exactly
 * when it changes, and never for text that stayed the same.
 */
function Rendered({
  typed,
  words,
  spelling,
  rejected,
  open,
  onToggle,
  onOpen,
  onAccept,
  onIgnore,
  text,
}: {
  typed: string;
  words: Word[];
  spelling: Suggestion[];
  rejected: ReadonlySet<string>;
  open: number | null;
  onToggle: (word: Word) => void;
  onOpen: (start: number | null) => void;
  onAccept: (suggestion: Suggestion, option: string) => void;
  onIgnore: (suggestion: Suggestion) => void;
  text: Strings;
}) {
  const restoredAt = new Map(words.map((word) => [word.start, word]));
  const suspectAt = new Map(spelling.map((suggestion) => [suggestion.start, suggestion]));
  const pieces: React.ReactNode[] = [];
  let cursor = 0;

  for (const [start, end] of wordSpans(typed)) {
    if (start > cursor) pieces.push(typed.slice(cursor, start));
    cursor = end;

    const suspect = suspectAt.get(start);
    if (suspect) {
      pieces.push(
        <SuspectWord
          key={`s${start}`}
          suggestion={suspect}
          isOpen={open === start}
          onOpen={() => onOpen(open === start ? null : start)}
          onAccept={(option) => onAccept(suspect, option)}
          onIgnore={() => onIgnore(suspect)}
          text={text}
        />,
      );
      continue;
    }

    const word = restoredAt.get(start);
    if (word) {
      pieces.push(<RestoredWord key={wordKey(word)} word={word} kept={rejected.has(wordKey(word))} onToggle={onToggle} text={text} />);
      continue;
    }

    pieces.push(typed.slice(start, end));
  }

  if (cursor < typed.length) pieces.push(typed.slice(cursor));
  return <>{pieces}</>;
}

function RestoredWord({
  word,
  kept,
  onToggle,
  text,
}: {
  word: Word;
  kept: boolean;
  onToggle: (word: Word) => void;
  text: Strings;
}) {
  const shown = kept ? word.from : word.to;
  const hint =
    word.source === "dictionary"
      ? text.fromDictionary
      : text.fromModel(Math.round((word.confidence ?? 1) * 100));

  return (
    <button
      type="button"
      onClick={() => onToggle(word)}
      className={`group relative inline rounded-md px-0.5 transition ${
        kept
          ? "text-neutral-400 line-through decoration-neutral-400/70 dark:text-neutral-500"
          : "bg-emerald-100/70 text-emerald-900 hover:bg-emerald-200/80 dark:bg-emerald-500/15 dark:text-emerald-200 dark:hover:bg-emerald-500/25"
      }`}
    >
      {[...shown].map((char, index) =>
        !kept && char !== word.from[index] ? (
          <span key={`${index}-${char}`} className="letter-arrive">
            {char}
          </span>
        ) : (
          <span key={`${index}-${char}`}>{char}</span>
        ),
      )}
      <span
        role="tooltip"
        className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 hidden -translate-x-1/2 whitespace-nowrap rounded-lg bg-neutral-900 px-2.5 py-1.5 text-xs font-medium text-white shadow-lg group-hover:block group-focus-visible:block dark:bg-white dark:text-neutral-900"
      >
        {hint}
        <span className="block font-normal opacity-60">{kept ? text.undoHint : text.keepHint}</span>
      </span>
    </button>
  );
}

function SuspectWord({
  suggestion,
  isOpen,
  onOpen,
  onAccept,
  onIgnore,
  text,
}: {
  suggestion: Suggestion;
  isOpen: boolean;
  onOpen: () => void;
  onAccept: (option: string) => void;
  onIgnore: () => void;
  text: Strings;
}) {
  return (
    <span className="relative inline">
      <button
        type="button"
        onClick={onOpen}
        aria-expanded={isOpen}
        className="rounded-md px-0.5 underline decoration-amber-500 decoration-wavy decoration-2 underline-offset-4 transition hover:bg-amber-100/70 dark:hover:bg-amber-500/15"
      >
        {suggestion.typed}
      </button>
      {isOpen && (
        <span className="line-in absolute top-full left-0 z-20 mt-2 flex w-max min-w-44 flex-col gap-1 rounded-xl border border-neutral-200 bg-white p-2 text-base shadow-xl dark:border-neutral-700 dark:bg-neutral-900">
          <span className="px-2 pt-1 text-xs font-medium text-neutral-500 dark:text-neutral-400">
            {text.didYouMean}
          </span>
          {suggestion.options.map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => onAccept(option)}
              className="rounded-lg px-2 py-1.5 text-left font-medium transition hover:bg-emerald-50 hover:text-emerald-800 dark:hover:bg-emerald-500/15 dark:hover:text-emerald-200"
            >
              {option}
            </button>
          ))}
          <button
            type="button"
            onClick={onIgnore}
            className="rounded-lg px-2 py-1.5 text-left text-sm text-neutral-500 transition hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-800"
          >
            {text.keepAsIs}
          </button>
        </span>
      )}
    </span>
  );
}
