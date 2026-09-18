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

const ROWS = [
  { key: "rowLexicon", ambiguous: 79.3, sentences: 71.9 },
  { key: "rowTagger", ambiguous: 93.8, sentences: 86.7 },
  { key: "rowHybrid", ambiguous: 93.8, sentences: 88.1 },
] as const;

/** The measured numbers, each with a bar so the difference reads at a glance. */
export function Results({ text }: { text: Strings }) {
  return (
    <section className="flex flex-col gap-5" aria-labelledby="results-title">
      <div className="flex flex-col gap-2">
        <h2 id="results-title" className="text-2xl font-semibold tracking-tight">
          {text.resultsTitle}
        </h2>
        <p className="text-neutral-600 dark:text-neutral-400">{text.results}</p>
      </div>

      <div className="flex flex-col gap-4">
        <div className="grid grid-cols-[8rem_1fr_1fr] gap-4 text-xs uppercase tracking-wide text-neutral-500 sm:grid-cols-[11rem_1fr_1fr]">
          <span>{text.columnSystem}</span>
          <span>{text.columnAmbiguous}</span>
          <span>{text.columnSentences}</span>
        </div>
        {ROWS.map((row) => {
          const best = row.key === "rowHybrid";
          return (
            <div key={row.key} className="grid grid-cols-[8rem_1fr_1fr] items-center gap-4 sm:grid-cols-[11rem_1fr_1fr]">
              <span className={best ? "font-semibold" : "text-neutral-600 dark:text-neutral-400"}>
                {text[row.key]}
              </span>
              <Bar value={row.ambiguous} best={best} />
              <Bar value={row.sentences} best={best} />
            </div>
          );
        })}
      </div>

      <p className="text-sm text-neutral-500 dark:text-neutral-400">{text.resultsCaveat}</p>
    </section>
  );
}

function Bar({ value, best }: { value: number; best: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-neutral-100 dark:bg-neutral-800">
        <div
          className={`h-full rounded-full ${best ? "bg-emerald-500" : "bg-neutral-400 dark:bg-neutral-600"}`}
          style={{ width: `${value}%` }}
        />
      </div>
      <span className={`w-12 text-right tabular-nums ${best ? "font-semibold" : ""}`}>{value}%</span>
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
