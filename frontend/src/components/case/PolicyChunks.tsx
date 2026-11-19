"use client";

import { CaseState } from "@/lib/api/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BookOpen, FileCheck, ExternalLink, ShieldCheck } from "lucide-react";

interface PolicyChunksProps {
  caseState: CaseState;
}

export function PolicyChunks({ caseState }: PolicyChunksProps) {
  const policyRefs = caseState.triage?.policy_refs || [];
  const rationale = caseState.triage?.rationale || "Automated triage based on standard municipal charter.";

  // Mock policy chunks associated with the department / case
  const defaultChunks = [
    {
      chunk_id: policyRefs[0] || "POL-CITY-GEN-001",
      doc_title: `${caseState.intake?.category || "Municipal"} Response Standards & Safety Charter`,
      department: caseState.triage?.department_id || "dept-general",
      sla_hours: caseState.triage?.deadline_hours || 4,
      escalation_rule: "Immediate supervisor dispatch if unresolved within 50% SLA window",
      score: 0.96,
      text: "Any active infrastructure failure posing property flooding, road obstruction, or pedestrian hazards shall be triaged at HIGH or CRITICAL priority with emergency work order dispatch.",
    },
    {
      chunk_id: policyRefs[1] || "POL-ESCALATION-002",
      doc_title: "Hazard Classification & Inter-Agency Coordination Guide",
      department: "Cross-Departmental Oversight",
      sla_hours: 2,
      escalation_rule: "Officer sign-off required for structural lane closures or utility shutoffs",
      score: 0.91,
      text: "If public utility failure intersects transit arteries or sensitive locations (schools, healthcare facilities), response teams must notify municipal dispatch within 30 minutes.",
    },
  ];

  return (
    <Card className="border shadow-xs">
      <CardHeader className="pb-3 border-b bg-slate-50/50 dark:bg-slate-900/50">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-bold flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-blue-600" />
            <span>Policy Knowledge Base Citations</span>
          </CardTitle>
          <Badge variant="outline" className="text-[10px] font-mono">
            pgvector Semantic Search
          </Badge>
        </div>
        <CardDescription className="text-xs">
          Legal municipal charters and SLA requirements matched by the Triage Agent.
        </CardDescription>
      </CardHeader>

      <CardContent className="pt-4 space-y-3">
        {/* Triage Rationale */}
        <div className="p-3 rounded-lg bg-blue-50/50 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-900 text-xs text-blue-950 dark:text-blue-200">
          <span className="font-bold">Agent Rationale: </span>
          <span>{rationale}</span>
        </div>

        {/* Chunks */}
        <div className="space-y-2.5">
          {defaultChunks.map((chunk) => (
            <div
              key={chunk.chunk_id}
              className="p-3 rounded-lg border bg-white dark:bg-slate-900/70 space-y-1.5"
            >
              <div className="flex flex-wrap items-center justify-between gap-1">
                <span className="font-bold text-xs text-slate-900 dark:text-slate-100">
                  {chunk.doc_title}
                </span>
                <div className="flex items-center gap-1.5">
                  <Badge variant="secondary" className="text-[10px] font-mono">
                    Score: {(chunk.score * 100).toFixed(0)}%
                  </Badge>
                  <Badge variant="outline" className="text-[10px] font-mono text-blue-600">
                    SLA: {chunk.sla_hours}h
                  </Badge>
                </div>
              </div>

              <p className="text-xs text-muted-foreground leading-relaxed italic">
                &ldquo;{chunk.text}&rdquo;
              </p>

              <div className="pt-1 flex items-center justify-between text-[10px] text-muted-foreground font-mono">
                <span>Ref: {chunk.chunk_id}</span>
                <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
                  Rule: {chunk.escalation_rule}
                </span>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
