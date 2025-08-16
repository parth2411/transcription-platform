// frontend/next.config.js
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Remove the experimental.appDir since it's now default in Next.js 14+
  images: {
    domains: ['localhost', 'your-production-domain.com'],
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },
}

module.exports = nextConfig