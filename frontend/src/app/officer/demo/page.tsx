"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  runScenario,
  sandboxRejectTicket,
  sandboxCrewCheckin,
  sandboxCrewNoShow,
  sandboxRepairPhoto,
  triggerTick,
} from "@/lib/api/endpoints";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Sliders,
  Play,
  Clock,
  RotateCcw,
  Camera,
  Truck,
  Sparkles,
  Terminal,
  ShieldAlert,
  ArrowRight,
  FastForward,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
} from "lucide-react";

export default function DemoPage() {
  const [simTime, setSimTime] = useState<string>("");
  const [runningScenario, setRunningScenario] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [logs, setLogs] = useState<Array<{ ts: string; msg: string; type: "info" | "success" | "warn" }>>([]);

  // Update simulated clock & init logs
  useEffect(() => {
    const now = new Date().toLocaleTimeString();
    setLogs([
      { ts: now, msg: "CivicPilot Simulation Controller initialized.", type: "info" },
      { ts: now, msg: "SIM_TIME_SCALE=60 (1 hr = 60s simulated speed).", type: "info" },
    ]);

    const updateTime = () => {
      setSimTime(new Date().toLocaleTimeString());
    };
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  const addLog = (msg: string, type: "info" | "success" | "warn" = "info") => {
    setLogs((prev) => [{ ts: new Date().toLocaleTimeString(), msg, type }, ...prev.slice(0, 30)]);
  };

  const handleRunScenario = async (scenario: "happy" | "disruption" | "ambiguity" | "case1042") => {
    setRunningScenario(scenario);
    addLog(`Launching scenario: [${scenario.toUpperCase()}]...`, "info");
    try {
      const res = await runScenario(scenario);
      addLog(`Scenario [${scenario.toUpperCase()}] launched successfully! Target Case #${res.data.case_id}`, "success");
    } catch (err: any) {
      addLog(`Error executing scenario ${scenario}: ${err.message}`, "warn");
    } finally {
      setRunningScenario(null);
    }
  };

  const handleTick = async () => {
    try {
      await triggerTick();
      addLog("POST /api/tick triggered: Evaluated due SLA timers & cron checks.", "success");
    } catch (err: any) {
      addLog("Failed to ping /api/tick: " + err.message, "warn");
    }
  };

  const handleSandbox = async (action: string, fn: () => Promise<any>) => {
    setActionLoading(true);
    addLog(`Executing sandbox signal: ${action}...`, "info");
    try {
      await fn();
      addLog(`Sandbox action '${action}' delivered to event bus!`, "success");
    } catch (err: any) {
      addLog(`Sandbox error: ${err.message}`, "warn");
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="container mx-auto max-w-6xl px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b pb-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
            <Sliders className="h-7 w-7 text-blue-600" />
            <span>Interactive Demo &amp; Sandbox Controller</span>
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
            Trigger the 3 deck scenarios, execute the Case 1042 benchmark, and inject in-flight disruptions.
          </p>
        </div>

        {/* Simulated Clock Bar */}
        <div className="flex items-center gap-3 p-2.5 rounded-xl border bg-slate-900 text-white shadow-xs font-mono text-xs">
          <Clock className="h-4 w-4 text-amber-400 animate-spin" style={{ animationDuration: "10s" }} />
          <div>
            <div className="text-[10px] text-slate-400">SIM_TIME_SCALE (60x)</div>
            <div className="font-bold text-sm text-emerald-400">{simTime || "12:00:00 PM"}</div>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={handleTick}
            className="h-7 px-2 text-[10px] text-slate-900 bg-slate-100 hover:bg-slate-200"
          >
            <FastForward className="h-3 w-3 mr-1" />
            <span>Cron Tick</span>
          </Button>
        </div>
      </div>

      {/* Scenarios Grid (The 4 Live Demos) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Scenario 1: Happy Path */}
        <Card className="border-2 border-emerald-200 bg-emerald-50/20 dark:bg-emerald-950/10 shadow-xs">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <Badge className="bg-emerald-600 text-white text-[10px] font-bold">
                SCENARIO 1 &bull; HAPPY PATH
              </Badge>
              <Link href="/officer/cases/1001">
                <Badge variant="outline" className="text-[10px] font-mono hover:bg-emerald-100">
                  Inspect Case #1001 &rarr;
                </Badge>
              </Link>
            </div>
            <CardTitle className="text-base font-bold text-slate-900 dark:text-slate-100 mt-2">
              Urgent Water Main Leak &rarr; Verified Closure
            </CardTitle>
            <CardDescription className="text-xs leading-relaxed">
              Water bursting at Oak St &amp; 5th Ave. System parses damage, retrieves SLA policy (4h), plans dispatch, notifies 47 citizens, verifies repair photo, citizen confirms resolution.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-2 flex items-center justify-between">
            <span className="text-[11px] font-mono text-muted-foreground">Est duration: ~2 mins</span>
            <Button
              size="sm"
              onClick={() => handleRunScenario("happy")}
              disabled={runningScenario === "happy"}
              className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold gap-1.5 shadow-xs"
            >
              <Play className="h-3.5 w-3.5" />
              <span>{runningScenario === "happy" ? "Running..." : "Run Happy Path"}</span>
            </Button>
          </CardContent>
        </Card>

        {/* Scenario 2: Disruption (Ticket Rejection) */}
        <Card className="border-2 border-amber-200 bg-amber-50/20 dark:bg-amber-950/10 shadow-xs">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <Badge className="bg-amber-600 text-white text-[10px] font-bold">
                SCENARIO 2 &bull; DISRUPTION
              </Badge>
              <Link href="/officer/cases/1002">
                <Badge variant="outline" className="text-[10px] font-mono hover:bg-amber-100">
                  Inspect Case #1002 &rarr;
                </Badge>
              </Link>
            </div>
            <CardTitle className="text-base font-bold text-slate-900 dark:text-slate-100 mt-2">
              Ticket Rejected &rarr; Adaptation Rule (a) Replan
            </CardTitle>
            <CardDescription className="text-xs leading-relaxed">
              Dangerous pothole on Mission St. Roads department rejects ticket claiming state highway boundary. Orchestrator triggers Adaptation Rule (a), re-reads policy, and replans work order.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-2 flex items-center justify-between">
            <span className="text-[11px] font-mono text-muted-foreground">Tests: planner.replan</span>
            <Button
              size="sm"
              onClick={() => handleRunScenario("disruption")}
              disabled={runningScenario === "disruption"}
              className="bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold gap-1.5 shadow-xs"
            >
              <Play className="h-3.5 w-3.5" />
              <span>{runningScenario === "disruption" ? "Running..." : "Run Disruption"}</span>
            </Button>
          </CardContent>
        </Card>

        {/* Scenario 3: Ambiguity (Confidence Threshold Guardrail) */}
        <Card className="border-2 border-orange-200 bg-orange-50/20 dark:bg-orange-950/10 shadow-xs">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <Badge className="bg-orange-600 text-white text-[10px] font-bold">
                SCENARIO 3 &bull; AMBIGUITY
              </Badge>
              <Link href="/officer/cases/1003">
                <Badge variant="outline" className="text-[10px] font-mono hover:bg-orange-100">
                  Inspect Case #1003 &rarr;
                </Badge>
              </Link>
            </div>
            <CardTitle className="text-base font-bold text-slate-900 dark:text-slate-100 mt-2">
              Vague Complaint &rarr; Safety Guardrail Halt
            </CardTitle>
            <CardDescription className="text-xs leading-relaxed">
              Vague report: &ldquo;Thing is broken near the park&rdquo;. Confidence score 0.47 breaches the 0.65 threshold. Guardrail safely halts execution into NEEDS_HUMAN queue for officer review.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-2 flex items-center justify-between">
            <span className="text-[11px] font-mono text-muted-foreground">Tests: guardrail threshold</span>
            <Button
              size="sm"
              onClick={() => handleRunScenario("ambiguity")}
              disabled={runningScenario === "ambiguity"}
              className="bg-orange-600 hover:bg-orange-700 text-white text-xs font-bold gap-1.5 shadow-xs"
            >
              <Play className="h-3.5 w-3.5" />
              <span>{runningScenario === "ambiguity" ? "Running..." : "Run Ambiguity"}</span>
            </Button>
          </CardContent>
        </Card>

        {/* Scenario 4: Case 1042 Benchmark */}
        <Card className="border-2 border-red-300 bg-red-50/30 dark:bg-red-950/20 shadow-xs">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <Badge className="bg-red-600 text-white text-[10px] font-bold animate-pulse">
                CASE 1042 &bull; CRITICAL SIGN-OFF
              </Badge>
              <Link href="/officer/cases/1042">
                <Badge variant="outline" className="text-[10px] font-mono hover:bg-red-100 border-red-300">
                  Inspect Case #1042 &rarr;
                </Badge>
              </Link>
            </div>
            <CardTitle className="text-base font-bold text-slate-900 dark:text-slate-100 mt-2">
              Downed Power Line 50m from Elementary School
            </CardTitle>
            <CardDescription className="text-xs leading-relaxed">
              CRITICAL risk tier. 12kV arcing line near playground. Plan blocks step s1 (100m perimeter evacuation &amp; grid shutoff) until officer authorization. Supervisor approves in Approvals queue.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-2 flex items-center justify-between">
            <span className="text-[11px] font-mono text-red-600 font-semibold">Risk: CRITICAL</span>
            <Button
              size="sm"
              onClick={() => handleRunScenario("case1042")}
              disabled={runningScenario === "case1042"}
              className="bg-red-600 hover:bg-red-700 text-white text-xs font-bold gap-1.5 shadow-xs"
            >
              <Play className="h-3.5 w-3.5" />
              <span>{runningScenario === "case1042" ? "Running..." : "Run Case 1042"}</span>
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Sandbox Controls Card */}
      <Card className="border shadow-xs">
        <CardHeader className="pb-3 border-b bg-slate-50/50 dark:bg-slate-900/50">
          <CardTitle className="text-base font-bold flex items-center gap-2">
            <Truck className="h-4 w-4 text-blue-600" />
            <span>Direct Sandbox Injections (Contract Section 7)</span>
          </CardTitle>
          <CardDescription className="text-xs">
            Test backend resilience endpoints directly against work orders in progress.
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <Button
              variant="outline"
              disabled={actionLoading}
              onClick={() =>
                handleSandbox("Ticket Rejection", () =>
                  sandboxRejectTicket("TKT-5521", "State highway route outside city bounds")
                )
              }
              className="text-xs border-rose-300 text-rose-700 hover:bg-rose-50 h-12 flex flex-col items-center justify-center"
            >
              <div className="font-bold flex items-center gap-1">
                <RotateCcw className="h-3.5 w-3.5" />
                <span>Reject Ticket (TKT-5521)</span>
              </div>
              <span className="text-[10px] text-muted-foreground mt-0.5">Adaptation Rule (a)</span>
            </Button>

            <Button
              variant="outline"
              disabled={actionLoading}
              onClick={() =>
                handleSandbox("Crew No-Show", () => sandboxCrewNoShow("TKT-5521"))
              }
              className="text-xs border-amber-300 text-amber-700 hover:bg-amber-50 h-12 flex flex-col items-center justify-center"
            >
              <div className="font-bold flex items-center gap-1">
                <Clock className="h-3.5 w-3.5" />
                <span>Crew No-Show Alert</span>
              </div>
              <span className="text-[10px] text-muted-foreground mt-0.5">Adaptation Rule (b)</span>
            </Button>

            <Button
              variant="outline"
              disabled={actionLoading}
              onClick={() =>
                handleSandbox("Crew Check-In", () => sandboxCrewCheckin("TKT-5521"))
              }
              className="text-xs border-emerald-300 text-emerald-700 hover:bg-emerald-50 h-12 flex flex-col items-center justify-center"
            >
              <div className="font-bold flex items-center gap-1">
                <Truck className="h-3.5 w-3.5" />
                <span>Crew GPS Check-In</span>
              </div>
              <span className="text-[10px] text-muted-foreground mt-0.5">Dispatches location</span>
            </Button>

            <Button
              variant="outline"
              disabled={actionLoading}
              onClick={() =>
                handleSandbox("Repair Photo Upload", () => sandboxRepairPhoto("TKT-5521"))
              }
              className="text-xs border-teal-300 text-teal-700 hover:bg-teal-50 h-12 flex flex-col items-center justify-center"
            >
              <div className="font-bold flex items-center gap-1">
                <Camera className="h-3.5 w-3.5" />
                <span>Upload Repair Photo</span>
              </div>
              <span className="text-[10px] text-muted-foreground mt-0.5">Triggers Vision Eval</span>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Real-Time Controller Logs Terminal */}
      <Card className="border shadow-xs bg-slate-950 text-slate-200">
        <CardHeader className="pb-2 border-b border-slate-800">
          <div className="flex items-center justify-between">
            <CardTitle className="text-xs font-mono flex items-center gap-2 text-slate-300">
              <Terminal className="h-4 w-4 text-emerald-400" />
              <span>SIMULATION EVENT LOG STREAM</span>
            </CardTitle>
            <span className="text-[10px] font-mono text-slate-500">Live SSE Feed</span>
          </div>
        </CardHeader>
        <CardContent className="pt-3 max-h-60 overflow-y-auto font-mono text-xs space-y-1">
          {logs.map((log, i) => (
            <div key={i} className="flex items-start gap-2 text-[11px]">
              <span className="text-slate-500 shrink-0">[{log.ts}]</span>
              <span
                className={
                  log.type === "success"
                    ? "text-emerald-400"
                    : log.type === "warn"
                    ? "text-amber-400"
                    : "text-slate-300"
                }
              >
                {log.msg}
              </span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
