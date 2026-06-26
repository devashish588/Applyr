import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Applyr — Job Search Operating System",
  description: "Your career command center. Discover jobs, tailor resumes, track applications, and connect with recruiters — all from one place.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="color-scheme" content="dark" />
      </head>
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
