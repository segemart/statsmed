import './globals.css';

export const metadata = {
  title: 'Statsmed - Statistics for Medical Data',
  description: 'Upload data, run statistical tests, and save your analysis results.',
  icons: {
    icon: '/favicon.png',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
