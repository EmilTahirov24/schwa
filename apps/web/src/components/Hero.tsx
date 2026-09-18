"use client";

import { useEffect, useState, useSyncExternalStore } from "react";

import { DEMO_PAIRS, type Strings } from "@/lib/strings";

const LETTER_DELAY = 110;
const HOLD = 2200;
const BEFORE_FIRST = 700;

/**
 * The first thing on the page: a sentence typed without its letters, fixing itself one
 * letter at a time. It says what the tool does before anyone has read a word.
 */
export function Hero({ text }: { text: Strings }) {
  const [pairIndex, setPairIndex] = useState(0);
  const [revealed, setRevealed] = useState(0);

  const [typed, restored] = DEMO_PAIRS[pairIndex];
  const changed = [...typed]
    .map((char, index) => (char !== restored[index] ? index : -1))
    .filter((index) => index >= 0);

  const reduce = usePrefersReducedMotion();

  useEffect(() => {
    // With reduced motion the sentences still change, but each arrives already restored.
    if (!reduce && revealed < changed.length) {
      const wait = revealed === 0 ? BEFORE_FIRST : LETTER_DELAY;
      const timer = setTimeout(() => setRevealed((count) => count + 1), wait);
      return () => clearTimeout(timer);
    }

    const timer = setTimeout(() => {
      setPairIndex((index) => (index + 1) % DEMO_PAIRS.length);
      setRevealed(0);
    }, HOLD);
    return () => clearTimeout(timer);
  }, [revealed, changed.length, reduce]);

  const shown = new Set(reduce ? changed : changed.slice(0, revealed));

  return (
    <section className="flex flex-col gap-6 pt-6 sm:pt-12">
      <p className="text-sm font-medium tracking-wide text-emerald-600 dark:text-emerald-400">
        ə · Schwa
      </p>
      <h1 className="text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
        {text.heroTitle}
      </h1>
      <p className="max-w-2xl text-lg leading-relaxed text-pretty text-neutral-600 dark:text-neutral-400">
        {text.heroLead}
      </p>

      <div
        className="rounded-2xl border border-neutral-200 bg-neutral-50 px-5 py-6 dark:border-neutral-800 dark:bg-neutral-900/60 sm:px-8 sm:py-8"
        aria-label={`${typed} → ${restored}`}
      >
        <p
          key={pairIndex}
          className="line-in font-medium tracking-tight text-2xl sm:text-4xl"
          aria-hidden="true"
        >
          {[...typed].map((char, index) =>
            shown.has(index) ? (
              <span key={`${index}-on`} className="letter-arrive text-emerald-600 dark:text-emerald-400">
                {restored[index]}
              </span>
            ) : (
              <span key={`${index}-off`}>{char}</span>
            ),
          )}
          <span className="ml-1 inline-block h-[0.9em] w-[2px] translate-y-[0.1em] animate-pulse bg-neutral-400" />
        </p>
      </div>

      <p className="flex items-center gap-2 text-sm text-neutral-500 dark:text-neutral-400">
        <span className="inline-block h-2 w-2 rounded-full bg-emerald-500" />
        {text.heroPrivate}
      </p>
    </section>
  );
}

const REDUCED_MOTION = "(prefers-reduced-motion: reduce)";

/** Whether the visitor asked their system for less motion, kept in sync if they change it. */
function usePrefersReducedMotion(): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const query = window.matchMedia(REDUCED_MOTION);
      query.addEventListener("change", onChange);
      return () => query.removeEventListener("change", onChange);
    },
    () => window.matchMedia(REDUCED_MOTION).matches,
    () => false,
  );
}
