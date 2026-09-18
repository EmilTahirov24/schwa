import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Copied in by scripts/sync.mjs: the onnxruntime build and the extension's code, which
    // is linted and tested where it lives.
    "public/ort/**",
    "src/lib/schwa/**",
  ]),
]);

export default eslintConfig;
