"use client";

import { useEffect, useState, useCallback, Suspense } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  getCase,
  sandboxRejectTicket,
  sandboxCrewCheckin,
  sandboxCrewNoShow,
  sandboxRepairPhoto,
  resolveCase,
} from "@/lib/api/endpoints";
import { getErrorMessage } from "@/lib/api/errorMessage";
import { useSSE } from "@/lib/hooks/useSSE";
import { CaseState, CaseStatus, Urgency } from "@/lib/api/types";
import { EventTimeline } from "@/components/case/EventTimeline";
import { PlanView } from "@/components/case/PlanView";
import { ConfidenceMeters } from "@/components/case/ConfidenceMeters";
import { PolicyChunks } from "@/components/case/PolicyChunks";
import { CaseMapView } from "@/components/case/CaseMapView";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Activity,
  ArrowLeft,
  Clock,
  Radio,
  ShieldAlert,
  UserCheck,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Camera,
  Truck,
  FileText,
  AlertCircle,
  HelpCircle,
  Sparkles,
  Zap,
} from "lucide-react";

function CaseDetailContent() {
  const params = useParams();
  const caseId = params?.id as string;

  const [caseState, setCaseState] = useState<CaseState | null>(null);
  const [loading, setLoading] = useState(true);
  const [resolveNote, setResolveNote] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState("");

  const { events, status: sseStatus, refetch } = useSSE(caseId);

  const fetchCaseDetails = useCallback(async () => {
    if (!caseId) return;
    try {
      const res = await getCase(caseId);
      if (res.data) {
        setCaseState(res.data);
      }
    } catch (err) {
      console.error("Failed to load case detail:", err);
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    // Load external API state on mount and keep the detail view current.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchCaseDetails();
    const interval = setInterval(fetchCaseDetails, 3000);
    return () => clearInterval(interval);
  }, [fetchCaseDetails]);

  // Sandbox trigger handlers
  const handleRejectTicket = async () => {
    if (!caseState?.tickets?.[0]?.id) return;
    setActionLoading(true);
    try {
      await sandboxRejectTicket(
        caseState.tickets[0].id,
        "Jurisdiction dispute: Roadway belongs to State Highway Authority"
      );
      setActionMessage("Ticket rejected. Adaptation Rule (a) triggered!");
      refetch();
      fetchCaseDetails();
      setTimeout(() => setActionMessage(""), 4000);
    } catch (err) {
      setActionMessage(getErrorMessage(err, "Ticket rejection failed."));
    } finally {
      setActionLoading(false);
    }
  };

  const handleCrewNoShow = async () => {
    if (!caseState?.tickets?.[0]?.id) return;
    setActionLoading(true);
    try {
      await sandboxCrewNoShow(caseState.tickets[0].id);
      setActionMessage("Crew no-show signaled. Adaptation Rule (b) triggered (Urgency escalated)!");
      refetch();
      fetchCaseDetails();
      setTimeout(() => setActionMessage(""), 4000);
    } catch (err) {
      setActionMessage(getErrorMessage(err, "Crew no-show signal failed."));
    } finally {
      setActionLoading(false);
    }
  };

  const handleCrewCheckin = async () => {
    if (!caseState?.tickets?.[0]?.id) return;
    setActionLoading(true);
    try {
      await sandboxCrewCheckin(caseState.tickets[0].id);
      setActionMessage("Crew checked in on-site!");
      refetch();
      fetchCaseDetails();
      setTimeout(() => setActionMessage(""), 4000);
    } catch (err) {
      setActionMessage(getErrorMessage(err, "Crew check-in signal failed."));
    } finally {
      setActionLoading(false);
    }
  };

  const handleRepairPhoto = async () => {
    if (!caseState?.tickets?.[0]?.id) return;
    setActionLoading(true);
    try {
      await sandboxRepairPhoto(caseState.tickets[0].id);
      setActionMessage("Repair photo uploaded! Evaluator Agent running vision audit.");
      refetch();
      fetchCaseDetails();
      setTimeout(() => setActionMessage(""), 4000);
    } catch (err) {
      setActionMessage(getErrorMessage(err, "Repair evidence upload failed."));
    } finally {
      setActionLoading(false);
    }
  };

  const handleResolveNeedsHuman = async () => {
    if (!caseState || !resolveNote.trim()) return;
    setActionLoading(true);
    try {
      const res = await resolveCase(caseState.id, { note: resolveNote.trim() });
      if (res.data) setCaseState(res.data);
      setResolveNote("");
      setActionMessage("Grievance unblocked and returned to autonomous execution!");
      refetch();
      setTimeout(() => setActionMessage(""), 4000);
    } catch (err) {
      setActionMessage(getErrorMessage(err, "Could not resolve the case."));
    } finally {
      setActionLoading(false);
    }
  };

  if (loading && !caseState) {
    return (
      <div className="container mx-auto max-w-7xl px-4 py-24 text-center">
        <Activity className="h-8 w-8 animate-spin text-blue-600 mx-auto mb-2" />
        <div className="text-sm text-muted-foreground font-mono">Loading case #{caseId} telemetry...</div>
      </div>
    );
  }

  if (!caseState) {
    return (
      <div className="container mx-auto max-w-lg px-4 py-16 text-center space-y-4">
        <h2 className="text-xl font-bold text-rose-600">Case #{caseId} Not Found</h2>
        <Link href="/officer/cases">
          <Button variant="outline" size="sm">Return to Case Queue</Button>
        </Link>
      </div>
    );
  }

  const isCase1042 = caseState.id === "1042";
  const hasTicket = caseState.tickets.length > 0;

  return (
    <div className="container mx-auto max-w-7xl px-4 py-6 space-y-6">
      {/* Top Breadcrumb & Status Header */}
      <div className="p-4 sm:p-6 rounded-2xl border bg-white dark:bg-slate-900 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link href="/officer/cases" className="text-muted-foreground hover:text-foreground">
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <ArrowLeft className="h-4 w-4" />
              </Button>
            </Link>

            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-xl font-black text-slate-900 dark:text-white">
                  Case #{caseState.id}
                </span>
                <Badge className="bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs uppercase">
                  {caseState.status}
                </Badge>
                {caseState.triage?.urgency === Urgency.critical ? (
                  <Badge className="bg-red-600 text-white font-black text-xs animate-pulse">
                    CRITICAL URGENCY
                  </Badge>
                ) : (
                  <Badge variant="outline" className="font-semibold text-xs border-amber-300 text-amber-700 bg-amber-50">
                    {caseState.triage?.urgency?.toUpperCase() || "HIGH"} URGENCY
                  </Badge>
                )}
                {isCase1042 && (
                  <Badge variant="destructive" className="font-mono text-xs gap-1">
                    <ShieldAlert className="h-3 w-3" />
                    CASE 1042 (BENCHMARK)
                  </Badge>
                )}
              </div>
              <h1 className="text-lg font-bold text-slate-800 dark:text-slate-200 mt-1">
                {caseState.intake?.summary || caseState.raw.text}
              </h1>
            </div>
          </div>

          <div className="flex flex-col sm:items-end gap-1.5 font-mono text-xs">
            <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-bold">
              <Radio className="h-3.5 w-3.5 animate-pulse" />
              <span>SSE STREAM: {sseStatus.toUpperCase()}</span>
            </div>
            <div className="text-muted-foreground">
              SLA Deadline: {caseState.triage?.deadline_hours || 4}h target
            </div>
          </div>
        </div>

        {/* Metadata Strip: PII-Masked citizen info, Ward, Office */}
        <div className="pt-3 border-t grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
          <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-950/50 border">
            <span className="text-muted-foreground block text-[10px]">PII-Masked Citizen</span>
            <span className="font-bold text-slate-900 dark:text-slate-100">
              {caseState.citizen.contact_masked}
            </span>
            <span className="text-[10px] text-muted-foreground block">
              Lang: {caseState.citizen.language.toUpperCase()} &bull; Channel: {caseState.raw.channel.toUpperCase()}
            </span>
          </div>

          <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-950/50 border">
            <span className="text-muted-foreground block text-[10px]">Department &amp; Office</span>
            <span className="font-bold text-blue-600 dark:text-blue-400">
              {caseState.intake?.category || "Municipal"}
            </span>
            <span className="text-[10px] text-muted-foreground block">
              Office: {caseState.triage?.office_id || "central"}
            </span>
          </div>

          <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-950/50 border">
            <span className="text-muted-foreground block text-[10px]">Ward Assignment</span>
            <span className="font-bold text-slate-900 dark:text-slate-100">
              {caseState.triage?.ward_id || "ward-5"}
            </span>
            <span className="text-[10px] text-muted-foreground block">
              Point-in-polygon geocoded
            </span>
          </div>

          <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-950/50 border">
            <span className="text-muted-foreground block text-[10px]">Work Ticket &amp; Crew</span>
            <span className="font-bold text-emerald-600 dark:text-emerald-400">
              {caseState.tickets?.[0]?.crew_id || "Unassigned"}
            </span>
            <span className="text-[10px] text-muted-foreground block font-semibold">
              Ticket: {caseState.tickets?.[0]?.id || "TKT-PENDING"}
            </span>
          </div>
        </div>
      </div>

      {/* Human Intervention / Approval Alert Bar if needed */}
      {caseState.flags.needs_human && (
        <div className="p-4 rounded-xl border-2 border-rose-300 bg-rose-50/80 dark:bg-rose-950/30 text-rose-950 dark:text-rose-100 space-y-3 shadow-xs">
          <div className="flex items-center gap-2 font-bold text-sm text-rose-800 dark:text-rose-200">
            <AlertCircle className="h-5 w-5 text-rose-600 shrink-0" />
            <span>NEEDS HUMAN OFFICER ATTENTION (Ambiguity / Low Confidence / Dispute)</span>
          </div>
          <p className="text-xs text-rose-800 dark:text-rose-300">
            {caseState.flags.human_reason || "Autonomous confidence threshold breach or citizen dispute requires officer intervention."}
          </p>
          <div className="flex flex-col sm:flex-row gap-2 pt-1">
            <Input
              value={resolveNote}
              onChange={(e) => setResolveNote(e.target.value)}
              placeholder="Enter officer resolution notes (e.g. 'Confirmed hazardous road sinkhole on Mission St, verified location')..."
              className="text-xs bg-white dark:bg-slate-900"
            />
            <Button
              size="sm"
              onClick={handleResolveNeedsHuman}
              disabled={actionLoading || !resolveNote.trim()}
              className="bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold shrink-0"
            >
              Resolve &amp; Unblock Agent Loop
            </Button>
          </div>
        </div>
      )}

      {/* Action Notification Message */}
      {actionMessage && (
        <div className="p-3 rounded-lg border border-emerald-300 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-200 text-xs flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-emerald-600" />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* Main Grid: 2 Columns */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (7 cols): The Live Event Timeline */}
        <div className="lg:col-span-7 space-y-6">
          <Card className="border shadow-xs">
            <CardHeader className="pb-3 border-b bg-slate-50/50 dark:bg-slate-900/50">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-base font-black flex items-center gap-2">
                    <Activity className="h-4 w-4 text-blue-600" />
                    <span>Live Autonomous Audit Trail</span>
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Colour-coded by the 6 loop phases (Perceive, Reason, Plan, Act, Evaluate, Adapt).
                  </CardDescription>
                </div>
                <Badge variant="outline" className="font-mono text-xs">
                  {events.length} Events
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-4">
              <EventTimeline events={events} />
            </CardContent>
          </Card>
        </div>

        {/* Right Column (5 cols): Plan DAG, Confidence Meters, Map, Policy Chunks, Sandbox Controls */}
        <div className="lg:col-span-5 space-y-6">
          {/* Interactive Officer Sandbox Controls */}
          <Card className="border shadow-xs border-blue-200 bg-blue-50/20 dark:bg-blue-950/10">
            <CardHeader className="pb-3 border-b border-blue-100 dark:border-blue-900">
              <CardTitle className="text-sm font-bold flex items-center gap-2">
                <Zap className="h-4 w-4 text-blue-600" />
                <span>Sandbox In-Flight Disruptions (Live Demo)</span>
              </CardTitle>
              <CardDescription className="text-xs">
                Inject field signals to watch the agent adapt in real time.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-3 space-y-2">
              <div className="grid grid-cols-2 gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRejectTicket}
                  disabled={actionLoading || !hasTicket}
                  className="text-xs border-rose-200 hover:bg-rose-50 text-rose-700 dark:hover:bg-rose-950/30"
                >
                  <RotateCcw className="h-3 w-3 mr-1" />
                  <span>Reject Ticket</span>
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCrewNoShow}
                  disabled={actionLoading || !hasTicket}
                  className="text-xs border-amber-200 hover:bg-amber-50 text-amber-700 dark:hover:bg-amber-950/30"
                >
                  <Clock className="h-3 w-3 mr-1" />
                  <span>Crew No-Show</span>
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCrewCheckin}
                  disabled={actionLoading || !hasTicket}
                  className="text-xs border-emerald-200 hover:bg-emerald-50 text-emerald-700 dark:hover:bg-emerald-950/30"
                >
                  <Truck className="h-3 w-3 mr-1" />
                  <span>Crew Check-in</span>
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRepairPhoto}
                  disabled={actionLoading || !hasTicket}
                  className="text-xs border-teal-200 hover:bg-teal-50 text-teal-700 dark:hover:bg-teal-950/30"
                >
                  <Camera className="h-3 w-3 mr-1" />
                  <span>Upload Repair Photo</span>
                </Button>
              </div>

              {isCase1042 && (
                <div className="pt-2">
                  <Link href="/officer/approvals">
                    <Button size="sm" className="w-full bg-red-600 hover:bg-red-700 text-white text-xs font-bold gap-1.5 shadow-sm">
                      <ShieldAlert className="h-3.5 w-3.5" />
                      <span>Review Pending Critical Sign-Off (Case 1042) &rarr;</span>
                    </Button>
                  </Link>
                </div>
              )}
            </CardContent>
          </Card>

          {/* AI Confidence & Guardrails */}
          <ConfidenceMeters caseState={caseState} />

          {/* Plan DAG */}
          <Card className="border shadow-xs">
            <CardHeader className="pb-3 border-b bg-slate-50/50 dark:bg-slate-900/50">
              <CardTitle className="text-sm font-bold">
                Executable Resolution Plan (DAG)
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4">
              <PlanView plan={caseState.plan} />
            </CardContent>
          </Card>

          {/* Map View */}
          <CaseMapView caseState={caseState} />

          {/* Policy Chunks Cited */}
          <PolicyChunks caseState={caseState} events={events} />
        </div>
      </div>
    </div>
  );
}

export default function CaseDetailPage() {
  return (
    <Suspense fallback={<div className="container mx-auto p-12 text-center text-xs">Loading case details...</div>}>
      <CaseDetailContent />
    </Suspense>
  );
}
