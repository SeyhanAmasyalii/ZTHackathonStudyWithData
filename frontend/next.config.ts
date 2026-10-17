import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Azure App Service: .next/standalone + `node server.js` (scripts/package_azure.py paketler).
  output: "standalone",
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
