"use client";

import { CaseState, CaseStatus } from "@/lib/api/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  CheckCircle2,
  Clock,
  AlertCircle,
  Truck,
  Wrench,
  ShieldAlert,
  HelpCircle,
  RefreshCw,
  Eye,
  Brain,
  ListOrdered,
  Zap,
} from "lucide-react";
import { Progress } from "@/components/ui/progress";

interface StatusTrackerProps {
  caseState: CaseState;
}

export function StatusTracker({ caseState }: StatusTrackerProps) {
  const getStatusConfig = (status: CaseStatus) => {
    switch (status) {
      case CaseStatus.NEW:
      case CaseStatus.INTAKE:
        return { label: "Intake & Perception", color: "bg-purple-100 text-purple-800 border-purple-300", step: 1, pct: 15 };
      case CaseStatus.TRIAGED:
        return { label: "Triaged by Policy KB", color: "bg-blue-100 text-blue-800 border-blue-300", step: 2, pct: 35 };
      case CaseStatus.PLANNED:
        return { label: "Resolution Plan Generated", color: "bg-indigo-100 text-indigo-800 border-indigo-300", step: 3, pct: 50 };
      case CaseStatus.IN_PROGRESS:
        return { label: "Work Order Dispatched / In Progress", color: "bg-emerald-100 text-emerald-800 border-emerald-300", step: 4, pct: 75 };
      case CaseStatus.AT_RISK:
        return { label: "At Risk / Escalating", color: "bg-amber-100 text-amber-800 border-amber-300", step: 4, pct: 70 };
      case CaseStatus.NEEDS_HUMAN:
        return { label: "Officer Review Required", color: "bg-orange-100 text-orange-800 border-orange-300", step: 2, pct: 40 };
      case CaseStatus.AWAITING_CONFIRMATION:
        return { label: "Repair Done - Verification Pending", color: "bg-teal-100 text-teal-800 border-teal-300", step: 5, pct: 90 };
      case CaseStatus.CLOSED:
        return { label: "Verified & Closed", color: "bg-green-100 text-green-800 border-green-300", step: 6, pct: 100 };
      case CaseStatus.REOPENED:
        return { label: "Reopened by Citizen Dispute", color: "bg-rose-100 text-rose-800 border-rose-300", step: 6, pct: 85 };
      default:
        return { label: status, color: "bg-slate-100 text-slate-800 border-slate-300", step: 1, pct: 20 };
    }
  };

  const config = getStatusConfig(caseState.status);

  const steps = [
    { title: "Perceive", desc: "Report Ingested", icon: Eye, active: config.step >= 1 },
    { title: "Reason", desc: "Policy Triage", icon: Brain, active: config.step >= 2 },
    { title: "Plan", desc: "Plan Generated", icon: ListOrdered, active: config.step >= 3 },
    { title: "Act", desc: "Crew Dispatched", icon: Zap, active: config.step >= 4 },
    { title: "Evaluate", desc: "AI Photo Audit", icon: CheckCircle2, active: config.step >= 5 },
    { title: "Adapt / Close", desc: "Citizen Closure", icon: RefreshCw, active: config.step >= 6 },
  ];

  return (
    <Card className="border shadow-xs">
      <CardHeader className="pb-3 border-b bg-slate-50/50 dark:bg-slate-900/50">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono uppercase text-muted-foreground">Case #{caseState.id}</span>
              <Badge variant="outline" className={`font-semibold text-xs border ${config.color}`}>
                {config.label}
              </Badge>
              {caseState.flags.needs_human && (
                <Badge variant="destructive" className="text-xs gap-1">
                  <AlertCircle className="h-3 w-3" />
                  Needs Human Officer
                </Badge>
              )}
            </div>
            <CardTitle className="text-lg font-bold mt-1 text-slate-900 dark:text-slate-100">
              {caseState.intake?.category || "Municipal"} Grievance Resolution
            </CardTitle>
          </div>

          <div className="text-right">
            <div className="text-xs font-mono text-muted-foreground flex items-center gap-1 justify-end">
              <Clock className="h-3.5 w-3.5 text-blue-600" />
              <span>Target SLA: {caseState.triage?.deadline_hours || 4} hours</span>
            </div>
            <div className="text-xs font-medium text-slate-600 dark:text-slate-400 mt-0.5">
              Ward: {caseState.triage?.ward_id || "Unassigned"} &bull; Priority: {caseState.triage?.urgency || "Normal"}
            </div>
          </div>
        </div>

        <div className="mt-4 space-y-1.5">
          <div className="flex justify-between text-xs font-medium text-muted-foreground">
            <span>Resolution Loop Progress</span>
            <span>{config.pct}% Complete</span>
          </div>
          <Progress value={config.pct} className="h-2 bg-slate-200 dark:bg-slate-800" />
        </div>
      </CardHeader>

      <CardContent className="pt-4">
        {/* Horizontal Visual Step Indicator */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
          {steps.map((st, i) => {
            const Icon = st.icon;
            return (
              <div
                key={st.title}
                className={`p-2.5 rounded-lg border text-center transition-all ${
                  st.active
                    ? "bg-blue-50/70 border-blue-200 text-blue-900 dark:bg-blue-950/40 dark:border-blue-800 dark:text-blue-200"
                    : "bg-slate-50/30 border-slate-200/60 text-slate-400 dark:bg-slate-900/20 dark:border-slate-800"
                }`}
              >
                <div className="flex justify-center mb-1">
                  <Icon className={`h-4 w-4 ${st.active ? "text-blue-600 dark:text-blue-400" : "text-slate-300"}`} />
                </div>
                <div className="text-xs font-bold leading-tight">{st.title}</div>
                <div className="text-[10px] text-muted-foreground leading-tight mt-0.5">{st.desc}</div>
              </div>
            );
          })}
        </div>

        {/* Assigned tickets and crew */}
        {caseState.tickets && caseState.tickets.length > 0 && (
          <div className="mt-4 pt-4 border-t flex flex-wrap items-center justify-between text-xs gap-2">
            <div className="flex items-center gap-2">
              <Truck className="h-4 w-4 text-emerald-600" />
              <span className="font-semibold">Work Order:</span>
              <span className="font-mono bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">
                {caseState.tickets[0].id}
              </span>
              <span className="text-muted-foreground">&bull; Assigned Crew:</span>
              <span className="font-semibold text-emerald-700 dark:text-emerald-400">
                {caseState.tickets[0].crew_id || "Auto-dispatching nearest crew"}
              </span>
            </div>
            <div className="text-muted-foreground font-mono">
              Status: <span className="uppercase font-semibold">{caseState.tickets[0].status}</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
