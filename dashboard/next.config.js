/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  // Allow connecting to the bot WebSocket server
  async rewrites() {
    return [
      {
        source: '/ws',
        destination: `${process.env.NEXT_PUBLIC_WS_URL || 'http://bot:8765'}/ws`,
      },
      {
        source: '/api/bot/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://bot:8765'}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
