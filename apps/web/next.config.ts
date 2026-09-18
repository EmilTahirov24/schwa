import type { NextConfig } from "next";

// The demo is a static site: the model runs in the visitor's browser, so there is no server
// to deploy and it can be hosted anywhere that serves files. On GitHub Pages it lives under
// /schwa, which is what NEXT_PUBLIC_BASE_PATH is for; locally it is empty.
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

const nextConfig: NextConfig = {
  output: "export",
  basePath,
  trailingSlash: true,
};

export default nextConfig;
