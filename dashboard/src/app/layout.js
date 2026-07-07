import './globals.css';

export const metadata = {
  title: 'Video Thumbnail Bot — Dashboard',
  description: 'Real-time monitoring dashboard for the Video Thumbnail Generator Telegram Bot. Track downloads, thumbnail generation, and uploads.',
  viewport: 'width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no',
  themeColor: '#0f0f1a',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        {/* Google Fonts: Inter + JetBrains Mono */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap"
          rel="stylesheet"
        />
        {/* Telegram Web App SDK */}
        <script src="https://telegram.org/js/telegram-web-app.js" defer></script>
      </head>
      <body>
        {children}
      </body>
    </html>
  );
}
