/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",       // static export for Netlify
  trailingSlash: true,    // Netlify serves index.html from directories
};

module.exports = nextConfig;
