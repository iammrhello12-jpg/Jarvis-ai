import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "JARVIS AI - Your Intelligent Assistant",
  description: "An advanced AI assistant that helps you with all your life problems. Powered by cutting-edge language models.",
  keywords: ["AI", "assistant", "chatbot", "JARVIS", "artificial intelligence"],
  authors: [{ name: "JARVIS AI" }],
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0a0a0a",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="bg-[var(--background)]">
      <body className="antialiased">{children}</body>
    </html>
  );
}
