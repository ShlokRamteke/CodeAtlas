import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Project Archaeologist — AI Software Understanding",
  description:
    "Understand unfamiliar software before you change it. Combines current architecture, historical context, and bounded AI reasoning.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-background text-foreground antialiased selection:bg-primary/20">
        {children}
      </body>
    </html>
  );
}
