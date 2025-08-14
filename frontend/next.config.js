/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  swcMinify: true,
  async rewrites() {
    return [
      {
        source: '/api/backend/:path*',
        destination: `${process.env.BACKEND_URL || 'http://localhost:8000'}/api/:path*`,
      },
    ]
  },
  env: {
    NEXT_PUBLIC_BACKEND_URL: process.env.BACKEND_URL || 'http://localhost:8000',
  },
}

module.exports = nextConfig