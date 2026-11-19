import type { Metadata } from "next";
import { Suspense } from "react";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Navbar } from "@/components/layout/Navbar";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "CivicPilot - Autonomous Multi-Agent Grievance Resolution",
  description:
    "End-to-end municipal grievance resolution powered by autonomous agents: Perceive, Reason, Plan, Act, Evaluate, Adapt.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <head>
        <link
          rel="stylesheet"
          href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
          integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
          crossOrigin=""
        />
      </head>
      <body className="min-h-full flex flex-col bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
        <Suspense fallback={<div className="h-16 border-b bg-background" />}>
          <Navbar />
        </Suspense>
        <main className="flex-1">{children}</main>
        <footer className="border-t bg-white dark:bg-slate-900 py-6 text-center text-xs text-muted-foreground">
          <div className="container mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
            <p>
              CivicPilot &copy; 2026 &mdash; Built for autonomous municipal service delivery across Water, Roads, Sanitation, Electricity, Parks, and Public Health.
            </p>
            <div className="flex items-center gap-4 text-xs font-mono">
              <span className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-ping inline-block" />
                Loop: Perceive &rarr; Adapt
              </span>
              <span>Slide 12 Benchmarks Active</span>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
