import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";

import "./globals.css";
import SiteNav from "./components/nav";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "AI LMS · AI-powered corporate learning",
    template: "%s · AI LMS",
  },
  description:
    "AI-powered corporate learning management system: courses, assignments, progress and AI-generated training.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-white text-zinc-900">
        <SiteNav />
        <div className="flex-1">{children}</div>
        <footer className="border-t border-[var(--border)] bg-[var(--surface-muted)]">
          <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-8 text-sm text-zinc-500 sm:flex-row sm:items-center sm:justify-between sm:px-6">
            <p>AI LMS · Local development build</p>
            <nav aria-label="Footer" className="flex flex-wrap gap-x-5 gap-y-2">
              <Link href="/courses" className="hover:text-[var(--brand)]">
                Catalog
              </Link>
              <Link href="/learning" className="hover:text-[var(--brand)]">
                My Learning
              </Link>
              <Link href="/manage" className="hover:text-[var(--brand)]">
                Manage
              </Link>
              <Link href="/manage/studio" className="hover:text-[var(--brand)]">
                AI Studio
              </Link>
            </nav>
          </div>
        </footer>
      </body>
    </html>
  );
}
