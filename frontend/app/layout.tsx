import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Vulnova — Enterprise AI Application Security Platform",
  description:
    "AI-powered Enterprise Application Security Platform for continuous attack surface discovery, dynamic security testing, and automated vulnerability triage.",
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
