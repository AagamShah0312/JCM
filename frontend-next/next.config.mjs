/** @type {import('next').NextConfig} */
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
console.log('[next.config] proxying /api/* to', API);

const nextConfig = {
  reactStrictMode: true,
  // Keep trailing slashes so the /api proxy matches Django routes without a
  // redirect loop. Next's `:path*` capture strips trailing slashes, so the
  // destination re-adds them (all Django API URLs end with '/').
  trailingSlash: true,
  // Standalone output for the Docker image.
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${API}/api/:path*/`,
      },
      {
        source: '/media/:path*',
        destination: `${API}/media/:path*/`,
      },
    ];
  },
};

export default nextConfig;
