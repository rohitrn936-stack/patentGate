import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PatentGate",
  description: "AI-powered patent risk research and product redesign support",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
