import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "duzelt — Azərbaycan hərflərini bərpa edir",
  description:
    "Restores Azerbaijani diacritics in text typed without them: sence neden basliyaq becomes səncə nədən başlayaq.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="az">
      <body className="bg-white text-neutral-900 antialiased dark:bg-neutral-950 dark:text-neutral-100">
        {children}
      </body>
    </html>
  );
}
