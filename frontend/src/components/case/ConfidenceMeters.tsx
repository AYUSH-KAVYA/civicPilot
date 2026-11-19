"use client";

import { CaseState } from "@/lib/api/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { ShieldCheck, AlertTriangle, Gauge, Sparkles } from "lucide-react";

interface ConfidenceMetersProps {
  caseState: CaseState;
}

export function ConfidenceMeters({ caseState }: ConfidenceMetersProps) {
  const intakeConf = caseState.intake?.confidence || 0.85;
  const triageConf = caseState.triage?.confidence || 0.88;
  const overallConf = Math.min(intakeConf, triageConf);
  const threshold = 0.65; // Contract Section 8 CONFIDENCE_THRESHOLD

  const isBelowThreshold = overallConf < threshold;

  const getConfidenceColor = (conf: number) => {
    if (conf >= 0.85) return "text-emerald-600 dark:text-emerald-400";
    if (conf >= 0.65) return "text-blue-600 dark:text-blue-400";
    return "text-rose-600 dark:text-rose-400";
  };

  return (
    <Card className="border shadow-xs">
      <CardHeader className="pb-3 border-b bg-slate-50/50 dark:bg-slate-900/50">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-bold flex items-center gap-2">
            <Gauge className="h-4 w-4 text-blue-600" />
            <span>AI Confidence &amp; Guardrails</span>
          </CardTitle>
          <Badge
            variant="outline"
            className={`font-mono text-[10px] ${
              isBelowThreshold
                ? "bg-rose-50 text-rose-700 border-rose-300"
                : "bg-emerald-50 text-emerald-700 border-emerald-300"
            }`}
          >
            Threshold: &ge; 0.65
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="pt-4 space-y-4">
        {/* Intake Confidence */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs font-semibold">
            <span>Intake Perception Confidence</span>
            <span className={getConfidenceColor(intakeConf)}>
              {(intakeConf * 100).toFixed(0)}%
            </span>
          </div>
          <Progress value={intakeConf * 100} className="h-2 bg-slate-100 dark:bg-slate-800" />
          <div className="text-[10px] text-muted-foreground flex justify-between">
            <span>parse_media context accuracy</span>
            <span>{intakeConf >= 0.65 ? "PASS" : "FAIL"}</span>
          </div>
        </div>

        {/* Triage Confidence */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs font-semibold">
            <span>Triage Policy Fit Confidence</span>
            <span className={getConfidenceColor(triageConf)}>
              {(triageConf * 100).toFixed(0)}%
            </span>
          </div>
          <Progress value={triageConf * 100} className="h-2 bg-slate-100 dark:bg-slate-800" />
          <div className="text-[10px] text-muted-foreground flex justify-between">
            <span>policy_search semantic alignment</span>
            <span>{triageConf >= 0.65 ? "PASS" : "FAIL"}</span>
          </div>
        </div>

        {/* Guardrail Status Banner */}
        <div
          className={`p-2.5 rounded-lg border text-xs flex items-center gap-2 ${
            isBelowThreshold
              ? "bg-rose-50 dark:bg-rose-950/30 border-rose-200 text-rose-800 dark:text-rose-200"
              : "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 text-emerald-800 dark:text-emerald-200"
          }`}
        >
          {isBelowThreshold ? (
            <>
              <AlertTriangle className="h-4 w-4 text-rose-600 shrink-0" />
              <span>
                <strong>Guardrail Triggered:</strong> Confidence &lt; 0.65 halted execution to{" "}
                <code className="font-bold">NEEDS_HUMAN</code> queue.
              </span>
            </>
          ) : (
            <>
              <ShieldCheck className="h-4 w-4 text-emerald-600 shrink-0" />
              <span>
                <strong>Guardrail Verified:</strong> Confidence &ge; 0.65 allows safe autonomous tool dispatch.
              </span>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
