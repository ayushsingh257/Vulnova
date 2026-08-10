import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Vulnova | Autonomous AI Application Security Platform",
  description:
    "Enterprise AI-powered application security platform providing autonomous vulnerability intelligence, attack surface discovery, secure scanning, and SOC workflows.",
  keywords: [
    "Application Security",
    "AppSec Platform",
    "Autonomous AI Security",
    "Vulnerability Management",
    "Attack Surface Discovery",
    "Container Sandbox Scanning",
    "CVSS 4.0 Intelligence",
    "SOC Operations",
  ],
  authors: [{ name: "Vulnova Security Engineering" }],
  openGraph: {
    title: "Vulnova | Autonomous AI Application Security Platform",
    description:
      "Enterprise AI-powered application security platform providing autonomous vulnerability intelligence, attack surface discovery, secure scanning, and SOC workflows.",
    url: "https://vulnova.com",
    siteName: "Vulnova Security",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Vulnova | Autonomous AI Application Security Platform",
    description:
      "Enterprise AI-powered application security platform providing autonomous vulnerability intelligence, attack surface discovery, secure scanning, and SOC workflows.",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-zinc-950 text-zinc-100 antialiased selection:bg-red-500/30 selection:text-red-200">
        {children}
      </body>
    </html>
  );
}
