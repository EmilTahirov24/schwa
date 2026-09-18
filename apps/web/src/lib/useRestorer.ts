"use client";

import { useEffect, useState } from "react";

import { loadRestorer, type Restorer } from "@/lib/restorer";

const base = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

/** The files the model needs, in the order they matter for the progress bar. */
const FILES = [
  `${base}/ort/ort-wasm-simd-threaded.wasm`,
  `${base}/model/tagger.onnx`,
  `${base}/model/lexicon.tsv.gz`,
];

export type RestorerState =
  | { status: "loading"; loaded: number; total: number }
  | { status: "ready"; restorer: Restorer }
  | { status: "failed" };

/**
 * Download the model while showing real progress, then load it.
 *
 * The files are fetched here first, counting bytes as they arrive, so the page can say
 * "4.1 / 18.3 MB" instead of spinning. The runtime then asks for the same URLs and gets
 * them from the browser's cache rather than the network.
 */
export function useRestorer(): RestorerState {
  const [state, setState] = useState<RestorerState>({ status: "loading", loaded: 0, total: 0 });

  useEffect(() => {
    let cancelled = false;

    async function download() {
      const responses = await Promise.all(FILES.map((url) => fetch(url)));
      if (responses.some((response) => !response.ok)) throw new Error("missing model files");

      const total = responses.reduce(
        (sum, response) => sum + Number(response.headers.get("content-length") ?? 0),
        0,
      );
      let loaded = 0;
      let lastPaint = 0;

      await Promise.all(
        responses.map(async (response) => {
          const reader = response.body?.getReader();
          if (!reader) return;
          for (;;) {
            const { done, value } = await reader.read();
            if (done) break;
            loaded += value.byteLength;
            // Repaint at most every 80 ms: progress events arrive far faster than that.
            const now = performance.now();
            if (!cancelled && now - lastPaint > 80) {
              lastPaint = now;
              setState({ status: "loading", loaded, total });
            }
          }
        }),
      );
    }

    download()
      .catch(() => undefined) // a failed preload only costs the progress bar
      .then(() => loadRestorer())
      .then((restorer) => {
        if (cancelled) return;
        setState(restorer ? { status: "ready", restorer } : { status: "failed" });
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}

export function megabytes(bytes: number): string {
  return `${(bytes / 1e6).toFixed(1)} MB`;
}
