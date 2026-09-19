import { useState } from "react";

import results from "@/lib/schwa/results.json";
import { GITHUB_URL, type Strings } from "@/lib/strings";

const PAIRS = [
  ["c", "ç"],
  ["e", "ə"],
  ["g", "ğ"],
  ["i", "ı"],
  ["o", "ö"],
  ["s", "ş"],
  ["u", "ü"],
] as const;

/** The whole problem fits in seven tiles: each plain letter hides exactly one other. */
export function HowItWorks({ text }: { text: Strings }) {
  return (
    <section className="grid gap-10 md:grid-cols-2" aria-labelledby="how-title">
      <div className="flex flex-col gap-4">
        <h2 id="how-title" className="text-2xl font-semibold tracking-tight">
          {text.howTitle}
        </h2>
        <p className="leading-relaxed text-neutral-600 dark:text-neutral-400">{text.how}</p>

        <div className="mt-2 grid grid-cols-7 gap-2">
          {PAIRS.map(([plain, marked]) => (
            <div
              key={plain}
              className="flex flex-col items-center rounded-xl border border-neutral-200 py-3 dark:border-neutral-800"
            >
              <span className="text-lg text-neutral-400 dark:text-neutral-500">{plain}</span>
              <span className="text-xs text-neutral-300 dark:text-neutral-600">↓</span>
              <span className="text-2xl font-semibold text-emerald-600 dark:text-emerald-400">{marked}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-4">
        <h2 className="text-2xl font-semibold tracking-tight">{text.ambiguityTitle}</h2>
        <p className="leading-relaxed text-neutral-600 dark:text-neutral-400">{text.ambiguity}</p>

        <div className="mt-2 flex flex-col gap-2 rounded-2xl border border-neutral-200 p-5 dark:border-neutral-800">
          <p className="font-mono text-sm text-neutral-400">qiz</p>
          <div className="flex flex-wrap gap-3">
            <span className="rounded-lg bg-emerald-100/70 px-3 py-1.5 text-lg text-emerald-900 dark:bg-emerald-500/15 dark:text-emerald-200">
              qız <span className="text-sm opacity-60">· məktəbə getdi</span>
            </span>
            <span className="rounded-lg bg-neutral-100 px-3 py-1.5 text-lg text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300">
              qiz <span className="text-sm opacity-60">· sözü qədimdir</span>
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}

// Written by scripts/evaluate.py and copied in by scripts/sync.mjs, so the page shows the
// numbers of the last evaluation and nothing typed by hand.
const DOMAINS = [
  { split: "test", label: "domainWikipedia", caption: "resultsWikipedia" },
  { split: "web_test", label: "domainWeb", caption: "resultsWeb" },
] as const;

const ROWS = [
  { key: "rowLexicon", system: "lexicon" },
  { key: "rowTagger", system: "tagger" },
  { key: "rowHybrid", system: "hybrid" },
] as const;

type Split = (typeof DOMAINS)[number]["split"];
type Rate = "ambiguous_accuracy" | "sentence_accuracy";

/**
 * The measured numbers on both kinds of text, each with a bar so the difference reads at a
 * glance. Switching the text moves the bars rather than swapping the table: what changes
 * between Wikipedia and the web is the point.
 */
export function Results({ text }: { text: Strings }) {
  const [split, setSplit] = useState<Split>("test");
  const domain = DOMAINS.find((item) => item.split === split) ?? DOMAINS[0];
  const measured = results[split];

  return (
    <section className="flex flex-col gap-5" aria-labelledby="results-title">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-2">
          <h2 id="results-title" className="text-2xl font-semibold tracking-tight">
            {text.resultsTitle}
          </h2>
          <p className="text-neutral-600 dark:text-neutral-400">{text[domain.caption](measured.sentences)}</p>
        </div>
        <div role="tablist" aria-label={text.resultsTitle} className="flex rounded-xl bg-neutral-100 p-1 dark:bg-neutral-800/70">
          {DOMAINS.map((item) => (
            <button
              key={item.split}
              type="button"
              role="tab"
              aria-selected={item.split === split}
              onClick={() => setSplit(item.split)}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                item.split === split
                  ? "bg-white text-neutral-900 shadow-sm dark:bg-neutral-900 dark:text-neutral-100"
                  : "text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200"
              }`}
            >
              {text[item.label]}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-4" role="tabpanel">
        <div className="grid grid-cols-[6.5rem_1fr_1fr] gap-4 text-xs uppercase tracking-wide text-neutral-500 sm:grid-cols-[11rem_1fr_1fr]">
          <span>{text.columnSystem}</span>
          <span>{text.columnAmbiguous}</span>
          <span>{text.columnSentences}</span>
        </div>
        {ROWS.map((row) => {
          const best = row.system === "hybrid";
          const scores = measured.systems[row.system];
          return (
            <div key={row.key} className="grid grid-cols-[6.5rem_1fr_1fr] items-center gap-4 sm:grid-cols-[11rem_1fr_1fr]">
              <span className={best ? "font-semibold" : "text-neutral-600 dark:text-neutral-400"}>
                {text[row.key]}
              </span>
              <Bar rate="ambiguous_accuracy" scores={scores} best={best} />
              <Bar rate="sentence_accuracy" scores={scores} best={best} />
            </div>
          );
        })}
      </div>

      <p className="text-sm text-neutral-500 dark:text-neutral-400">
        {text.intervalNote} {text.resultsCaveat}
      </p>
    </section>
  );
}

type Scores = Record<Rate, number> & { intervals: Record<Rate, number[]> };

function Bar({ rate, scores, best }: { rate: Rate; scores: Scores; best: boolean }) {
  const percent = (value: number) => (value * 100).toFixed(1);
  const [low, high] = scores.intervals[rate];
  return (
    <div className="flex items-center gap-3">
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-neutral-100 dark:bg-neutral-800">
        <div
          className={`h-full rounded-full transition-[width] duration-700 ease-out motion-reduce:transition-none ${
            best ? "bg-emerald-500" : "bg-neutral-400 dark:bg-neutral-600"
          }`}
          style={{ width: `${scores[rate] * 100}%` }}
        />
      </div>
      <span className="flex w-14 flex-col items-end tabular-nums leading-tight">
        <span className={best ? "font-semibold" : ""}>{percent(scores[rate])}%</span>
        <span className="text-[10px] text-neutral-400 dark:text-neutral-500">
          {percent(low)}–{percent(high)}
        </span>
      </span>
    </div>
  );
}

/** Three ways in: while typing, in code, or by reading how it was built. */
export function GetIt({ text }: { text: Strings }) {
  const card =
    "flex flex-col gap-3 rounded-2xl border border-neutral-200 p-6 transition hover:border-emerald-400 dark:border-neutral-800 dark:hover:border-emerald-500/60";

  return (
    <section className="flex flex-col gap-5" aria-labelledby="get-title">
      <h2 id="get-title" className="text-2xl font-semibold tracking-tight">
        {text.getTitle}
      </h2>
      <div className="grid gap-4 md:grid-cols-3">
        <div className={card}>
          <h3 className="font-semibold">{text.getExtensionTitle}</h3>
          <p className="flex-1 text-sm leading-relaxed text-neutral-600 dark:text-neutral-400">
            {text.getExtension}
          </p>
          <a href={`${GITHUB_URL}/tree/main/apps/extension`} className="text-sm font-medium text-emerald-700 hover:underline dark:text-emerald-400">
            {text.getExtensionCta} →
          </a>
        </div>
        <div className={card}>
          <h3 className="font-semibold">{text.getPythonTitle}</h3>
          <p className="flex-1 text-sm leading-relaxed text-neutral-600 dark:text-neutral-400">{text.getPython}</p>
          <code className="rounded-lg bg-neutral-100 px-3 py-2 font-mono text-sm dark:bg-neutral-800">
            pip install &quot;schwa-az[onnx]&quot;
          </code>
        </div>
        <div className={card}>
          <h3 className="font-semibold">{text.getSourceTitle}</h3>
          <p className="flex-1 text-sm leading-relaxed text-neutral-600 dark:text-neutral-400">{text.getSource}</p>
          <a href={GITHUB_URL} className="text-sm font-medium text-emerald-700 hover:underline dark:text-emerald-400">
            {text.getSourceCta} →
          </a>
        </div>
      </div>
    </section>
  );
}
