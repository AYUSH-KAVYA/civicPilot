"use client";

import { useState } from "react";
import { CaseEvent, Phase } from "@/lib/api/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  ChevronDown,
  ChevronRight,
  Eye,
  Brain,
  ListOrdered,
  Zap,
  CheckCircle2,
  RefreshCw,
  ShieldAlert,
  Wrench,
  MessageSquare,
  Sparkles,
  Clock,
  Terminal,
} from "lucide-react";

interface EventTimelineProps {
  events: CaseEvent[];
}

export function EventTimeline({ events }: EventTimelineProps) {
  const [expandedEvents, setExpandedEvents] = useState<Record<string, boolean>>({});

  const toggleExpand = (id: string) => {
    setExpandedEvents((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const getPhaseConfig = (phase: Phase) => {
    switch (phase) {
      case Phase.perceive:
        return {
          label: "Perceive",
          color: "bg-purple-100 text-purple-800 border-purple-300 dark:bg-purple-950/40 dark:text-purple-300",
          icon: Eye,
          bar: "bg-purple-500",
        };
      case Phase.reason:
        return {
          label: "Reason",
          color: "bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-950/40 dark:text-blue-300",
          icon: Brain,
          bar: "bg-blue-500",
        };
      case Phase.plan:
        return {
          label: "Plan",
          color: "bg-indigo-100 text-indigo-800 border-indigo-300 dark:bg-indigo-950/40 dark:text-indigo-300",
          icon: ListOrdered,
          bar: "bg-indigo-500",
        };
      case Phase.act:
        return {
          label: "Act",
          color: "bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-300",
          icon: Zap,
          bar: "bg-emerald-500",
        };
      case Phase.evaluate:
        return {
          label: "Evaluate",
          color: "bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-950/40 dark:text-amber-300",
          icon: CheckCircle2,
          bar: "bg-amber-500",
        };
      case Phase.adapt:
        return {
          label: "Adapt",
          color: "bg-rose-100 text-rose-800 border-rose-300 dark:bg-rose-950/40 dark:text-rose-300 animate-pulse",
          icon: RefreshCw,
          bar: "bg-rose-500",
        };
      case Phase.guardrail:
        return {
          label: "Guardrail",
          color: "bg-red-100 text-red-800 border-red-300 dark:bg-red-950/40 dark:text-red-300",
          icon: ShieldAlert,
          bar: "bg-red-600",
        };
      case Phase.tool_call:
      case Phase.tool_result:
        return {
          label: phase === Phase.tool_call ? "Tool Call" : "Tool Result",
          color: "bg-cyan-100 text-cyan-800 border-cyan-300 dark:bg-cyan-950/40 dark:text-cyan-300",
          icon: Wrench,
          bar: "bg-cyan-500",
        };
      case Phase.message:
      default:
        return {
          label: "Message",
          color: "bg-slate-100 text-slate-800 border-slate-300 dark:bg-slate-900 dark:text-slate-300",
          icon: MessageSquare,
          bar: "bg-slate-400",
        };
    }
  };

  return (
    <div className="space-y-3">
      {events.map((evt, idx) => {
        const config = getPhaseConfig(evt.phase);
        const Icon = config.icon;
        const isExpanded = !!expandedEvents[evt.id];
        const isAdaptation = evt.phase === Phase.adapt;
        const isGuardrail = evt.phase === Phase.guardrail;
        const hasDetail = evt.detail && Object.keys(evt.detail).length > 0;

        return (
          <div
            key={evt.id || idx}
            className={`relative pl-4 border-l-2 transition-all rounded-r-lg ${config.bar} ${
              isAdaptation
                ? "bg-rose-50/60 dark:bg-rose-950/20 border-l-4 border-rose-500 shadow-xs"
                : isGuardrail
                ? "bg-red-50/60 dark:bg-red-950/20 border-l-4 border-red-600"
                : "bg-white dark:bg-slate-900/60 hover:bg-slate-50 dark:hover:bg-slate-900"
            }`}
          >
            <div className="p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className={`text-[10px] font-bold border uppercase font-mono ${config.color}`}>
                    <Icon className="h-3 w-3 mr-1" />
                    {config.label}
                  </Badge>

                  <span className="font-mono text-[11px] font-bold text-slate-700 dark:text-slate-300 uppercase">
                    [{evt.agent}]
                  </span>

                  {evt.tool_name && (
                    <Badge variant="secondary" className="font-mono text-[10px] text-cyan-800 dark:text-cyan-300 bg-cyan-50 dark:bg-cyan-950/40">
                      tool: {evt.tool_name}
                    </Badge>
                  )}

                  {isAdaptation && (
                    <Badge className="bg-rose-600 text-white text-[10px] font-bold">
                      ADAPTATION RULE ACTIVE
                    </Badge>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono text-muted-foreground">
                    {new Date(evt.ts).toLocaleTimeString()}
                  </span>

                  {hasDetail && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => toggleExpand(evt.id)}
                      className="h-6 px-1.5 text-[10px] font-mono text-blue-600 hover:text-blue-700"
                    >
                      {isExpanded ? (
                        <>
                          <span>Hide JSON</span>
                          <ChevronDown className="h-3 w-3 ml-0.5" />
                        </>
                      ) : (
                        <>
                          <span>JSON Payload</span>
                          <ChevronRight className="h-3 w-3 ml-0.5" />
                        </>
                      )}
                    </Button>
                  )}
                </div>
              </div>

              {/* Summary line */}
              <div className="mt-1.5 text-xs font-medium text-slate-900 dark:text-slate-100 flex items-start gap-1.5">
                <span>{evt.summary}</span>
              </div>

              {/* Adaptation reason if present */}
              {evt.reason && (
                <div className="mt-1.5 text-xs text-rose-700 dark:text-rose-300 font-medium flex items-center gap-1">
                  <Sparkles className="h-3 w-3" />
                  <span>Trigger Reason: {evt.reason}</span>
                </div>
              )}

              {/* Expandable JSON Detail */}
              {isExpanded && hasDetail && (
                <div className="mt-2 rounded-md bg-slate-950 p-2.5 text-[11px] font-mono text-emerald-400 overflow-x-auto shadow-inner border border-slate-800">
                  <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1 border-b border-slate-800 pb-1">
                    <span className="flex items-center gap-1">
                      <Terminal className="h-3 w-3" />
                      Payload Inspector &bull; Audit Trail Section 5
                    </span>
                    <span>Event #{evt.id}</span>
                  </div>
                  <pre>{JSON.stringify(evt.detail, null, 2)}</pre>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
