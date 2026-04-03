import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PrivateGPT Secure RAG",
  description:
    "Secure multi-tenant document intelligence with private retrieval-augmented generation.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
