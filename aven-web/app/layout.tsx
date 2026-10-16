import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AVEN",
  description: "Denial appeals and revenue recovery for medical practices",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans antialiased">{children}</body>
    </html>
  );
}
