import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Schwa — privacy",
  description: "What the Schwa demo page, browser extension and service do with your text.",
};

export default function PrivacyPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 px-4 py-12 text-neutral-800 sm:px-6 dark:text-neutral-200">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Privacy</h1>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          Schwa — Azerbaijani diacritic restoration
        </p>
      </header>

      <section className="flex flex-col gap-3 text-sm leading-relaxed">
        <h2 className="font-medium">The demo page and the browser extension</h2>
        <p>
          Both carry the model and run it in your browser. The text you restore is never sent
          anywhere: there is no server behind them that could receive it, and they work with
          no connection once loaded. Nothing is stored - no text, no settings, no account, no
          identifiers.
        </p>
        <p>
          The extension asks for no permission for any website and installs no script that
          watches what you type. When you use the context menu or press the shortcut, a short
          function is placed into that one tab, reads the text you pointed at, puts the
          restored text back, and is gone. Outside that moment it cannot read the page.
        </p>

        <h2 className="mt-4 font-medium">The optional service</h2>
        <p>
          The project also contains an HTTP service for people who want to restore text from
          their own code. It is not used by the page or the extension. If you run it, the text
          sent to it is held in memory for the length of the request and never written to disk
          or to the logs. The only thing it remembers, in memory, is the address and time of
          recent requests, which its rate limit counts.
        </p>

        <h2 className="mt-4 font-medium">Source</h2>
        <p>
          All of this is verifiable:{" "}
          <a
            className="underline underline-offset-2"
            href="https://github.com/EmilTahirov24/schwa"
          >
            github.com/EmilTahirov24/schwa
          </a>
          .
        </p>
      </section>

      <Link href="/" className="text-sm underline underline-offset-2">
        ← back
      </Link>
    </main>
  );
}
