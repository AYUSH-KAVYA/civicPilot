"use client";

import { Plan, StepStatus, RiskTier } from "@/lib/api/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  CheckCircle2,
  Clock,
  AlertCircle,
  HelpCircle,
  ShieldAlert,
  ArrowRight,
  GitBranch,
  Terminal,
  Play,
  RotateCcw,
} from "lucide-react";

interface PlanViewProps {
  plan: Plan | null;
}

export function PlanView({ plan }: PlanViewProps) {
  if (!plan || !plan.steps || plan.steps.length === 0) {
    return (
      <div className="p-6 text-center text-xs text-muted-foreground italic">
        No execution plan generated yet. The Planner Agent will construct the DAG upon triage completion.
      </div>
    );
  }

  const getStatusBadge = (status: StepStatus) => {
    switch (status) {
      case StepStatus.done:
        return (
          <Badge className="bg-emerald-600 hover:bg-emerald-700 text-white text-[10px] gap-1 font-mono">
            <CheckCircle2 className="h-3 w-3" />
            DONE
          </Badge>
        );
      case StepStatus.running:
        return (
          <Badge className="bg-blue-600 hover:bg-blue-700 text-white text-[10px] gap-1 font-mono animate-pulse">
            <Play className="h-3 w-3" />
            RUNNING
          </Badge>
        );
      case StepStatus.awaiting_approval:
        return (
          <Badge className="bg-amber-600 hover:bg-amber-700 text-white text-[10px] gap-1 font-mono">
            <ShieldAlert className="h-3 w-3" />
            AWAITING APPROVAL
          </Badge>
        );
      case StepStatus.failed:
        return (
          <Badge className="bg-rose-600 hover:bg-rose-700 text-white text-[10px] gap-1 font-mono">
            <AlertCircle className="h-3 w-3" />
            FAILED
          </Badge>
        );
      case StepStatus.skipped:
        return (
          <Badge variant="outline" className="text-slate-500 text-[10px] font-mono">
            SKIPPED
          </Badge>
        );
      case StepStatus.pending:
      default:
        return (
          <Badge variant="outline" className="text-[10px] font-mono text-muted-foreground">
            PENDING
          </Badge>
        );
    }
  };

  const getRiskBadge = (risk: RiskTier) => {
    switch (risk) {
      case RiskTier.critical:
        return (
          <Badge className="bg-red-700 text-white text-[10px] font-mono font-bold">
            TIER: CRITICAL (OFFICER SIGN-OFF)
          </Badge>
        );
      case RiskTier.sensitive:
        return (
          <Badge className="bg-amber-600 text-white text-[10px] font-mono font-medium">
            TIER: SENSITIVE
          </Badge>
        );
      case RiskTier.routine:
      default:
        return (
          <Badge variant="outline" className="text-[10px] font-mono text-slate-600 dark:text-slate-400">
            TIER: ROUTINE
          </Badge>
        );
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-xs font-mono text-muted-foreground px-1 pb-1">
        <span>Plan Version: {plan.version}</span>
        <span>Total Steps: {plan.steps.length}</span>
      </div>

      <div className="space-y-3">
        {plan.steps.map((step, idx) => (
          <div
            key={step.id}
            className={`p-3.5 rounded-xl border bg-white dark:bg-slate-900 shadow-xs transition-all ${
              step.status === StepStatus.running
                ? "border-blue-400 ring-1 ring-blue-400/30"
                : step.status === StepStatus.awaiting_approval
                ? "border-amber-400 bg-amber-50/20 dark:bg-amber-950/10"
                : ""
            }`}
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold text-slate-500">
                  #{step.id}
                </span>
                <span className="font-bold text-sm text-slate-900 dark:text-slate-100">
                  {step.title}
                </span>
              </div>

              <div className="flex items-center gap-2">
                {getRiskBadge(step.risk_tier)}
                {getStatusBadge(step.status)}
              </div>
            </div>

            <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-muted-foreground font-mono">
              <div>
                Tool: <code className="text-blue-600 font-semibold">{step.tool}</code>
              </div>

              {step.depends_on && step.depends_on.length > 0 && (
                <div className="flex items-center gap-1 text-[11px] text-slate-500">
                  <GitBranch className="h-3 w-3" />
                  <span>Depends on: [{step.depends_on.join(", ")}]</span>
                </div>
              )}

              {step.fallback && (
                <div className="flex items-center gap-1 text-[11px] text-amber-600 dark:text-amber-400">
                  <RotateCcw className="h-3 w-3" />
                  <span>Fallback: {step.fallback.tool}</span>
                </div>
              )}
            </div>

            {/* Step args & result */}
            {step.result && (
              <div className="mt-2 p-2 rounded bg-slate-50 dark:bg-slate-950 text-[11px] font-mono text-muted-foreground border">
                Result: {JSON.stringify(step.result)}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
