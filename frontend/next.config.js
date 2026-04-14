const publicApiUrl = process.env.NEXT_PUBLIC_API_URL || "/api";
const internalApiUrl = process.env.INTERNAL_API_URL || "http://localhost:8000";

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  env: {
    NEXT_PUBLIC_API_URL: publicApiUrl,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${internalApiUrl}/api/:path*`,
      },
      {
        source: "/storage/:path*",
        destination: `${internalApiUrl}/storage/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
