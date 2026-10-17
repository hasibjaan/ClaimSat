/** @type {import('next').NextConfig} */
const nextConfig = {
  // Self-contained server (.next/standalone/server.js) for the Cloud Run Docker image.
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
