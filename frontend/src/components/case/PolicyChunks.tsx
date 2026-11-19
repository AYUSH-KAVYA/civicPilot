"use client";

import { CaseEvent, CaseState, Phase } from "@/lib/api/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BookOpen } from "lucide-react";

interface PolicyChunksProps {
  caseState: CaseState;
  events?: CaseEvent[];
}

export function PolicyChunks({ caseState, events = [] }: PolicyChunksProps) {
  const policyRefs = caseState.triage?.policy_refs || [];
  const rationale = caseState.triage?.rationale;
  const policyEvents = events.filter((event) => event.tool_name === "policy_search" && event.phase === Phase.tool_result);

  return (
    <Card className="border shadow-xs">
      <CardHeader className="pb-3 border-b bg-slate-50/50 dark:bg-slate-900/50">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-bold flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-blue-600" />
            <span>Policy Knowledge Base Citations</span>
          </CardTitle>
          <Badge variant="outline" className="text-[10px] font-mono">
            Case policy references
          </Badge>
        </div>
        <CardDescription className="text-xs">
          Citations and search results returned for this case; unavailable text is not fabricated.
        </CardDescription>
      </CardHeader>

      <CardContent className="pt-4 space-y-3">
        {/* Triage Rationale */}
        {rationale && <div className="p-3 rounded-lg bg-blue-50/50 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-900 text-xs text-blue-950 dark:text-blue-200"><span className="font-bold">Agent rationale: </span>{rationale}</div>}

        {policyRefs.length ? (
          <div className="flex flex-wrap gap-2">{policyRefs.map((reference) => <Badge key={reference} variant="outline" className="font-mono">{reference}</Badge>)}</div>
        ) : (
          <p className="text-xs text-muted-foreground">No policy references are attached to this triage result.</p>
        )}

        {policyEvents.map((event) => (
          <details key={event.id} className="rounded-lg border bg-slate-50 p-3 text-xs dark:bg-slate-950/50">
            <summary className="cursor-pointer font-semibold">Policy search result · {new Date(event.ts).toLocaleString()}</summary>
            <pre className="mt-2 overflow-x-auto whitespace-pre-wrap font-mono text-[11px]">{JSON.stringify(event.detail, null, 2)}</pre>
          </details>
        ))}
      </CardContent>
    </Card>
  );
}
