import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "duzelt — privacy",
  description: "What the duzelt service and browser extension do with the text you give them.",
};

export default function PrivacyPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 px-4 py-12 text-neutral-800 sm:px-6 dark:text-neutral-200">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Privacy</h1>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          duzelt — Azerbaijani diacritic restoration
        </p>
      </header>

      <section className="flex flex-col gap-3 text-sm leading-relaxed">
        <h2 className="font-medium">What is sent</h2>
        <p>
          The text you ask to restore is sent to the service, which returns the restored text
          and the list of changed words. Nothing else is sent: no account, no identifiers, no
          page content.
        </p>

        <h2 className="mt-4 font-medium">What is kept</h2>
        <p>
          Nothing. The text is held in memory for the length of the request and is never
          written to disk or to the logs. The service records only how many characters
          arrived and how long the work took, which is what keeps it running and honest about
          its speed.
        </p>

        <h2 className="mt-4 font-medium">The browser extension</h2>
        <p>
          The extension has no permission for any website and installs no script that watches
          what you type. When you use the context menu or press the shortcut, a short function
          is placed into that one tab, reads the text you pointed at, puts the restored text
          back, and is gone. Outside that moment it cannot read the page.
        </p>
        <p>
          It stores one setting in your browser: the address of the service it talks to. You
          can point it at your own server, in which case no text reaches this one at all.
        </p>

        <h2 className="mt-4 font-medium">Source</h2>
        <p>
          All of this is verifiable:{" "}
          <a
            className="underline underline-offset-2"
            href="https://github.com/EmilTahirov24/duzelt"
          >
            github.com/EmilTahirov24/duzelt
          </a>
          .
        </p>
      </section>

      <a href="/" className="text-sm underline underline-offset-2">
        ← back
      </a>
    </main>
  );
}
