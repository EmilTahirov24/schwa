"use client";

import Link from "next/link";
import { useState } from "react";

import { Hero } from "@/components/Hero";
import { LiveEditor } from "@/components/LiveEditor";
import { GetIt, HowItWorks, Results } from "@/components/Sections";
import { GITHUB_URL, strings, type Language } from "@/lib/strings";

export default function Page() {
  const [language, setLanguage] = useState<Language>("az");
  const text = strings[language];

  return (
    <div className="mx-auto flex min-h-screen max-w-5xl flex-col px-4 sm:px-8">
      <nav className="flex items-center justify-between py-5">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-neutral-900 text-lg text-white dark:bg-white dark:text-neutral-900">
            ə
          </span>
          Schwa
        </Link>
        <div className="flex items-center gap-2">
          <a
            href={GITHUB_URL}
            className="rounded-lg px-3 py-1.5 text-sm text-neutral-600 transition hover:text-neutral-900 dark:text-neutral-400 dark:hover:text-neutral-100"
          >
            GitHub
          </a>
          <button
            type="button"
            onClick={() => setLanguage(language === "az" ? "en" : "az")}
            className="rounded-lg border border-neutral-300 px-2.5 py-1 text-xs font-semibold tracking-wide text-neutral-600 transition hover:border-neutral-500 hover:text-neutral-900 dark:border-neutral-700 dark:text-neutral-400 dark:hover:border-neutral-500 dark:hover:text-neutral-100"
            aria-label={language === "az" ? "Switch to English" : "Azərbaycancaya keç"}
          >
            {language === "az" ? "EN" : "AZ"}
          </button>
        </div>
      </nav>

      <main className="flex flex-1 flex-col gap-20 pb-20 sm:gap-24">
        <Hero text={text} />
        <LiveEditor text={text} />
        <HowItWorks text={text} />
        <Results text={text} />
        <GetIt text={text} />
      </main>

      <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-neutral-200 py-6 text-sm text-neutral-500 dark:border-neutral-800 dark:text-neutral-400">
        <span>
          Schwa · {text.madeBy} · MIT
        </span>
        <div className="flex gap-4">
          <Link href="/privacy/" className="hover:text-neutral-900 dark:hover:text-neutral-100">
            {text.privacy}
          </Link>
          <a href={GITHUB_URL} className="hover:text-neutral-900 dark:hover:text-neutral-100">
            GitHub
          </a>
        </div>
      </footer>
    </div>
  );
}
