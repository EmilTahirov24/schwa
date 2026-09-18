"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { applyChanges, info, restore, type Change } from "@/lib/api";
import { EXAMPLE, strings, type Language } from "@/lib/strings";

export default function Page() {
  const [language, setLanguage] = useState<Language>("az");
  const [input, setInput] = useState("");
  const [typed, setTyped] = useState("");
  const [changes, setChanges] = useState<Change[]>([]);
  const [rejected, setRejected] = useState<ReadonlySet<number>>(new Set());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [model, setModel] = useState<string | null>(null);

  const text = strings[language];

  useEffect(() => {
    info()
      .then((service) => setModel(service.restorer))
      .catch(() => setModel(null));
  }, []);

  const output = useMemo(() => applyChanges(typed, changes, rejected), [typed, changes, rejected]);
  const accepted = changes.length - rejected.size;

  const submit = useCallback(async () => {
    if (!input.trim() || busy) return;

    setBusy(true);
    setError(null);
    setCopied(false);

    try {
      const result = await restore(input);
      setTyped(input);
      setChanges(result.changes);
      setRejected(new Set());
    } catch {
      setError(text.offline);
    } finally {
      setBusy(false);
    }
  }, [busy, input, text.offline]);

  const toggle = (index: number) => {
    setRejected((current) => {
      const next = new Set(current);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
    setCopied(false);
  };

  const copy = async () => {
    await navigator.clipboard.writeText(output);
    setCopied(true);
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col gap-8 px-4 py-12 sm:px-6">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">duzelt</h1>
          <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">{text.tagline}</p>
        </div>
        <button
          type="button"
          onClick={() => setLanguage(language === "az" ? "en" : "az")}
          className="rounded-md border border-neutral-300 px-2.5 py-1 text-xs font-medium uppercase tracking-wide text-neutral-600 transition hover:border-neutral-400 hover:text-neutral-900 dark:border-neutral-700 dark:text-neutral-400 dark:hover:border-neutral-500 dark:hover:text-neutral-100"
        >
          {language === "az" ? "EN" : "AZ"}
        </button>
      </header>

      <p className="max-w-2xl text-sm leading-relaxed text-neutral-700 dark:text-neutral-300">
        {text.intro}
      </p>

      <section className="flex flex-col gap-3">
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) void submit();
          }}
          placeholder={text.placeholder}
          rows={5}
          className="w-full resize-y rounded-lg border border-neutral-300 bg-white px-4 py-3 text-base leading-relaxed outline-none transition focus:border-neutral-500 dark:border-neutral-700 dark:bg-neutral-900 dark:focus:border-neutral-500"
        />

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => void submit()}
            disabled={busy || !input.trim()}
            className="rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-neutral-700 disabled:cursor-not-allowed disabled:opacity-40 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200"
          >
            {busy ? text.working : text.restore}
          </button>
          <button
            type="button"
            onClick={() => setInput(EXAMPLE)}
            className="rounded-md border border-neutral-300 px-3 py-2 text-sm transition hover:border-neutral-400 dark:border-neutral-700 dark:hover:border-neutral-500"
          >
            {text.example}
          </button>
          {input && (
            <button
              type="button"
              onClick={() => {
                setInput("");
                setTyped("");
                setChanges([]);
              }}
              className="rounded-md px-3 py-2 text-sm text-neutral-500 transition hover:text-neutral-900 dark:hover:text-neutral-100"
            >
              {text.clear}
            </button>
          )}
        </div>
      </section>

      {error && (
        <p className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-200">
          {error}
        </p>
      )}

      {typed && !error && (
        <section className="flex flex-col gap-3">
          <div className="flex items-center justify-between gap-4">
            <h2 className="text-sm font-medium text-neutral-500 dark:text-neutral-400">
              {text.result}
              <span className="ml-2 text-neutral-400 dark:text-neutral-500">
                {changes.length === 0 ? text.noChanges : text.changes(accepted)}
              </span>
            </h2>
            <button
              type="button"
              onClick={() => void copy()}
              className="rounded-md border border-neutral-300 px-3 py-1.5 text-xs transition hover:border-neutral-400 dark:border-neutral-700 dark:hover:border-neutral-500"
            >
              {copied ? text.copied : text.copy}
            </button>
          </div>

          <output className="rounded-lg border border-neutral-200 bg-neutral-50 px-4 py-3 text-base leading-relaxed whitespace-pre-wrap dark:border-neutral-800 dark:bg-neutral-900/60">
            <Highlighted typed={typed} changes={changes} rejected={rejected} onToggle={toggle} />
          </output>
        </section>
      )}

      <section className="flex flex-col gap-3 border-t border-neutral-200 pt-6 text-sm dark:border-neutral-800">
        <h2 className="font-medium text-neutral-900 dark:text-neutral-100">{text.resultsTitle}</h2>
        <p className="text-neutral-600 dark:text-neutral-400">{text.results}</p>

        <table className="w-full max-w-lg border-collapse text-left">
          <thead className="text-xs uppercase tracking-wide text-neutral-500 dark:text-neutral-500">
            <tr>
              <th className="py-1 font-medium">{text.columnSystem}</th>
              <th className="py-1 font-medium">{text.columnAmbiguous}</th>
              <th className="py-1 font-medium">{text.columnSentences}</th>
            </tr>
          </thead>
          <tbody className="text-neutral-700 dark:text-neutral-300">
            {[
              [text.rowLexicon, "79.3%", "71.9%", false],
              [text.rowTagger, "93.8%", "86.7%", false],
              [text.rowHybrid, "93.8%", "88.1%", true],
            ].map(([name, ambiguous, sentences, highlight]) => (
              <tr
                key={String(name)}
                className={
                  highlight
                    ? "border-t border-neutral-200 font-medium text-neutral-900 dark:border-neutral-800 dark:text-neutral-100"
                    : "border-t border-neutral-200 dark:border-neutral-800"
                }
              >
                <td className="py-1.5">{name}</td>
                <td className="py-1.5 tabular-nums">{ambiguous}</td>
                <td className="py-1.5 tabular-nums">{sentences}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <p className="text-xs text-neutral-500 dark:text-neutral-500">{text.resultsCaveat}</p>
      </section>

      <footer className="mt-auto flex flex-col gap-3 border-t border-neutral-200 pt-6 text-sm text-neutral-600 dark:border-neutral-800 dark:text-neutral-400">
        <h2 className="font-medium text-neutral-900 dark:text-neutral-100">{text.howTitle}</h2>
        <p className="leading-relaxed">{text.how}</p>
        <p className="leading-relaxed">{text.ambiguity}</p>
        <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-neutral-500 dark:text-neutral-500">
          <a
            href="https://github.com/EmilTahirov24/duzelt"
            className="underline underline-offset-2 hover:text-neutral-900 dark:hover:text-neutral-100"
          >
            github.com/EmilTahirov24/duzelt
          </a>
          {model && <span>{text.running(model)}</span>}
        </p>
      </footer>
    </main>
  );
}

function Highlighted({
  typed,
  changes,
  rejected,
  onToggle,
}: {
  typed: string;
  changes: Change[];
  rejected: ReadonlySet<number>;
  onToggle: (index: number) => void;
}) {
  const pieces: React.ReactNode[] = [];
  let cursor = 0;

  changes.forEach((change, index) => {
    if (change.start > cursor) pieces.push(typed.slice(cursor, change.start));
    const kept = rejected.has(index);

    pieces.push(
      <button
        key={`${change.start}-${index}`}
        type="button"
        onClick={() => onToggle(index)}
        title={kept ? change.to : change.from}
        className={
          kept
            ? "cursor-pointer rounded px-0.5 text-neutral-500 line-through decoration-neutral-400"
            : "cursor-pointer rounded bg-emerald-100 px-0.5 underline decoration-emerald-500 decoration-2 underline-offset-2 dark:bg-emerald-500/15"
        }
      >
        {kept ? change.from : change.to}
      </button>,
    );

    cursor = change.end;
  });

  if (cursor < typed.length) pieces.push(typed.slice(cursor));
  return <>{pieces}</>;
}
