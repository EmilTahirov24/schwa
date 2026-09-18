"use client";

import { useEffect, useMemo, useState } from "react";

import { withRejected, wordKey, type Restored, type Word } from "@/lib/restorer";
import { EXAMPLES, type Strings } from "@/lib/strings";
import { megabytes, useRestorer } from "@/lib/useRestorer";

const DEBOUNCE = 120;

/**
 * Type on the left, read the restored text as you go. There is no button: the model is
 * fast enough to answer between keystrokes, and watching the letters change is the point.
 */
export function LiveEditor({ text }: { text: Strings }) {
  const model = useRestorer();
  const [input, setInput] = useState("");
  const [result, setResult] = useState<{ typed: string; restored: Restored } | null>(null);
  const [rejected, setRejected] = useState<ReadonlySet<string>>(new Set());
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (model.status !== "ready" || !input) return;

    let current = true;
    const timer = setTimeout(async () => {
      const restored = await model.restorer.restoreDetailed(input);
      if (current) setResult({ typed: input, restored });
    }, DEBOUNCE);

    return () => {
      current = false;
      clearTimeout(timer);
    };
  }, [input, model]);

  // Clearing the box clears the result: derived here rather than reset in an effect.
  const visible = input ? result : null;

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
          onChange={(event) => {
            setInput(event.target.value);
            setCopied(false);
          }}
          placeholder={text.placeholder}
          spellCheck={false}
          rows={7}
          className="min-h-44 w-full resize-y rounded-2xl border border-neutral-300 bg-white px-5 py-4 text-lg leading-relaxed outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-500/15 dark:border-neutral-700 dark:bg-neutral-900"
        />

        <div className="relative min-h-44 rounded-2xl border border-neutral-200 bg-neutral-50 px-5 py-4 text-lg leading-relaxed dark:border-neutral-800 dark:bg-neutral-900/60">
          {visible ? (
            <output className="whitespace-pre-wrap break-words" aria-live="polite">
              <Rendered typed={visible.typed} words={visible.restored.words} rejected={rejected} onToggle={toggle} text={text} />
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
                setInput(example);
                setRejected(new Set());
                setCopied(false);
              }}
              className="rounded-full border border-neutral-300 px-3 py-1 text-sm text-neutral-700 transition hover:border-emerald-500 hover:text-emerald-700 dark:border-neutral-700 dark:text-neutral-300 dark:hover:border-emerald-400 dark:hover:text-emerald-300"
            >
              {example.length > 28 ? `${example.slice(0, 26)}…` : example}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3">
          {visible && visible.restored.words.length > 0 && (
            <span className="text-sm tabular-nums text-emerald-700 dark:text-emerald-400">
              {text.restoredLetters(restoredLetters)}
            </span>
          )}
          {input && (
            <button
              type="button"
              onClick={() => {
                setInput("");
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
 * The restored text, letter by letter. A letter that changed carries a key made of its
 * position and its new value, so React mounts it afresh - and the arrival animation plays -
 * exactly when it changes, and never for text that stayed the same.
 */
function Rendered({
  typed,
  words,
  rejected,
  onToggle,
  text,
}: {
  typed: string;
  words: Word[];
  rejected: ReadonlySet<string>;
  onToggle: (word: Word) => void;
  text: Strings;
}) {
  const pieces: React.ReactNode[] = [];
  let cursor = 0;

  for (const word of words) {
    if (word.start > cursor) pieces.push(typed.slice(cursor, word.start));

    const kept = rejected.has(wordKey(word));
    const shown = kept ? word.from : word.to;
    const hint =
      word.source === "dictionary"
        ? text.fromDictionary
        : text.fromModel(Math.round((word.confidence ?? 1) * 100));

    pieces.push(
      <button
        key={wordKey(word)}
        type="button"
        onClick={() => onToggle(word)}
        className={`group relative inline rounded-md px-0.5 transition ${
          kept
            ? "text-neutral-400 line-through decoration-neutral-400/70 dark:text-neutral-500"
            : "bg-emerald-100/70 text-emerald-900 hover:bg-emerald-200/80 dark:bg-emerald-500/15 dark:text-emerald-200 dark:hover:bg-emerald-500/25"
        }`}
      >
        {[...shown].map((char, index) => {
          const fresh = !kept && char !== word.from[index];
          return fresh ? (
            <span key={`${index}-${char}`} className="letter-arrive">
              {char}
            </span>
          ) : (
            <span key={`${index}-${char}`}>{char}</span>
          );
        })}
        <span
          role="tooltip"
          className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 hidden -translate-x-1/2 whitespace-nowrap rounded-lg bg-neutral-900 px-2.5 py-1.5 text-xs font-medium text-white shadow-lg group-hover:block group-focus-visible:block dark:bg-white dark:text-neutral-900"
        >
          {hint}
          <span className="block font-normal opacity-60">{kept ? text.undoHint : text.keepHint}</span>
        </span>
      </button>,
    );

    cursor = word.end;
  }

  if (cursor < typed.length) pieces.push(typed.slice(cursor));
  return <>{pieces}</>;
}
