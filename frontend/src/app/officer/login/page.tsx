"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Shield, KeyRound, ArrowRight, Lock, CheckCircle2 } from "lucide-react";
import { useAuthStore } from "@/lib/stores/authStore";
import { login } from "@/lib/api/endpoints";

export default function OfficerLoginPage() {
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const { login: setAuthToken } = useAuthStore();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const res = await login(password);
      if (res.data?.token) {
        setAuthToken(res.data.token);
        router.push("/officer/cases");
      }
    } catch (err: any) {
      setError(err.response?.data?.error?.message || "Invalid officer credentials");
    } finally {
      setLoading(false);
    }
  };

  const handleDemoQuickLogin = async () => {
    setLoading(true);
    const res = await login("officer123");
    if (res.data?.token) {
      setAuthToken(res.data.token);
      router.push("/officer/cases");
    }
    setLoading(false);
  };

  return (
    <div className="container mx-auto flex min-h-[calc(100vh-12rem)] items-center justify-center px-4 py-12">
      <Card className="w-full max-w-md border shadow-lg">
        <CardHeader className="text-center space-y-2 pb-6 border-b bg-slate-50/50 dark:bg-slate-900/50">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-blue-600 text-white shadow-md">
            <Shield className="h-6 w-6" />
          </div>
          <CardTitle className="text-2xl font-black tracking-tight text-slate-900 dark:text-white">
            Municipal Officer Portal
          </CardTitle>
          <CardDescription className="text-xs text-muted-foreground">
            Sign in to access grievance triage, risk-tiered approvals, and autonomous agent supervision.
          </CardDescription>
        </CardHeader>

        <CardContent className="pt-6 space-y-5">
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                Officer Access Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter officer password (e.g. officer123)"
                  className="pl-9 text-sm"
                  required
                />
              </div>
            </div>

            {error && (
              <div className="p-2.5 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 text-rose-700 dark:text-rose-300 text-xs">
                {error}
              </div>
            )}

            <Button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold h-10 shadow-xs"
            >
              {loading ? "Authenticating..." : "Sign In to Officer Console"}
            </Button>
          </form>

          <div className="pt-4 border-t text-center space-y-3">
            <div className="text-[11px] text-muted-foreground">
              Demo / Mock Mode Environment Active
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleDemoQuickLogin}
              disabled={loading}
              className="w-full text-xs font-mono border-dashed border-blue-300 text-blue-700 dark:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-950/30"
            >
              <KeyRound className="h-3.5 w-3.5 mr-1.5 text-blue-600" />
              <span>One-Click Demo Officer Login</span>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
