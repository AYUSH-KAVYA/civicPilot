"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { listApprovals, handleApproval, listCases, resolveCase } from "@/lib/api/endpoints";
import { getErrorMessage } from "@/lib/api/errorMessage";
import { Approval, CaseState, RiskTier, CaseStatus } from "@/lib/api/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  ShieldAlert,
  AlertCircle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ArrowRight,
  Brain,
  Sparkles,
  UserCheck,
  RotateCcw,
} from "lucide-react";

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [needsHumanCases, setNeedsHumanCases] = useState<CaseState[]>([]);
  const [loading, setLoading] = useState(true);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [resolveNotes, setResolveNotes] = useState<Record<string, string>>({});
  const [actionMsg, setActionMsg] = useState("");

  const loadData = useCallback(async () => {
    try {
      const [apprRes, casesRes] = await Promise.all([
        listApprovals("pending"),
        listCases({ status: "ALL" }),
      ]);
      if (apprRes.data) setApprovals(apprRes.data);
      if (casesRes.data?.cases) {
        const filtered = casesRes.data.cases.filter(
          (c) => c.flags.needs_human || c.status === CaseStatus.NEEDS_HUMAN
        );
        setNeedsHumanCases(filtered);
      }
    } catch (err) {
      console.error("Failed to load approvals:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Load external API state on mount, then refresh while the queue is open.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadData();
    const interval = setInterval(loadData, 3000);
    return () => clearInterval(interval);
  }, [loadData]);

  const onApprove = async (id: string) => {
    const note = notes[id] || "Officer authorization granted per protocol.";
    try {
      await handleApproval(id, { decision: "approve", note });
      setActionMsg(`Approval ${id} APPROVED. Authorized autonomous agent execution resumed!`);
      loadData();
      setTimeout(() => setActionMsg(""), 4000);
    } catch (err) {
      setActionMsg(getErrorMessage(err, "Failed to approve the request."));
    }
  };

  const onReject = async (id: string) => {
    const note = notes[id] || "Officer rejected authorization. Plan step flagged failed.";
    try {
      await handleApproval(id, { decision: "reject", note });
      setActionMsg(`Approval ${id} REJECTED.`);
      loadData();
      setTimeout(() => setActionMsg(""), 4000);
    } catch (err) {
      setActionMsg(getErrorMessage(err, "Failed to reject the request."));
    }
  };

  const onResolve = async (caseId: string) => {
    const note = resolveNotes[caseId] || "Officer clarified ambiguity and assigned appropriate routing.";
    try {
      await resolveCase(caseId, { note });
      setActionMsg(`Case #${caseId} resolved and unblocked!`);
      loadData();
      setTimeout(() => setActionMsg(""), 4000);
    } catch (err) {
      setActionMsg(getErrorMessage(err, "Failed to resolve the case."));
    }
  };

  return (
    <div className="container mx-auto max-w-6xl px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b pb-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
            <ShieldAlert className="h-7 w-7 text-red-600" />
            <span>Officer Authorization &amp; Review Queue</span>
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
            Human-in-the-loop governance: Risk-tiered authorization gates and low-confidence resolution.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Badge className="bg-red-600 text-white font-mono text-xs font-bold">
            {approvals.length} Pending Sign-Offs
          </Badge>
          <Badge className="bg-orange-500 text-white font-mono text-xs font-bold">
            {needsHumanCases.length} Needs Human
          </Badge>
        </div>
      </div>

      {actionMsg && (
        <div className="p-3 rounded-lg border border-emerald-300 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-200 text-xs flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-emerald-600 shrink-0" />
          <span>{actionMsg}</span>
        </div>
      )}

      {/* Tabs */}
      <Tabs defaultValue="approvals" className="w-full">
        <TabsList className="grid w-full grid-cols-2 max-w-md">
          <TabsTrigger value="approvals" className="text-xs font-bold gap-1.5">
            <ShieldAlert className="h-3.5 w-3.5 text-red-600" />
            <span>Risk-Tiered Approvals ({approvals.length})</span>
          </TabsTrigger>
          <TabsTrigger value="needs_human" className="text-xs font-bold gap-1.5">
            <AlertCircle className="h-3.5 w-3.5 text-orange-500" />
            <span>Needs Human Queue ({needsHumanCases.length})</span>
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Risk-Tiered Approvals */}
        <TabsContent value="approvals" className="pt-4 space-y-4">
          {approvals.length === 0 ? (
            <Card className="border shadow-xs">
              <CardContent className="p-12 text-center text-muted-foreground text-xs italic">
                No approvals currently pending. Autonomous agents are operating within routine risk boundaries.
              </CardContent>
            </Card>
          ) : (
            approvals.map((appr) => {
              const isCritical = appr.risk_tier === RiskTier.critical;
              return (
                <Card
                  key={appr.id}
                  className={`border-2 shadow-xs ${
                    isCritical
                      ? "border-red-400 bg-red-50/20 dark:bg-red-950/10"
                      : "border-amber-300 bg-amber-50/20 dark:bg-amber-950/10"
                  }`}
                >
                  <CardHeader className="pb-3 border-b bg-white dark:bg-slate-900">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-slate-500">
                          ID: {appr.id}
                        </span>
                        <Badge
                          className={
                            isCritical
                              ? "bg-red-700 text-white font-bold text-[10px]"
                              : "bg-amber-600 text-white font-semibold text-[10px]"
                          }
                        >
                          TIER: {appr.risk_tier?.toUpperCase()}
                        </Badge>
                        <Link href={`/officer/cases/${appr.case_id}`}>
                          <Badge variant="outline" className="text-[10px] font-mono hover:bg-slate-100">
                            Case #{appr.case_id} &rarr;
                          </Badge>
                        </Link>
                      </div>

                      <span className="text-[10px] font-mono text-muted-foreground">
                        Requested: {appr.requested_at || appr.created_at
                          ? new Date(appr.requested_at || appr.created_at || "").toLocaleTimeString()
                          : "Time unavailable"}
                      </span>
                    </div>

                    <CardTitle className="text-base font-bold text-slate-900 dark:text-slate-100 mt-2">
                      {appr.summary || appr.rationale || `Approval required for step ${appr.step_id || "not specified"}`}
                    </CardTitle>
                  </CardHeader>

                  <CardContent className="pt-4 space-y-4">
                    {/* Agent Reasoning Packet */}
                    <div className="p-3 rounded-lg border bg-slate-50 dark:bg-slate-950/60 space-y-2 text-xs">
                      <div className="flex items-center gap-2 font-bold text-slate-800 dark:text-slate-200">
                        <Brain className="h-4 w-4 text-blue-600" />
                        <span>Agent Reasoning Packet &bull; Contract Section 6</span>
                      </div>

                      {(appr.detail || appr.rationale || appr.step_id) && (
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] font-mono">
                          {Object.entries(appr.detail || { rationale: appr.rationale, step_id: appr.step_id }).map(([key, val]) => (
                            <div key={key} className="bg-white dark:bg-slate-900 p-2 rounded border">
                              <span className="text-muted-foreground block text-[10px] uppercase">
                                {key.replace(/_/g, " ")}:
                              </span>
                              <span className="font-semibold text-slate-800 dark:text-slate-200">
                                {typeof val === "object" ? JSON.stringify(val) : String(val)}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Officer Decision Controls */}
                    <div className="flex flex-col sm:flex-row items-center gap-3 pt-1">
                      <Input
                        value={notes[appr.id] || ""}
                        onChange={(e) => setNotes({ ...notes, [appr.id]: e.target.value })}
                        placeholder="Officer authorization note (optional)..."
                        className="text-xs"
                      />

                      <div className="flex items-center gap-2 shrink-0">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => onReject(appr.id)}
                          className="border-rose-300 text-rose-700 hover:bg-rose-50 text-xs font-semibold"
                        >
                          <XCircle className="h-3.5 w-3.5 mr-1 text-rose-600" />
                          <span>Reject</span>
                        </Button>

                        <Button
                          size="sm"
                          onClick={() => onApprove(appr.id)}
                          className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold gap-1 shadow-xs"
                        >
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          <span>Approve &amp; Dispatch</span>
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })
          )}
        </TabsContent>

        {/* Tab 2: Needs Human Queue */}
        <TabsContent value="needs_human" className="pt-4 space-y-4">
          {needsHumanCases.length === 0 ? (
            <Card className="border shadow-xs">
              <CardContent className="p-12 text-center text-muted-foreground text-xs italic">
                No cases currently waiting for human triage. All reports passed confidence guardrails (&ge;0.65).
              </CardContent>
            </Card>
          ) : (
            needsHumanCases.map((c) => (
              <Card key={c.id} className="border-2 border-orange-300 bg-orange-50/20 dark:bg-orange-950/10 shadow-xs">
                <CardHeader className="pb-3 border-b bg-white dark:bg-slate-900">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-bold">Case #{c.id}</span>
                      <Badge className="bg-orange-600 text-white text-[10px]">NEEDS HUMAN</Badge>
                      <Badge variant="outline" className="text-[10px]">
                        {c.intake?.category || "General"}
                      </Badge>
                      <Link href={`/officer/cases/${c.id}`}>
                        <Button variant="ghost" size="sm" className="h-6 text-xs text-blue-600">
                          Inspect Full Timeline &rarr;
                        </Button>
                      </Link>
                    </div>

                    <span className="text-xs font-mono text-muted-foreground">
                      Reported: {new Date(c.created_at).toLocaleTimeString()}
                    </span>
                  </div>

                  <CardTitle className="text-sm font-bold text-slate-800 dark:text-slate-200 mt-2">
                    {c.raw.text}
                  </CardTitle>
                </CardHeader>

                <CardContent className="pt-4 space-y-3">
                  <div className="p-2.5 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 text-xs text-rose-800 dark:text-rose-200 font-medium">
                    Reason: {c.flags.human_reason || "Low confidence score detected by Triage guardrail."}
                  </div>

                  <div className="flex flex-col sm:flex-row items-center gap-3 pt-1">
                    <Input
                      value={resolveNotes[c.id] || ""}
                      onChange={(e) => setResolveNotes({ ...resolveNotes, [c.id]: e.target.value })}
                      placeholder="Officer resolution notes (e.g. 'Classified as Water leak at 4th & Mission, urgency high')..."
                      className="text-xs"
                    />

                    <Button
                      size="sm"
                      onClick={() => onResolve(c.id)}
                      className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shrink-0 shadow-xs"
                    >
                      <UserCheck className="h-3.5 w-3.5 mr-1.5" />
                      <span>Resolve &amp; Re-enter Autonomous Loop</span>
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
