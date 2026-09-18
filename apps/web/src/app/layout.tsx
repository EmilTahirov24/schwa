import type { Metadata } from "next";
import { Inter } from "next/font/google";

import "./globals.css";

// latin-ext carries ə, ğ, ı, ş, ç, ö and ü; without it half of every restored word would
// fall back to another font mid-word.
const inter = Inter({ subsets: ["latin", "latin-ext"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Schwa — Azərbaycan hərflərini bərpa edir",
  description:
    "Restores Azerbaijani letters in text typed without them — sence neden basliyaq becomes səncə nədən başlıyaq. The model runs in your browser.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="az" className={inter.variable}>
      <body className="bg-white text-neutral-900 antialiased selection:bg-emerald-200 dark:bg-neutral-950 dark:text-neutral-100 dark:selection:bg-emerald-800">
        {children}
      </body>
    </html>
  );
}
