"use client";

import { useEffect, useState, Suspense } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { getCase } from "@/lib/api/endpoints";
import { useSSE } from "@/lib/hooks/useSSE";
import { CaseState } from "@/lib/api/types";
import { StatusTracker } from "@/components/citizen/StatusTracker";
import { NotificationInbox } from "@/components/citizen/NotificationInbox";
import { EvidenceUpload } from "@/components/citizen/EvidenceUpload";
import { ConfirmClosure } from "@/components/citizen/ConfirmClosure";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FileText, Radio, ArrowLeft, Loader2, ShieldCheck } from "lucide-react";
import Link from "next/link";

function TrackCaseContent() {
  const params = useParams();
  const searchParams = useSearchParams();
  const caseId = params?.id as string;
  const token = searchParams.get("token");

  const [caseState, setCaseState] = useState<CaseState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { events, status: sseStatus, refetch } = useSSE(caseId);

  useEffect(() => {
    async function loadCase() {
      if (!caseId) return;
      try {
        setLoading(true);
        const res = await getCase(caseId);
        if (res.data) {
          setCaseState(res.data);
        } else {
          setError("Case not found");
        }
      } catch (err: any) {
        setError(err.message || "Failed to load case");
      } finally {
        setLoading(false);
      }
    }
    loadCase();
  }, [caseId]);

  if (loading) {
    return (
      <div className="container mx-auto max-w-4xl px-4 py-20 flex flex-col items-center justify-center gap-3">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <p className="text-sm text-muted-foreground">Loading grievance audit trail...</p>
      </div>
    );
  }

  if (error || !caseState) {
    return (
      <div className="container mx-auto max-w-xl px-4 py-16 text-center space-y-4">
        <h2 className="text-xl font-bold text-rose-600">Grievance Not Found</h2>
        <p className="text-sm text-muted-foreground">
          Could not find a grievance with ID #{caseId}. Please verify your tracking URL.
        </p>
        <Link href="/report">
          <Button variant="outline" size="sm">File a New Report</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="container mx-auto max-w-5xl px-4 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Link href="/" className="text-muted-foreground hover:text-foreground">
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
              <FileText className="h-6 w-6 text-blue-600" />
              <span>Tracking Grievance #{caseState.id}</span>
            </h1>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Authenticated via citizen access token. Updates reflect real-time agent execution.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono">
          <ShieldCheck className="h-4 w-4 text-emerald-600" />
          <span>Access Token Verified</span>
        </div>
      </div>

      {/* Status Tracker */}
      <StatusTracker caseState={caseState} />

      {/* Live Agent Activity Feed */}
      <Card className="border shadow-xs">
        <CardHeader className="pb-3 border-b bg-slate-50/50 dark:bg-slate-900/50">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <Radio className="h-4 w-4 text-emerald-600 animate-pulse" />
              <span>Autonomous Agent Loop Events</span>
            </CardTitle>
            <Badge variant="outline" className="text-[10px] font-mono">
              SSE Stream: {sseStatus.toUpperCase()}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="pt-4 space-y-2.5 max-h-96 overflow-y-auto">
          {events.length === 0 ? (
            <div className="text-xs text-muted-foreground text-center py-6">
              No audit events found.
            </div>
          ) : (
            events.map((evt) => (
              <div
                key={evt.id}
                className="p-2.5 rounded-lg border bg-slate-50/60 dark:bg-slate-950/30 text-xs flex items-start justify-between gap-3"
              >
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="font-bold uppercase text-[10px] font-mono text-blue-600 dark:text-blue-400">
                      [{evt.agent}]
                    </span>
                    <span className="font-semibold text-slate-800 dark:text-slate-200">
                      {evt.summary}
                    </span>
                  </div>
                  {evt.tool_name && (
                    <div className="text-[10px] font-mono text-muted-foreground">
                      Tool executed: <code className="text-blue-600">{evt.tool_name}</code>
                    </div>
                  )}
                </div>
                <span className="text-[10px] font-mono text-muted-foreground shrink-0">
                  {new Date(evt.ts).toLocaleTimeString()}
                </span>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      {/* Notifications & Evidence */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <NotificationInbox events={events} />
        <EvidenceUpload caseId={caseState.id} onSubmitted={refetch} />
      </div>

      {/* Confirm / Dispute closure */}
      <ConfirmClosure
        caseState={caseState}
        onUpdated={(updated) => setCaseState(updated)}
      />
    </div>
  );
}

export default function TrackCasePage() {
  return (
    <Suspense fallback={<div className="container mx-auto p-12 text-center text-xs">Loading grievance tracker...</div>}>
      <TrackCaseContent />
    </Suspense>
  );
}
