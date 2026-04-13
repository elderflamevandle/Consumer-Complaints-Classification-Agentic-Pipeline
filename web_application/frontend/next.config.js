/** @type {import('next').NextConfig} */
const nextConfig = {
  // Produce a self-contained Node.js server bundle — required for the
  // multi-stage Docker image (copies .next/standalone + .next/static).
  output: 'standalone',

  // Strip server-identifying headers from all responses
  poweredByHeader: false,

  // Strict mode for React — catches common issues during development
  reactStrictMode: true,

  // API proxy rewrites for local development only.
  // In Docker, NEXT_PUBLIC_API_URL=http://backend:8000 is set via
  // docker-compose and the Axios client uses it directly — no rewrite needed.
  async rewrites() {
    if (process.env.NODE_ENV === 'production') return []
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/:path*`,
      },
    ]
  },

  // Security headers applied to every route
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-DNS-Prefetch-Control', value: 'on' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
        ],
      },
    ]
  },
}

module.exports = nextConfig
