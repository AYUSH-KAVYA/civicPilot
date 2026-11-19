"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import {
  Activity,
  ShieldAlert,
  Sliders,
  BarChart3,
  FileText,
  UserCheck,
} from "lucide-react";

function OfficerNav({ pathname }: { pathname: string }) {
  const navItems = [
    { href: "/officer/cases", label: "Live Queue", icon: Activity },
    { href: "/officer/approvals", label: "Approvals & Review", icon: ShieldAlert },
    { href: "/officer/demo", label: "Demo Scenarios", icon: Sliders },
    { href: "/officer/metrics", label: "Metrics & Evaluation", icon: BarChart3 },
  ];

  return (
    <div className="border-b bg-white dark:bg-slate-900 sticky top-16 z-40 shadow-xs">
      <div className="container mx-auto px-4 sm:px-6 flex items-center justify-between h-12">
        <div className="flex items-center space-x-1 sm:space-x-3 text-xs sm:text-sm font-semibold">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active =
              pathname === item.href ||
              (item.href !== "/officer/cases" && pathname.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-colors ${
                  active
                    ? "bg-blue-100 text-blue-900 font-bold dark:bg-blue-950/60 dark:text-blue-200"
                    : "text-muted-foreground hover:text-foreground hover:bg-slate-100 dark:hover:bg-slate-800"
                }`}
              >
                <Icon
                  className={`h-3.5 w-3.5 ${
                    active ? "text-blue-600 dark:text-blue-400" : "text-muted-foreground"
                  }`}
                />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>

        <div className="hidden sm:flex items-center gap-2 text-xs">
          <span className="font-mono text-muted-foreground">Officer On-Duty:</span>
          <Badge
            variant="outline"
            className="border-blue-300 text-blue-700 bg-blue-50/50 dark:bg-blue-950/30"
          >
            Badge #409 (Chen)
          </Badge>
        </div>
      </div>
    </div>
  );
}

export default function OfficerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <Suspense fallback={<div className="container mx-auto px-4 py-16 text-center text-sm text-muted-foreground" role="status">Loading officer console…</div>}>
      <OfficerLayoutContent>{children}</OfficerLayoutContent>
    </Suspense>
  );
}

function OfficerLayoutContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const isLoginPage = pathname === "/officer/login";
  const [hasOfficerToken, setHasOfficerToken] = useState(false);
  const isAuthenticated = isLoginPage || hasOfficerToken;

  useEffect(() => {
    if (isLoginPage) return;
    const token = localStorage.getItem("officer_token");
    if (!token) {
      router.replace("/officer/login");
      return;
    }
    // Defer the browser-only session update until after this subscription effect completes.
    queueMicrotask(() => setHasOfficerToken(true));
  }, [isLoginPage, router]);

  return (
    <div className="flex flex-col min-h-[calc(100vh-4rem)]">
      <OfficerNav pathname={pathname} />
      <div className="flex-1">
        {isAuthenticated ? children : <div className="container mx-auto px-4 py-16 text-center text-sm text-muted-foreground" role="status">Checking officer session…</div>}
      </div>
    </div>
  );
}
