import './globals.css';

export const metadata = {
  title: 'Video Thumbnail Bot — Dashboard',
  description: 'Real-time monitoring dashboard for the Video Thumbnail Generator Telegram Bot. Track downloads, thumbnail generation, and uploads.',
};

export const viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: '#0f1114',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        {/* Google Fonts: Outfit (display) + DM Sans (body) + JetBrains Mono (mono) */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;700&family=Outfit:wght@200;800&display=swap"
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
