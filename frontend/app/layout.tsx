import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Applyr — AI Job Application Mission Control",
  description: "Transparent AI-powered job application platform. Upload your resume, discover jobs, tailor applications, and track every step.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
