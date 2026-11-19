"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/stores/authStore";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  ShieldAlert,
  Bot,
  Activity,
  Sliders,
  BarChart3,
  FileText,
  Radio,
  LogIn,
  LogOut,
  ChevronRight,
} from "lucide-react";

export function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, logout } = useAuthStore();
  const mockActive = process.env.NEXT_PUBLIC_USE_MOCKS === "true" || process.env.NEXT_PUBLIC_USE_MOCKS === "1";

  const navLinks = [
    { href: "/", label: "Overview", icon: Bot },
    { href: "/report", label: "Report Issue", icon: FileText },
    { href: "/officer/cases", label: "Officer Queue", icon: Activity },
    { href: "/officer/approvals", label: "Approvals", icon: ShieldAlert },
    { href: "/officer/demo", label: "Demo Scenarios", icon: Sliders },
    { href: "/officer/metrics", label: "Metrics & Eval", icon: BarChart3 },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 shadow-xs">
      <div className="container mx-auto flex h-16 items-center justify-between px-4 sm:px-6">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2.5 font-bold tracking-tight text-lg text-primary hover:opacity-90 transition-opacity">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 text-white shadow-sm">
              <Radio className="h-5 w-5 animate-pulse" />
            </div>
            <div className="flex flex-col">
              <span className="leading-tight font-extrabold text-blue-900 dark:text-blue-100">
                Civic<span className="text-blue-600 dark:text-blue-400">Pilot</span>
              </span>
              <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-widest">
                Autonomous Municipal Loop
              </span>
            </div>
          </Link>

          <Badge variant={mockActive ? "outline" : "secondary"} className="ml-2 hidden sm:inline-flex text-[11px] font-mono border-blue-200 bg-blue-50/50 text-blue-700 dark:bg-blue-950/30 dark:text-blue-300">
            {mockActive ? "MOCK MODE (NO BACKEND REQ)" : "LIVE API"}
          </Badge>
        </div>

        {/* Navigation items */}
        <nav className="hidden md:flex items-center space-x-1 lg:space-x-2 text-sm font-medium">
          {navLinks.map((link) => {
            const Icon = link.icon;
            const isActive = pathname === link.href || (link.href !== "/" && pathname.startsWith(link.href));
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-colors ${
                  isActive
                    ? "bg-blue-100 text-blue-900 font-semibold dark:bg-blue-950/60 dark:text-blue-200"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                }`}
              >
                <Icon className={`h-4 w-4 ${isActive ? "text-blue-600 dark:text-blue-400" : "text-muted-foreground"}`} />
                <span>{link.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Right action / Auth */}
        <div className="flex items-center gap-2">
          {isAuthenticated ? (
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground hidden lg:inline">
                Officer Chen (Badge #409)
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  logout();
                  router.push("/officer/login");
                }}
                className="gap-1.5 text-xs text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950/20"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span>Exit</span>
              </Button>
            </div>
          ) : (
            <Link href="/officer/login">
              <Button size="sm" variant="outline" className="gap-1.5 text-xs">
                <LogIn className="h-3.5 w-3.5 text-blue-600" />
                <span>Officer Login</span>
              </Button>
            </Link>
          )}

          <Link href="/report" className="hidden sm:inline-flex">
            <Button size="sm" className="bg-blue-600 hover:bg-blue-700 text-white gap-1 text-xs shadow-xs">
              <span>Report Grievance</span>
              <ChevronRight className="h-3 w-3" />
            </Button>
          </Link>
        </div>
      </div>
    </header>
  );
}
