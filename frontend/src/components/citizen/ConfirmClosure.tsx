"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { CheckCircle2, XCircle, AlertTriangle, MessageSquare } from "lucide-react";
import { confirmCase } from "@/lib/api/endpoints";
import { CaseState, CaseStatus } from "@/lib/api/types";

interface ConfirmClosureProps {
  caseState: CaseState;
  onUpdated: (updatedCase: CaseState) => void;
}

export function ConfirmClosure({ caseState, onUpdated }: ConfirmClosureProps) {
  const [comment, setComment] = useState("");
  const [loading, setLoading] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState(false);

  const handleDecision = async (confirmed: boolean) => {
    setLoading(true);
    try {
      const res = await confirmCase(caseState.id, {
        confirmed,
        comment: comment.trim() || undefined,
      });
      if (res.data) {
        onUpdated(res.data);
      }
      setFeedbackGiven(true);
    } catch (err: any) {
      alert("Error submitting confirmation: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  if (caseState.status === CaseStatus.CLOSED) {
    return (
      <div className="p-4 rounded-xl border border-emerald-200 bg-emerald-50/60 dark:bg-emerald-950/20 text-emerald-900 dark:text-emerald-200 text-xs flex items-center gap-3">
        <CheckCircle2 className="h-5 w-5 text-emerald-600 shrink-0" />
        <div>
          <div className="font-bold">Case Officially Resolved &amp; Verified</div>
          <div className="text-emerald-700 dark:text-emerald-400 mt-0.5">
            Thank you for confirming resolution. Municipal audit record closed.
          </div>
        </div>
      </div>
    );
  }

  if (caseState.status === CaseStatus.REOPENED) {
    return (
      <div className="p-4 rounded-xl border border-rose-200 bg-rose-50/60 dark:bg-rose-950/20 text-rose-900 dark:text-rose-200 text-xs flex items-center gap-3">
        <AlertTriangle className="h-5 w-5 text-rose-600 shrink-0" />
        <div>
          <div className="font-bold">Grievance Reopened (Adaptation Rule e)</div>
          <div className="text-rose-700 dark:text-rose-400 mt-0.5">
            You flagged this issue as unresolved. It has been escalated to the officer queue for investigation.
          </div>
        </div>
      </div>
    );
  }

  return (
    <Card className="border-2 border-teal-200 bg-teal-50/30 dark:bg-teal-950/10 shadow-xs">
      <CardHeader className="pb-3 border-b border-teal-100 dark:border-teal-900">
        <CardTitle className="text-base font-bold text-teal-950 dark:text-teal-100 flex items-center gap-2">
          <CheckCircle2 className="h-5 w-5 text-teal-600" />
          <span>Resolution Verification &amp; Citizen Sign-Off</span>
        </CardTitle>
        <CardDescription className="text-xs text-teal-800 dark:text-teal-300">
          The field crew marked this work order complete. Please verify if the issue was satisfactorily resolved.
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-4 space-y-3">
        <Textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Optional feedback: e.g. 'Leak is completely fixed, thank you!' or 'Water is still leaking under the curb'..."
          rows={2}
          className="text-xs resize-none bg-white dark:bg-slate-900"
        />

        <div className="flex flex-wrap items-center justify-end gap-2 pt-1">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={loading}
            onClick={() => handleDecision(false)}
            className="border-rose-200 text-rose-700 hover:bg-rose-50 hover:text-rose-800 text-xs gap-1.5"
          >
            <XCircle className="h-3.5 w-3.5 text-rose-600" />
            <span>Dispute &amp; Reopen Case</span>
          </Button>

          <Button
            type="button"
            size="sm"
            disabled={loading}
            onClick={() => handleDecision(true)}
            className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs gap-1.5 font-semibold"
          >
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span>Confirm Resolution (Close)</span>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
